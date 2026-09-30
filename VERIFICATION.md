# BuildBrother AI verification

Validated locally on September 29, 2026:

- **21 backend tests passed**; **1 PostgreSQL integration test skipped** because no dedicated PostgreSQL test database was available.
- Alembic upgrade/downgrade/upgrade test passed. `alembic check` reported no schema drift.
- Next.js production build and TypeScript checks passed.
- Docker Compose configuration validated successfully.
- Browser verified: dashboard populated from the API; a synthetic event was ingested and correlated; incident status and an audit note were saved; the analyst returned a confidence explanation with evidence IDs; pipeline search and job expansion worked.
- Desktop and 390px mobile layouts were inspected.
- Local secrets and database files are gitignored. No GitHub App key is bundled with the repository.

## What is not verified here

- Docker's Linux engine was unavailable. Full Compose image startup and local PostgreSQL execution could not be exercised. The GitHub Actions workflow includes a dedicated PostgreSQL integration job.
- Live GitHub App collection requires the owners' App credentials. Collector behavior was tested using mocked GitHub responses; it is not represented as live-account validation.
- This is a local, single-workspace MVP. Public hosting, SSO/RBAC, tenant isolation, verified SBOM ingestion, webhooks, full log analysis and external LLM integration are not implemented.

The backend test runner emits one upstream Starlette/httpx TestClient deprecation warning; tests still pass.
