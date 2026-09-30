from datetime import timedelta
import httpx
import pytest
from sqlalchemy import select
from app.core.config import Settings
from app.github import GitHubClient, CollectionUnavailable, collect
from app.models import CollectorCursor, Repository, now


def github_client(session, handler):
    client = GitHubClient(Settings(_env_file=None), session,
                          httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler)))
    client.token, client.expires = "test-token", now()+timedelta(hours=1)
    return client


def test_etag_304_preserves_cached_records(client):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls)==1:
            return httpx.Response(200,json=[{"id":1}],headers={"ETag":"test-etag"})
        assert request.headers["if-none-match"] == "test-etag"
        return httpx.Response(304)
    with client.app.state.sessions() as session:
        github = github_client(session,handler)
        assert github.get("/repos/test/demo/commits") == [{"id":1}]
        assert github.get("/repos/test/demo/commits") == [{"id":1}]
        assert all(r.method=="GET" for r in calls)


def test_pagination_and_read_only_path_restriction(client):
    def handler(request):
        page=int(request.url.params["page"])
        return httpx.Response(200,json=[{"id":i} for i in range(100)] if page==1 else [{"id":100}])
    with client.app.state.sessions() as session:
        github=github_client(session,handler)
        assert len(list(github.pages("/repos/test/demo/commits"))) == 101
        with pytest.raises(ValueError): github.get("https://untrusted.example/steal")


def test_rate_limit_persists_backoff(client):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(403,headers={"x-ratelimit-remaining":"0","retry-after":"120"})
    with client.app.state.sessions() as session:
        github=github_client(session,handler)
        for _ in range(2):
            with pytest.raises(CollectionUnavailable):github.get("/repos/test/demo/actions/runs")
        assert len(calls)==1
        cursor=session.scalar(select(CollectorCursor))
        assert cursor.state=="rate_limited"
        assert cursor.next_attempt_at is not None


def test_permission_failure_is_not_empty_result(client):
    with client.app.state.sessions() as session:
        github=github_client(session,lambda _:httpx.Response(404))
        with pytest.raises(CollectionUnavailable):github.get("/repos/test/demo/dependabot/alerts")
        assert session.scalar(select(CollectorCursor)).state=="permission_or_feature_unavailable"


def test_collection_repeated_upsert_and_missing_feature(client, monkeypatch):
    monkeypatch.setattr(GitHubClient,"authorization",lambda self:"test-token")
    def handler(request):
        path=request.url.path
        if path=="/repos/test/demo":
            return httpx.Response(200,json={"id":42,"full_name":"test/demo","html_url":"https://github.com/test/demo","default_branch":"main"})
        if path.endswith("/actions/runs"):return httpx.Response(200,json={"workflow_runs":[]})
        if path.endswith("/dependabot/alerts"):return httpx.Response(403)
        return httpx.Response(200,json=[])
    with client.app.state.sessions() as session:
        cfg=Settings(_env_file=None,github_repository="test/demo")
        for _ in range(2):
            result=collect(session,cfg,httpx.Client(base_url="https://api.github.com",transport=httpx.MockTransport(handler)))
            assert result["status"]=="partial"
        assert len(list(session.scalars(select(Repository).where(Repository.full_name=="test/demo"))))==1
