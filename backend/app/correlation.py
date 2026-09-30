"""Deterministic relationships. Operational failures never contribute to security scores."""
from datetime import timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (Commit, Deployment, DeploymentComponent, Evidence, Incident,
                        IncidentEvidence, PullRequest, RuntimeEvent, SecurityFinding, WorkflowRun)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def correlate(session: Session, event: RuntimeEvent) -> Incident:
    incident = session.scalar(select(Incident).where(Incident.runtime_event_id == event.id))
    if incident is None:
        incident = Incident(runtime_event_id=event.id, title="", severity=event.severity,
                            confidence=0, summary="")
        session.add(incident)
        session.flush()
    session.execute(delete(IncidentEvidence).where(IncidentEvidence.incident_id == incident.id))
    contributions, gaps = [], []

    def attach(kind, key, label, when, relationship, url=""):
        session.add(IncidentEvidence(incident_id=incident.id, evidence_id=key, kind=kind,
                                    label=label[:500], occurred_at=when, relationship=relationship,
                                    source_url=url))

    def credit(label, points):
        contributions.append({"label": label, "points": points})

    deployment = session.scalar(select(Deployment).where(
        Deployment.service_key == event.service_key, Deployment.environment == event.environment,
        Deployment.deployed_at <= event.occurred_at, Deployment.status == "succeeded",
    ).order_by(Deployment.deployed_at.desc(), Deployment.id.desc()).limit(1))
    incident.deployment_id = deployment.id if deployment else None
    incident.title = f"{event.event_type.replace('.', ' ').replace('_', ' ').capitalize()} on {event.service_key}"
    incident.severity = event.severity
    attach("runtime", event.id, event.event_type, event.occurred_at, "Observed behavior on this service")
    finding_count = 0
    if deployment:
        credit("Service and environment match the active deployment", 30)
        attach("deployment", deployment.id, f"Deployed {deployment.commit_sha[:8]} to {deployment.environment}",
               deployment.deployed_at, "Latest successful deployment before the runtime event")
        run = session.get(WorkflowRun, deployment.workflow_run_id) if deployment.workflow_run_id else None
        if run and run.head_sha == deployment.commit_sha and run.repository_id == deployment.repository_id:
            credit("Workflow run and deployed commit match", 15)
            env = session.get(Evidence, run.id)
            attach("workflow", run.id, f"{run.name} #{run.source_run_id}", run.started_at,
                   "Produces the deployed commit; build outcome adds no security severity", env.source_url)
        else:
            gaps.append("No verified workflow run is attached to this deployment.")
        commit = session.scalar(select(Commit).where(Commit.repository_id == deployment.repository_id,
                                                    Commit.sha == deployment.commit_sha))
        if commit:
            env = session.get(Evidence, commit.id)
            attach("commit", commit.id, commit.message, env.occurred_at, "Exact deployed commit", env.source_url)
        else:
            gaps.append("Commit metadata has not been collected.")
        for pr in session.scalars(select(PullRequest).where(PullRequest.repository_id == deployment.repository_id,
                                                           PullRequest.merge_sha == deployment.commit_sha)):
            env = session.get(Evidence, pr.id)
            attach("pull_request", pr.id, f"PR #{pr.number}: {pr.title}", env.occurred_at,
                   "Merge commit matches deployment", env.source_url)
        components = {(c.name, c.version, c.ecosystem) for c in session.scalars(
            select(DeploymentComponent).where(DeploymentComponent.deployment_id == deployment.id))}
        matched_behavior = False
        for finding in session.scalars(select(SecurityFinding).where(
            SecurityFinding.repository_id == deployment.repository_id, SecurityFinding.state == "open")):
            env = session.get(Evidence, finding.id)
            if utc(env.occurred_at) > utc(event.occurred_at):
                continue
            exact_commit = finding.commit_sha is not None and finding.commit_sha == deployment.commit_sha
            exact_component = (finding.package_name, finding.package_version, finding.ecosystem) in components
            if not (exact_commit or exact_component):
                continue
            finding_count += 1
            matched_behavior |= finding.behavior == event.event_type
            attach("finding", finding.id, finding.title, env.occurred_at,
                   "Applies to exact deployed commit" if exact_commit else "Exact component and version in deployment manifest",
                   env.source_url)
        if finding_count:
            credit("Security finding matches the deployed commit or exact component", 25)
        else:
            gaps.append("No finding is proven applicable to this deployed commit or exact component version.")
        if deployment.artifact_digest and components:
            credit("Deployment includes an artifact digest and component manifest", 10)
        else:
            gaps.append("Artifact/component provenance is incomplete; dependency exposure cannot be assumed.")
        if matched_behavior:
            credit("Runtime behavior matches the finding's declared behavior", 10)
        else:
            gaps.append("Behavioral relevance of any finding is not established.")
        minutes = (utc(event.occurred_at) - utc(deployment.deployed_at)).total_seconds() / 60
        if minutes <= 60:
            credit("Runtime event occurred within one hour after deployment", 5)
        if not finding_count:
            gaps.append("A deployment link alone does not establish a security relationship.")
    else:
        gaps.append("No successful deployment existed for this service and environment at the event time.")
        gaps.append("Runtime evidence is unlinked; time proximity alone is insufficient.")
    incident.confidence = min(95, sum(c["points"] for c in contributions))
    incident.contributions, incident.gaps = contributions, gaps
    incident.summary = (
        f"{event.event_type} was observed on {event.service_key}. "
        + (f"The event maps to deployed commit {deployment.commit_sha[:8]}, with {finding_count} applicable finding(s). "
           if deployment else "No verified deployment could be linked. ")
        + "These findings may be related. The available evidence does not establish causation."
    )
    session.flush()
    return incident
