"""Read models used by both the UI and the deterministic analyst."""
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from datetime import datetime
from app.correlation import utc
from app.models import (Commit, CollectorCursor, Deployment, Evidence, Incident, IncidentEvidence,
                        IncidentNote, PullRequest, Repository, RuntimeEvent, SecurityFinding, Service,
                        WorkflowJob, WorkflowRun)


def serialize(row):
    values = {column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs}
    return {key: utc(value) if isinstance(value, datetime) else value for key, value in values.items()}


def incident_detail(session: Session, incident_id: str):
    incident = session.get(Incident, incident_id)
    if not incident:
        return None
    data = serialize(incident)
    data["timeline"] = [serialize(x) for x in session.scalars(select(IncidentEvidence).where(
        IncidentEvidence.incident_id == incident_id).order_by(IncidentEvidence.occurred_at, IncidentEvidence.kind))]
    data["runtime_event"] = serialize(session.get(RuntimeEvent, incident.runtime_event_id))
    data["deployment"] = serialize(session.get(Deployment, incident.deployment_id)) if incident.deployment_id else None
    data["notes"] = [serialize(n) for n in session.scalars(select(IncidentNote).where(
        IncidentNote.incident_id == incident_id).order_by(IncidentNote.created_at))]
    data["recommended_actions"] = [
        "Verify the deployment record against your release system.",
        "Review the original runtime event and compare it with the service baseline.",
        "Validate whether linked findings apply to the deployed artifact.",
        "Preserve relevant evidence and seek human approval before remediation.",
    ]
    return data


def workspace(session: Session, config):
    def rows(model, order=None):
        query = select(model)
        if order is not None:
            query = query.order_by(order)
        return [serialize(row) for row in session.scalars(query.limit(500))]
    data = {
        "repositories": rows(Repository), "commits": rows(Commit), "pull_requests": rows(PullRequest),
        "runs": rows(WorkflowRun, WorkflowRun.started_at.desc()), "jobs": rows(WorkflowJob),
        "findings": rows(SecurityFinding), "services": rows(Service),
        "deployments": rows(Deployment, Deployment.deployed_at.desc()),
        "events": rows(RuntimeEvent, RuntimeEvent.occurred_at.desc()),
        "incidents": rows(Incident, Incident.created_at.desc()),
    }
    data["source_urls"] = {e.id: e.source_url for e in session.scalars(select(Evidence).limit(2000))}
    data["collection"] = [{"resource": c.key, "state": c.state, "last_success_at": c.last_success_at,
                           "next_attempt_at": c.next_attempt_at, "rate_remaining": c.rate_remaining}
                          for c in session.scalars(select(CollectorCursor))]
    data["settings"] = {"demo_mode": any(r["is_demo"] for r in data["repositories"]), "github_repository": config.github_repository,
                        "github_configured": bool(config.github_app_id and config.github_installation_id and config.github_private_key),
                        "ingestion_configured": bool(config.ingest_token), "analyst_mode": "Evidence templates",
                        "scope": "Single local workspace", "limit": 500}
    return data
