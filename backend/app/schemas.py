from datetime import datetime, timezone, timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

Severity = Literal["low", "medium", "high", "critical"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ServiceInput(StrictModel):
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    name: str = Field(min_length=1, max_length=200)
    environment: str = Field(min_length=1, max_length=60)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    criticality: Severity = "medium"


class Component(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    ecosystem: str = Field(min_length=1, max_length=80)


class DeploymentInput(StrictModel):
    source_event_id: str = Field(min_length=1, max_length=150)
    service_key: str = Field(min_length=1, max_length=100)
    environment: str = Field(min_length=1, max_length=60)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    workflow_run_id: int | None = Field(default=None, gt=0)
    artifact_digest: str | None = Field(default=None, pattern=r"^sha256:[a-f0-9]{64}$")
    artifact_uri: str | None = Field(default=None, max_length=500)
    deployed_at: AwareDatetime
    status: Literal["succeeded", "failed"] = "succeeded"
    components: list[Component] = Field(default_factory=list, max_length=200)

    @field_validator("deployed_at")
    @classmethod
    def not_future(cls, value):
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Deployment time cannot be in the future")
        return value.astimezone(timezone.utc)


class RuntimeInput(StrictModel):
    source_event_id: str = Field(min_length=1, max_length=150)
    source: str = Field(default="synthetic", pattern=r"^[a-zA-Z0-9_.-]{1,30}$")
    service_key: str = Field(min_length=1, max_length=100)
    asset_key: str = Field(min_length=1, max_length=200)
    environment: str = Field(min_length=1, max_length=60)
    event_type: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,100}$")
    severity: Severity
    occurred_at: AwareDatetime
    attributes: dict = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def not_future(cls, value):
        return DeploymentInput.not_future(value)


class AnalystQuestion(StrictModel):
    question: str = Field(min_length=3, max_length=1500)
    incident_id: str | None = Field(default=None, max_length=80)


class IncidentUpdate(StrictModel):
    status: Literal["New", "Investigating", "Contained", "Resolved", "False Positive"]
    note: str = Field(default="", max_length=2000)
