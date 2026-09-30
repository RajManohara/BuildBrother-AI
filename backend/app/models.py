"""Evidence and deployment provenance. One local workspace in this MVP."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

Json = JSON().with_variant(JSONB(), "postgresql")


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), unique=True)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Evidence(Base):
    """Sanitized source envelope; source IDs are unique within repository and kind."""
    __tablename__ = "raw_source_events"
    __table_args__ = (UniqueConstraint("source", "source_event_id", "kind", "repository_id"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), index=True)
    source: Mapped[str] = mapped_column(String(30))
    source_event_id: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(40), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    payload_hash: Mapped[str] = mapped_column(String(64))
    attributes: Mapped[dict] = mapped_column(Json, default=dict)


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint("repository_id", "sha"),)
    id: Mapped[str] = mapped_column(ForeignKey("raw_source_events.id"), primary_key=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    sha: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    changed_paths: Mapped[list] = mapped_column(Json, default=list)


class PullRequest(Base):
    __tablename__ = "pull_requests"
    id: Mapped[str] = mapped_column(ForeignKey("raw_source_events.id"), primary_key=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    head_sha: Mapped[str] = mapped_column(String(64))
    merge_sha: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(30))
    changed_paths: Mapped[list] = mapped_column(Json, default=list)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (UniqueConstraint("repository_id", "source_run_id"),)
    id: Mapped[str] = mapped_column(ForeignKey("raw_source_events.id"), primary_key=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    source_run_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"))
    name: Mapped[str] = mapped_column(String(200))
    head_sha: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30))
    conclusion: Mapped[str | None] = mapped_column(String(30))
    branch: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowJob(Base):
    __tablename__ = "workflow_jobs"
    id: Mapped[str] = mapped_column(ForeignKey("raw_source_events.id"), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"))
    name: Mapped[str] = mapped_column(String(200))
    conclusion: Mapped[str | None] = mapped_column(String(30))
    steps: Mapped[list] = mapped_column(Json, default=list)


class SecurityFinding(Base):
    __tablename__ = "security_findings"
    id: Mapped[str] = mapped_column(ForeignKey("raw_source_events.id"), primary_key=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    title: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(30))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    package_name: Mapped[str | None] = mapped_column(String(200))
    package_version: Mapped[str | None] = mapped_column(String(100))
    ecosystem: Mapped[str | None] = mapped_column(String(80))
    behavior: Mapped[str | None] = mapped_column(String(100))


class Service(Base):
    __tablename__ = "services"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    environment: Mapped[str] = mapped_column(String(60))
    criticality: Mapped[str] = mapped_column(String(20), default="medium")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class RepositoryService(Base):
    __tablename__ = "repository_services"
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), primary_key=True)
    service_key: Mapped[str] = mapped_column(ForeignKey("services.key"), primary_key=True)
    path: Mapped[str] = mapped_column(String(500), default="/")


class Deployment(Base):
    __tablename__ = "deployments"
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=uid)
    source_event_id: Mapped[str] = mapped_column(String(150), unique=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    service_key: Mapped[str] = mapped_column(ForeignKey("services.key"), index=True)
    environment: Mapped[str] = mapped_column(String(60))
    commit_sha: Mapped[str] = mapped_column(String(64))
    workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"))
    artifact_digest: Mapped[str | None] = mapped_column(String(80))
    artifact_uri: Mapped[str | None] = mapped_column(String(500))
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(30))


class DeploymentComponent(Base):
    __tablename__ = "deployment_components"
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), primary_key=True)
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    ecosystem: Mapped[str] = mapped_column(String(80), primary_key=True)


class RuntimeEvent(Base):
    __tablename__ = "runtime_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    source: Mapped[str] = mapped_column(String(30))
    source_event_id: Mapped[str] = mapped_column(String(150))
    __table_args__ = (UniqueConstraint("source", "source_event_id"),)
    service_key: Mapped[str] = mapped_column(ForeignKey("services.key"), index=True)
    asset_key: Mapped[str] = mapped_column(String(200))
    environment: Mapped[str] = mapped_column(String(60))
    event_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    payload_hash: Mapped[str] = mapped_column(String(64))
    attributes: Mapped[dict] = mapped_column(Json, default=dict)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    runtime_event_id: Mapped[str] = mapped_column(ForeignKey("runtime_events.id"), unique=True)
    deployment_id: Mapped[str | None] = mapped_column(ForeignKey("deployments.id"))
    title: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="New")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    contributions: Mapped[list] = mapped_column(Json, default=list)
    gaps: Mapped[list] = mapped_column(Json, default=list)
    summary: Mapped[str] = mapped_column(Text)


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    relationship: Mapped[str] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    label: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(500), default="")


class CollectorCursor(Base):
    __tablename__ = "collector_cursors"
    key: Mapped[str] = mapped_column(String(500), primary_key=True)
    etag: Mapped[str | None] = mapped_column(String(200))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(100), default="pending")
    cached_payload: Mapped[dict] = mapped_column(Json, default=dict)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rate_remaining: Mapped[int | None] = mapped_column(Integer)


class IncidentNote(Base):
    __tablename__ = "incident_notes"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
