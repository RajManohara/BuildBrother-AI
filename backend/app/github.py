"""Read-only GitHub collection. Only installation-token creation uses POST."""
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlparse

import httpx
import jwt
from sqlalchemy import select

from app.correlation import utc
from app.models import (CollectorCursor, Commit, Evidence, PullRequest, Repository,
                        SecurityFinding, WorkflowJob, WorkflowRun, now)
from app.security import fingerprint, sanitize


class CollectionUnavailable(Exception):
    pass


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc) if value else now()


def safe_url(value):
    parsed = urlparse(value or "")
    return value if parsed.scheme == "https" and parsed.netloc == "github.com" else ""


class GitHubClient:
    def __init__(self, settings, session, client=None):
        self.settings, self.session = settings, session
        self.client = client or httpx.Client(base_url="https://api.github.com", timeout=20, follow_redirects=False)
        self.token, self.expires = "", now()

    def close(self):
        self.client.close()

    def authorization(self):
        if self.token and self.expires > now() + timedelta(minutes=2):
            return self.token
        cfg = self.settings
        if not (cfg.github_app_id and cfg.github_installation_id and cfg.github_private_key):
            raise CollectionUnavailable("GitHub App credentials are not configured")
        issued = int(now().timestamp())
        signed = jwt.encode({"iat": issued - 60, "exp": issued + 540, "iss": cfg.github_app_id},
                            cfg.github_private_key.replace("\\n", "\n"), algorithm="RS256")
        response = self.client.post(f"/app/installations/{cfg.github_installation_id}/access_tokens",
                                    headers={"Authorization": f"Bearer {signed}",
                                             "Accept": "application/vnd.github+json",
                                             "X-GitHub-Api-Version": cfg.github_api_version},
                                    json={"repositories": [cfg.github_repository.split("/")[-1]]})
        if response.status_code != 201:
            raise CollectionUnavailable(f"Installation authentication failed (HTTP {response.status_code})")
        body = response.json()
        self.token, self.expires = body["token"], timestamp(body["expires_at"])
        return self.token

    def get(self, path, params=None):
        if not path.startswith("/repos/") or "://" in path or ".." in path:
            raise ValueError("Only repository REST paths are allowed")
        params = params or {}
        key = f"{path}:page={params.get('page', 1)}"
        cursor = self.session.get(CollectorCursor, key)
        if cursor is None:
            cursor = CollectorCursor(key=key, cached_payload={})
            self.session.add(cursor)
            self.session.flush()
        if cursor.next_attempt_at and utc(cursor.next_attempt_at) > now():
            raise CollectionUnavailable("Collection is backing off after an upstream limit")
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.authorization()}",
                   "X-GitHub-Api-Version": self.settings.github_api_version}
        query_hash = fingerprint(params)
        if cursor.etag and cursor.cached_payload.get("query_hash") == query_hash:
            headers["If-None-Match"] = cursor.etag
        try:
            response = self.client.get(path, params=params, headers=headers)
        except httpx.HTTPError:
            cursor.state = "network_unavailable"
            cursor.next_attempt_at = now() + timedelta(minutes=1)
            raise CollectionUnavailable("Network request failed; retry has been scheduled")
        remaining = response.headers.get("x-ratelimit-remaining")
        cursor.rate_remaining = int(remaining) if remaining and remaining.isdigit() else None
        if response.status_code == 304:
            cursor.state, cursor.last_success_at = "up_to_date", now()
            return cursor.cached_payload.get("body", {})
        limited = "rate limit" in response.text.lower() or "abuse" in response.text.lower()
        if response.status_code in (403, 429) and (remaining == "0" or response.status_code == 429 or response.headers.get("retry-after") or limited):
            delay = response.headers.get("retry-after", "60")
            reset = response.headers.get("x-ratelimit-reset", "0")
            seconds = max(60, int(delay) if delay.isdigit() else 60,
                          int(reset) - int(now().timestamp()) if reset.isdigit() else 60)
            cursor.next_attempt_at = now() + timedelta(seconds=min(seconds, 86400))
            cursor.state = "rate_limited"
            raise CollectionUnavailable("GitHub rate limit reached; retry has been scheduled")
        if response.status_code in (403, 404):
            cursor.state = "permission_or_feature_unavailable"
            raise CollectionUnavailable(f"Resource unavailable (HTTP {response.status_code}); check permissions and feature availability")
        if response.status_code >= 400:
            cursor.state = f"upstream_http_{response.status_code}"
            cursor.next_attempt_at = now() + timedelta(minutes=1)
            raise CollectionUnavailable(f"GitHub request failed (HTTP {response.status_code})")
        body = sanitize(response.json())
        cursor.etag = response.headers.get("etag")
        cursor.cached_payload = {"query_hash": query_hash, "body": body}
        cursor.state, cursor.last_success_at, cursor.next_attempt_at = "collected", now(), None
        return body

    def pages(self, path, field=None, params=None):
        """A bounded backfill fails explicitly instead of silently claiming completeness."""
        for page in range(1, 51):
            body = self.get(path, {**(params or {}), "per_page": 100, "page": page})
            items = body.get(field, []) if field else body
            if not isinstance(items, list):
                raise CollectionUnavailable("Unexpected GitHub response shape")
            yield from items
            if len(items) < 100:
                return
        raise CollectionUnavailable("Backfill exceeded 5,000 records; narrow the collection window")


def envelope(session, repo, kind, source_id, when, attributes, url="", source="github"):
    record = session.scalar(select(Evidence).where(Evidence.repository_id == repo.id,
        Evidence.kind == kind, Evidence.source == source, Evidence.source_event_id == str(source_id)))
    if record is None:
        record = Evidence(repository_id=repo.id, kind=kind, source=source, source_event_id=str(source_id),
                          occurred_at=when, payload_hash="")
        session.add(record)
    record.attributes = sanitize(attributes)
    record.payload_hash = fingerprint(record.attributes)
    record.source_url, record.observed_at = safe_url(url), now()
    session.flush()
    return record


def upsert(session, model, key, **values):
    row = session.get(model, key)
    if row is None:
        row = model(id=key, **values)
        session.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    session.flush()
    return row


def collect(session, settings, client=None):
    name = settings.github_repository
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
        raise CollectionUnavailable("Invalid configured repository")
    github = GitHubClient(settings, session, client)
    issues = []
    base = f"/repos/{name}"
    try:
        meta = github.get(base)
        repo = upsert(session, Repository, str(meta["id"]), full_name=meta["full_name"],
                      source_url=safe_url(meta["html_url"]), default_branch=meta["default_branch"], is_demo=False)
        cutoff = now() - timedelta(days=30)

        def commits():
            for item in github.pages(base + "/commits", params={"since": cutoff.isoformat()}):
                details = github.get(base + "/commits/" + item["sha"])
                ev = envelope(session, repo, "commit", item["sha"], timestamp(item["commit"]["committer"]["date"]),
                              {"sha": item["sha"], "message": item["commit"]["message"]}, item["html_url"])
                upsert(session, Commit, ev.id, repository_id=repo.id, sha=item["sha"],
                       message=item["commit"]["message"][:500], changed_paths=[f["filename"] for f in details.get("files", [])])

        def pulls():
            for item in github.pages(base + "/pulls", params={"state": "all", "sort": "updated", "direction": "desc"}):
                if timestamp(item["updated_at"]) < cutoff:
                    break
                files = list(github.pages(base + f"/pulls/{item['number']}/files"))
                ev = envelope(session, repo, "pull_request", item["id"], timestamp(item.get("merged_at") or item["created_at"]),
                              {"title": item["title"], "number": item["number"]}, item["html_url"])
                upsert(session, PullRequest, ev.id, repository_id=repo.id, number=item["number"], title=item["title"][:500],
                       head_sha=item["head"]["sha"], merge_sha=item.get("merge_commit_sha") if item.get("merged_at") else None,
                       state=item["state"], changed_paths=[f["filename"] for f in files])

        def runs():
            for item in github.pages(base + "/actions/runs", "workflow_runs", {"created": ">=" + cutoff.date().isoformat()}):
                ev = envelope(session, repo, "workflow", item["id"], timestamp(item["created_at"]),
                              {k: item.get(k) for k in ("name", "status", "conclusion", "head_sha")}, item["html_url"])
                run = upsert(session, WorkflowRun, ev.id, repository_id=repo.id, source_run_id=item["id"],
                             name=(item.get("name") or "Workflow")[:200], head_sha=item["head_sha"], status=item["status"],
                             conclusion=item.get("conclusion"), branch=item.get("head_branch") or "detached",
                             started_at=timestamp(item.get("run_started_at") or item["created_at"]))
                for job in github.pages(base + f"/actions/runs/{item['id']}/jobs", "jobs"):
                    job_ev = envelope(session, repo, "job", job["id"], timestamp(job.get("started_at")),
                                      {"name": job["name"], "conclusion": job.get("conclusion")}, job.get("html_url"))
                    upsert(session, WorkflowJob, job_ev.id, workflow_run_id=run.id, name=job["name"][:200],
                           conclusion=job.get("conclusion"), steps=[{k: s.get(k) for k in ("name", "status", "conclusion")} for s in job.get("steps", [])])

        def findings(resource):
            for item in github.pages(base + f"/{resource}/alerts"):
                advisory = item.get("security_advisory", {})
                rule = item.get("rule", {})
                instance = item.get("most_recent_instance", {})
                dependency = item.get("dependency", {}).get("package", {})
                title = advisory.get("summary") or rule.get("description") or "Security finding"
                severity = advisory.get("severity") or rule.get("security_severity_level") or "medium"
                ev = envelope(session, repo, resource, item["number"], timestamp(item.get("created_at")),
                              {"title": title, "state": item["state"], "severity": severity}, item.get("html_url"))
                upsert(session, SecurityFinding, ev.id, repository_id=repo.id, title=title[:500], severity=severity,
                       state="open" if item["state"] == "open" else "closed", commit_sha=instance.get("commit_sha"),
                       package_name=dependency.get("name"), package_version=None, ecosystem=dependency.get("ecosystem"), behavior=None)

        def deployments():
            for item in github.pages(base + "/deployments"):
                if timestamp(item["created_at"]) < cutoff:
                    break
                statuses = list(github.pages(base + f"/deployments/{item['id']}/statuses"))
                envelope(session, repo, "github_deployment", item["id"], timestamp(item["created_at"]),
                         {"sha": item["sha"], "environment": item["environment"], "statuses": [
                             {k: s.get(k) for k in ("state", "created_at", "environment_url")} for s in statuses]}, repo.source_url)
                # Service identity is not inferred from environment names. A verified callback links it.

        for label, operation in [("commits", commits), ("pull_requests", pulls), ("workflow_runs", runs),
                                  ("dependabot", lambda: findings("dependabot")),
                                  ("code_scanning", lambda: findings("code-scanning")), ("deployments", deployments)]:
            try:
                operation()
            except (CollectionUnavailable, httpx.HTTPError) as error:
                issues.append({"resource": label, "message": str(error) if isinstance(error, CollectionUnavailable) else "Network request failed"})
        repo.collected_at = now()
        session.flush()
        return {"repository": name, "issues": issues, "status": "partial" if issues else "collected"}
    finally:
        github.close()
