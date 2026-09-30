# API examples

Use a local REST client and the values from your gitignored `.env`. Include:

```http
Content-Type: application/json
X-API-Key: <APP_API_KEY>
Authorization: Bearer <INGEST_TOKEN>
```

Do not commit those headers with real values. Read endpoints require only X-API-Key; writes require both when APP_API_KEY is configured.

## Register a service after collecting a repository

`POST http://localhost:8000/api/v1/services`

```json
{"key":"my-api","name":"My API","environment":"staging","repository":"RajManohara/BuildBrother-AI","criticality":"high"}
```

## Record a deployment

`POST http://localhost:8000/api/v1/deployments/ingest`

```json
{
  "source_event_id":"release-2026-09-28-001",
  "service_key":"my-api",
  "environment":"staging",
  "repository":"RajManohara/BuildBrother-AI",
  "commit_sha":"replace-with-actual-40-character-commit-sha",
  "workflow_run_id":811,
  "deployed_at":"2026-09-28T18:30:00Z",
  "status":"succeeded",
  "components":[]
}
```

Replace the SHA, workflow run ID and timestamp with actual values. The example is a template and intentionally fails SHA validation until replaced. Omit workflow_run_id if genuinely unavailable; never invent it. An optional artifact_digest must be `sha256:` plus 64 lowercase hex characters. Components require name, version and ecosystem; they should come from the deployed artifact's manifest, not an assumption about the repository.

## Ingest safe runtime evidence

`POST http://localhost:8000/api/v1/runtime/events`

```json
{
  "source":"synthetic",
  "source_event_id":"my-api-demo-001",
  "service_key":"my-api",
  "asset_key":"pod/my-api-demo",
  "environment":"staging",
  "event_type":"network.unusual_outbound",
  "severity":"medium",
  "occurred_at":"2026-09-28T18:49:00Z",
  "attributes":{"destination":"198.51.100.24","baseline_deviation":0.91}
}
```

Use an actual current or past aware timestamp. The documentation IP is synthetic; no network traffic is generated. Repeat the identical source ID and payload to verify idempotency. Reusing that ID with different contents returns 409.

## Ask about an incident

`POST http://localhost:8000/api/v1/analyst`

```json
{"question":"Why were these items grouped?","incident_id":"replace-with-stored-incident-id"}
```

Omit incident_id to select the highest-confidence open incident. Supported templates cover chronology, confidence, summary, and next investigation steps. Answers contain evidence IDs and source URLs when available.
