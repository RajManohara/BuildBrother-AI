# Security boundaries

This is a **single-workspace local MVP**. No per-user authentication, roles, or tenant isolation are implemented. The frontend is a trusted local client and holds server-only backend credentials. Binding it publicly would give visitors access to that workspace; do not do so.

- Docker publishes only on loopback. Direct local startup instructions also bind loopback.
- APP_API_KEY gates backend workspace reads when configured. INGEST_TOKEN is a distinct write credential. The setup script generates both; neither enters browser bundles.
- The frontend server proxy uses a fixed backend URL and an explicit route allowlist. Browser writes require JSON and a matching Origin.
- Pydantic forbids unknown fields, enforces aware timestamps and bounded fields, and validates SHA/digest syntax. Timestamp offsets are normalized to UTC.
- Ingestion bodies are limited to 1 MiB. Mutations have a bounded in-memory 60/minute/client limiter. Distributed deployments need shared rate limiting.
- Database queries use SQLAlchemy parameters. No source-controlled code or event text is executed.
- Incoming evidence is sanitized and hashed. Common token formats, private keys, sensitive fields and credential assignments are redacted; this is defense in depth, not a guarantee that arbitrary free text is secret-free.
- No full GitHub job logs or secret-scanning payloads are collected. The collector stores safe metadata, step outcomes and source links.
- GitHub URLs are restricted to HTTPS github.com. API collection has a fixed origin and does not follow redirects.
- Source text is untrusted. The current analyst uses deterministic retrieval/templates, so source instructions cannot trigger tool calls. Future LLM integration needs a separate prompt-injection and data-exfiltration review.
- The analyst cannot change repositories, rerun workflows, dismiss alerts, isolate endpoints, deploy fixes, or infer causation.
- Idempotency keys cannot be reused with conflicting runtime/deployment data. Database uniqueness constraints protect against racing inserts.
- A repository-to-service mapping is mandatory. Correlation requires the same service/environment and the latest successful deployment before the event. Failed deployments are not selected.
- App credentials live in gitignored environment files. `.pem` and `.key` files are also ignored. Use a secret manager and rotation procedures for a hosted deployment.

Still needed before production: SSO/RBAC, authenticated user audit identity, tenant isolation, secure HTTPS ingress, retention/deletion policies, structured security logging, schema evolution procedures, stronger source attestation, distributed ingestion, dependency audit tooling, and operational monitoring.
