from sqlalchemy import select
from app.models import Incident
from app.repository import incident_detail


def answer(session, question: str, incident_id: str | None):
    """Retrieval-only template answers; untrusted source text is never an instruction."""
    lower = question.lower()
    if any(word in lower for word in ("malware", "steal", "exploit code", "credential theft", "ransomware")):
        return {"answer": "BuildBrother supports defensive investigation only. Ask about an incident, its evidence, or its recommended review steps.", "citations": [], "mode": "deterministic"}
    if not incident_id:
        incident = session.scalar(select(Incident).where(Incident.status.notin_(["Resolved", "False Positive"]))
                                  .order_by(Incident.confidence.desc(), Incident.created_at.desc()).limit(1))
        incident_id = incident.id if incident else None
    detail = incident_detail(session, incident_id) if incident_id else None
    if not detail:
        return {"answer": "No matching incident is stored. Ingest runtime evidence and a deployment record before requesting an investigation.", "citations": [], "mode": "deterministic"}
    timeline = detail["timeline"]
    citations = [{"id": e["evidence_id"], "label": e["label"], "url": e["source_url"]} for e in timeline]
    if any(term in lower for term in ("before", "changed", "timeline")):
        text = "Stored sequence for this incident:\n" + "\n".join(
            f"• {e['occurred_at'].isoformat()}: {e['label']} [{e['evidence_id']}]" for e in timeline)
    elif any(term in lower for term in ("confidence", "score", "group", "why")):
        text = f"Correlation confidence is {detail['confidence']:.0f}/100.\n" + "\n".join(
            f"• +{c['points']}: {c['label']}" for c in detail["contributions"])
    elif any(term in lower for term in ("action", "investigate", "next", "first")):
        text = f"Review {detail['title']} ({detail['severity']} severity).\n" + "\n".join(
            f"• {action}" for action in detail["recommended_actions"])
    elif any(term in lower for term in ("summary", "summarize", "happened", "explain", "junior")):
        text = detail["summary"]
    else:
        return {"answer": "This MVP supports incident summaries, timelines, confidence explanations, and next investigation steps. Choose one of the suggested questions; broader cross-repository questions are not implemented yet.", "citations": [], "mode": "deterministic"}
    text += "\n\nEvidence gaps:\n" + "\n".join(f"• {gap}" for gap in detail["gaps"])
    text += "\n\nCorrelation does not establish causation. Remediation requires human approval."
    return {"answer": text, "citations": citations, "mode": "deterministic", "incident_id": detail["id"]}
