"""An idempotent, clearly labeled synthetic code-to-runtime investigation."""
from datetime import timedelta
from sqlalchemy import select
from app.github import envelope, upsert
from app.ingestion import ingest_deployment, ingest_runtime
from app.models import (Commit, PullRequest, Repository, RepositoryService, SecurityFinding,
                        Service, WorkflowJob, WorkflowRun, now)
from app.schemas import Component, DeploymentInput, RuntimeInput


def seed(session):
    if session.get(Repository, "demo-repo"):
        return
    base = now() - timedelta(hours=4)
    repo = Repository(id="demo-repo", full_name="demo/payments-api", source_url="", is_demo=True)
    session.add(repo)
    session.flush()
    for key, label in [("payments-api", "Payments API"), ("checkout-worker", "Checkout worker")]:
        session.add(Service(key=key, name=label, environment="demo", criticality="high", is_demo=True))
        session.flush()
        session.add(RepositoryService(repository_id=repo.id, service_key=key))
    sha = "b" * 40
    commit = envelope(session, repo, "commit", sha, base, {"message": "Update demo HTTP client"}, source="synthetic")
    upsert(session, Commit, commit.id, repository_id=repo.id, sha=sha,
           message="Update demo HTTP client dependency", changed_paths=["package-lock.json"])
    pr = envelope(session, repo, "pull_request", "42", base + timedelta(minutes=2), {"number": 42}, source="synthetic")
    upsert(session, PullRequest, pr.id, repository_id=repo.id, number=42, title="Update demo HTTP client",
           head_sha=sha, merge_sha=sha, state="closed", changed_paths=["package-lock.json"])
    for index in range(12):
        when = base - timedelta(days=5 - index // 2) + timedelta(minutes=index * 10)
        if index == 11:
            when = base + timedelta(minutes=4)
        event = envelope(session, repo, "workflow", 800 + index, when, {"name": "Build & verify"}, source="synthetic")
        run = upsert(session, WorkflowRun, event.id, repository_id=repo.id, source_run_id=800 + index,
                     name="Build & verify", head_sha=sha if index == 11 else f"{index:040x}", status="completed",
                     conclusion="failure" if index in (2, 7) else "success", branch="main", started_at=when)
        job = envelope(session, repo, "job", f"job-{index}", when, {"name": "Test suite"}, source="synthetic")
        upsert(session, WorkflowJob, job.id, workflow_run_id=run.id, name="Test suite", conclusion=run.conclusion,
               steps=[{"name": "Unit tests", "status": "completed", "conclusion": run.conclusion}])
    finding = envelope(session, repo, "finding", "demo-finding", base + timedelta(minutes=6),
                       {"title": "Synthetic dependency advisory — demo-http-client 1.0.0"}, source="synthetic")
    upsert(session, SecurityFinding, finding.id, repository_id=repo.id, title="Synthetic outbound-request advisory",
           severity="high", state="open", commit_sha=sha, package_name="demo-http-client", package_version="1.0.0",
           ecosystem="npm", behavior="network.unusual_outbound")
    session.flush()
    ingest_deployment(session, DeploymentInput(source_event_id="demo-deploy-1", service_key="payments-api",
        environment="demo", repository=repo.full_name, commit_sha=sha, workflow_run_id=811,
        artifact_digest="sha256:" + "d" * 64, artifact_uri="demo://payments-api", deployed_at=base + timedelta(minutes=10),
        components=[Component(name="demo-http-client", version="1.0.0", ecosystem="npm")]))
    for key, service, behavior, severity, offset in [
        ("demo-event-1", "payments-api", "network.unusual_outbound", "high", 29),
        ("demo-event-2", "checkout-worker", "authentication.unusual_source", "medium", 50),
    ]:
        ingest_runtime(session, RuntimeInput(source_event_id=key, source="synthetic", service_key=service,
            asset_key=f"pod/{service}-demo", environment="demo", event_type=behavior, severity=severity,
            occurred_at=base + timedelta(minutes=offset), attributes={"destination": "198.51.100.24",
            "baseline_deviation": 0.91, "notice": "Safe synthetic demonstration; no real compromise"}))
    session.commit()
