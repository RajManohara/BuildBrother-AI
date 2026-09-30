from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.correlation import correlate, utc
from app.models import (Deployment, DeploymentComponent, Repository, RepositoryService,
                        RuntimeEvent, Service, WorkflowRun)
from app.schemas import DeploymentInput, RuntimeInput, ServiceInput
from app.security import fingerprint, sanitize


def register_service(session: Session, data: ServiceInput) -> Service:
    repo = session.scalar(select(Repository).where(Repository.full_name == data.repository))
    if repo is None:
        raise HTTPException(422, "Collect the repository before mapping a service")
    service = session.get(Service, data.key)
    if service:
        raise HTTPException(409, "Service already exists")
    service = Service(key=data.key, name=data.name, environment=data.environment, criticality=data.criticality)
    session.add(service)
    session.flush()
    session.add(RepositoryService(repository_id=repo.id, service_key=service.key))
    session.flush()
    return service


def ingest_deployment(session: Session, data: DeploymentInput) -> Deployment:
    repo = session.scalar(select(Repository).where(Repository.full_name == data.repository))
    service = session.get(Service, data.service_key)
    if not repo or not service or not session.get(RepositoryService, (repo.id, service.key)):
        raise HTTPException(422, "Repository-to-service mapping is required")
    if service.environment != data.environment:
        raise HTTPException(422, "Environment does not match the registered service")
    run = None
    if data.workflow_run_id is not None:
        run = session.scalar(select(WorkflowRun).where(WorkflowRun.repository_id == repo.id,
                                                       WorkflowRun.source_run_id == data.workflow_run_id))
        if not run or run.head_sha != data.commit_sha or run.conclusion != "success":
            raise HTTPException(422, "Workflow must be a collected successful run for this repository and commit")
        if utc(run.started_at) > utc(data.deployed_at):
            raise HTTPException(422, "Deployment precedes workflow run")
    existing = session.scalar(select(Deployment).where(Deployment.source_event_id == data.source_event_id))
    if existing:
        actual = {(c.name, c.version, c.ecosystem) for c in session.scalars(select(DeploymentComponent).where(
            DeploymentComponent.deployment_id == existing.id))}
        expected = {(c.name, c.version, c.ecosystem) for c in data.components}
        if (existing.service_key != data.service_key or existing.repository_id != repo.id
            or existing.commit_sha != data.commit_sha or existing.environment != data.environment
            or utc(existing.deployed_at) != utc(data.deployed_at) or existing.status != data.status
            or existing.artifact_digest != data.artifact_digest or existing.artifact_uri != data.artifact_uri
            or existing.workflow_run_id != (run.id if run else None) or actual != expected):
            raise HTTPException(409, "Source event ID was already used with different deployment data")
        return existing
    deployment = Deployment(**data.model_dump(exclude={"repository", "workflow_run_id", "components"}),
                            repository_id=repo.id, workflow_run_id=run.id if run else None, source="callback")
    session.add(deployment)
    session.flush()
    for name, version, ecosystem in {(c.name, c.version, c.ecosystem) for c in data.components}:
        session.add(DeploymentComponent(deployment_id=deployment.id, name=name, version=version, ecosystem=ecosystem))
    session.flush()
    for event in session.scalars(select(RuntimeEvent).where(RuntimeEvent.service_key == service.key,
                                                           RuntimeEvent.occurred_at >= data.deployed_at)):
        correlate(session, event)
    return deployment


def ingest_runtime(session: Session, data: RuntimeInput):
    service = session.get(Service, data.service_key)
    if not service or service.environment != data.environment:
        raise HTTPException(422, "Register the service and environment first")
    payload = sanitize(data.model_dump(mode="json"))
    digest = fingerprint(payload)
    event = session.scalar(select(RuntimeEvent).where(RuntimeEvent.source == data.source,
                                                     RuntimeEvent.source_event_id == data.source_event_id))
    if event and event.payload_hash != digest:
        raise HTTPException(409, "Source event ID was already used with different event data")
    if event is None:
        event = RuntimeEvent(**data.model_dump(exclude={"attributes"}), attributes=payload["attributes"], payload_hash=digest)
        session.add(event)
        session.flush()
    incident = correlate(session, event)
    return event, incident
