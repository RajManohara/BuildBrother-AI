from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analyst import answer
from app.ingestion import ingest_deployment, ingest_runtime, register_service
from app.models import Incident, IncidentNote
from app.repository import incident_detail, serialize, workspace
from app.schemas import AnalystQuestion, DeploymentInput, IncidentUpdate, RuntimeInput, ServiceInput
from app.security import require_ingest, require_read, sanitize

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_read)])


def database(request: Request):
    with request.app.state.sessions() as session:
        try:
            yield session
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Conflicting record; retry with a unique source event ID")
        except Exception:
            session.rollback()
            raise


@router.get("/workspace", tags=["Workspace"])
def get_workspace(request: Request, session: Session = Depends(database)):
    return workspace(session, request.app.state.settings)


@router.get("/incidents/{incident_id}", tags=["Incidents"])
def get_incident(incident_id: str, session: Session = Depends(database)):
    detail = incident_detail(session, incident_id)
    if not detail:
        raise HTTPException(404, "Incident not found")
    return detail


@router.post("/services", tags=["Services"], dependencies=[Depends(require_ingest)])
def create_service(data: ServiceInput, session: Session = Depends(database)):
    return serialize(register_service(session, data))


@router.post("/deployments/ingest", tags=["Deployments"], dependencies=[Depends(require_ingest)])
def deployment_ingest(data: DeploymentInput, session: Session = Depends(database)):
    return serialize(ingest_deployment(session, data))


@router.post("/runtime/events", tags=["Runtime"], dependencies=[Depends(require_ingest)])
def runtime_ingest(data: RuntimeInput, session: Session = Depends(database)):
    event, incident = ingest_runtime(session, data)
    return {"event_id": event.id, "incident_id": incident.id, "confidence": incident.confidence}


@router.post("/analyst", tags=["Analyst"])
def analyst(data: AnalystQuestion, session: Session = Depends(database)):
    return answer(session, data.question, data.incident_id)


@router.patch("/incidents/{incident_id}", tags=["Incidents"], dependencies=[Depends(require_ingest)])
def update_incident(incident_id: str, data: IncidentUpdate, session: Session = Depends(database)):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    previous = incident.status
    incident.status = data.status
    session.add(IncidentNote(incident_id=incident.id, text=sanitize(
        f"Status: {previous} → {data.status}. {data.note}")))
    session.flush()
    return incident_detail(session, incident_id)
