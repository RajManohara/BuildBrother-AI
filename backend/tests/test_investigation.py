from datetime import datetime, timedelta
from sqlalchemy import select
from app.correlation import correlate, utc
from app.models import Deployment, Incident, Repository, RuntimeEvent, SecurityFinding, now


def runtime(client, **overrides):
    data = {"source":"synthetic", "source_event_id":"test-event", "service_key":"payments-api",
            "asset_key":"pod/test", "environment":"demo", "event_type":"network.unusual_outbound",
            "severity":"medium", "occurred_at":now().isoformat(), "attributes":{"destination":"198.51.100.24"}}
    data.update(overrides)
    return data


def test_demo_chain_and_unlinked_event(client):
    data = client.get("/api/v1/workspace").json()
    assert len(data["incidents"]) == 2
    linked = next(i for i in data["incidents"] if i["deployment_id"])
    unlinked = next(i for i in data["incidents"] if not i["deployment_id"])
    detail = client.get(f"/api/v1/incidents/{linked['id']}").json()
    assert linked["confidence"] == 95
    assert sum(c["points"] for c in linked["contributions"]) == 95
    assert unlinked["confidence"] == 0
    assert {e["kind"] for e in detail["timeline"]} == {"commit","pull_request","workflow","deployment","finding","runtime"}
    assert "does not establish causation" in linked["summary"]
    assert not any("failure" in c["label"].lower() for c in linked["contributions"])


def test_idempotency_conflict_and_redaction(client, headers):
    payload = runtime(client, attributes={"password":"secret", "message":"api_key=private-value"})
    first = client.post("/api/v1/runtime/events", json=payload, headers=headers)
    second = client.post("/api/v1/runtime/events", json=payload, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["event_id"] == second.json()["event_id"]
    payload["severity"] = "critical"
    assert client.post("/api/v1/runtime/events", json=payload, headers=headers).status_code == 409
    detail = client.get("/api/v1/incidents/" + first.json()["incident_id"]).json()
    assert detail["runtime_event"]["attributes"]["password"] == "[REDACTED]"
    assert "private-value" not in str(detail)


def test_future_deployment_cannot_link_to_earlier_event(client, headers):
    deployment = client.get("/api/v1/workspace").json()["deployments"][0]
    payload = runtime(client, occurred_at=(utc(datetime.fromisoformat(deployment["deployed_at"])) - timedelta(minutes=1)).isoformat())
    response = client.post("/api/v1/runtime/events", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["confidence"] == 0
    detail = client.get("/api/v1/incidents/" + response.json()["incident_id"]).json()
    assert detail["deployment"] is None


def test_environment_and_future_validation(client, headers):
    assert client.post("/api/v1/runtime/events", json=runtime(client, environment="production"), headers=headers).status_code == 422
    assert client.post("/api/v1/runtime/events", json=runtime(client, occurred_at=(now()+timedelta(days=1)).isoformat()), headers=headers).status_code == 422
    assert client.post("/api/v1/runtime/events", json=runtime(client, occurred_at="2026-01-01T00:00:00"), headers=headers).status_code == 422
    assert client.post("/api/v1/runtime/events", json=runtime(client, severity="certainly hacked"), headers=headers).status_code == 422


def test_ingestion_requires_separate_credential(client):
    assert client.post("/api/v1/runtime/events", json=runtime(client)).status_code == 401
    assert client.post("/api/v1/runtime/events", json=runtime(client), headers={"Authorization":"Bearer wrong"}).status_code == 401


def test_latest_successful_deployment_excludes_failed_release(client, headers):
    with client.app.state.sessions() as session:
        old = session.scalar(select(Deployment))
        session.add(Deployment(source_event_id="failed-new-release", repository_id=old.repository_id,
            service_key=old.service_key, environment=old.environment, commit_sha="a"*40,
            deployed_at=now()-timedelta(minutes=20), status="failed", source="callback"))
        session.commit()
    result = client.post("/api/v1/runtime/events", json=runtime(client), headers=headers).json()
    detail = client.get("/api/v1/incidents/"+result["incident_id"]).json()
    assert detail["deployment"]["commit_sha"] == "b"*40
    assert detail["severity"] == "medium"


def test_finding_for_other_commit_is_not_linked(client):
    with client.app.state.sessions() as session:
        finding = session.scalar(select(SecurityFinding))
        finding.commit_sha = "a"*40
        finding.package_version = "9.9.9"
        event = session.scalar(select(RuntimeEvent).where(RuntimeEvent.service_key=="payments-api"))
        session.flush()
        incident = correlate(session,event)
        assert not any("Security finding matches" in c["label"] for c in incident.contributions)
        session.commit()


def test_incident_workflow_and_cited_analyst(client, headers):
    incident = client.get("/api/v1/workspace").json()["incidents"][0]
    path = f"/api/v1/incidents/{incident['id']}"
    changed = client.patch(path,json={"status":"Investigating","note":"Verified service identity"},headers=headers)
    assert changed.status_code == 200
    assert changed.json()["notes"][0]["text"].endswith("Verified service identity")
    result = client.post("/api/v1/analyst",json={"question":"What happened before this event?","incident_id":incident["id"]})
    assert result.status_code == 200
    evidence_ids = {e["evidence_id"] for e in changed.json()["timeline"]}
    assert {c["id"] for c in result.json()["citations"]} == evidence_ids
    assert result.json()["mode"] == "deterministic"
    assert client.get("/api/v1/incidents/not-a-real-id").status_code == 404


def test_deployment_rejects_wrong_commit_and_reconciles_late_evidence(client, headers):
    base = {"source_event_id":"callback-2", "service_key":"checkout-worker", "environment":"demo",
            "repository":"demo/payments-api", "commit_sha":"a"*40, "workflow_run_id":811,
            "deployed_at":(now()-timedelta(hours=3,minutes=30)).isoformat()}
    assert client.post("/api/v1/deployments/ingest",json=base,headers=headers).status_code == 422
    base["commit_sha"] = "b"*40
    response = client.post("/api/v1/deployments/ingest",json=base,headers=headers)
    assert response.status_code == 200
    assert client.post("/api/v1/deployments/ingest",json=base,headers=headers).json()["id"] == response.json()["id"]
    data = client.get("/api/v1/workspace").json()
    target = next(e for e in data["events"] if e["service_key"]=="checkout-worker")
    incident = next(i for i in data["incidents"] if i["runtime_event_id"]==target["id"])
    assert incident["deployment_id"] == response.json()["id"]
    base["artifact_uri"] = "changed"
    assert client.post("/api/v1/deployments/ingest",json=base,headers=headers).status_code == 409


def test_body_limit_and_unknown_fields(client, headers):
    assert client.post("/api/v1/runtime/events",content=b"x"*1_048_577,headers=headers).status_code == 413
    assert client.post("/api/v1/runtime/events",json=runtime(client,execute="do something"),headers=headers).status_code == 422


def test_timezone_offsets_normalized(client, headers):
    from datetime import timezone
    instant = now()-timedelta(minutes=2)
    shifted = instant.astimezone(timezone(timedelta(hours=-7)))
    response = client.post("/api/v1/runtime/events",json=runtime(client,occurred_at=shifted.isoformat()),headers=headers)
    assert response.status_code == 200
    assert response.json()["confidence"] > 0


def test_demo_seed_is_idempotent(client):
    from app.demo import seed
    with client.app.state.sessions() as session:
        seed(session)
    assert len(client.get("/api/v1/workspace").json()["incidents"]) == 2
