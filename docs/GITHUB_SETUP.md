# Connect BuildBrother to GitHub

BuildBrother uses the REST API for durable scheduled collection. A GitHub MCP connection is optional for ad hoc developer investigation; it is not required to run this application and does not supply credentials to the collector.

## 1. Register and install your App

In GitHub, open Settings → Developer settings → GitHub Apps → New GitHub App. Choose a unique name (for example, BuildBrother Development), set the homepage to your repository, disable webhooks for this polling MVP, and restrict installation to your account.

Request repository permissions at **read-only** level:

- Contents: commit and changed-path metadata.
- Pull requests: PR metadata and changed files.
- Actions: workflow runs, jobs and step outcomes.
- Deployments: deployment records and statuses.
- Dependabot alerts: dependency findings, where available.
- Code scanning alerts: code-scanning findings, where available.

Metadata read access is implicit. Checks and Secret scanning are not used by this MVP and should not be requested. The collector does not download full job logs, avoiding unnecessary secret-bearing log storage.

Install the App only on `RajManohara/BuildBrother-AI` (or another explicitly selected repository). Enabling security features and repository settings remains a user-managed step. A missing permission or unavailable feature is shown as unavailable rather than interpreted as an absence of risk.

## 2. Configure your local server

Run `python scripts/setup_local.py` first. In the gitignored root `.env`, set:

```dotenv
GITHUB_APP_ID=your-app-id
GITHUB_INSTALLATION_ID=your-installation-id
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_REPOSITORY=RajManohara/BuildBrother-AI
GITHUB_API_VERSION=2026-03-10
```

Download the App private key from its GitHub settings. Store it locally, do not commit it, and do not send it through chat. The installation ID appears in the URL when viewing the installed App. The backend signs a short-lived JWT and exchanges it for an installation token, cached in memory and refreshed before expiry.

## 3. Collect and verify

From `backend`, apply migrations and run:

```powershell
.\.venv\Scripts\python -m app.bootstrap
.\.venv\Scripts\python -m app.worker --once
```

Open Repositories and Settings in the dashboard, then Refresh. Run the collector a second time and confirm source records are updated rather than duplicated. To keep polling, omit `--once` or use the Compose `github` profile. Run only one collector with SQLite; PostgreSQL uses an advisory lock.

For 403/404 resource errors, inspect permissions, installation selection, and feature availability. For rate limits, wait for the recorded backoff; do not create additional tokens to bypass it. Large backfills stop explicitly at 5,000 records per resource rather than claiming completeness.

## 4. Establish deployment provenance

Register your service using `POST /api/v1/services` after the repository is collected. Have your trusted deployment process submit `POST /api/v1/deployments/ingest` after successful deployment. A workflow reference must be collected, successful, and match both the repository and deployed commit. A missing workflow can be recorded, but lowers correlation confidence.

The callback credential is INGEST_TOKEN, not the GitHub App private key. APP_API_KEY is required separately if configured. The callback targets BuildBrother; BuildBrother never reruns or modifies the GitHub workflow. Do not expose the unauthenticated frontend to receive callbacks from the public internet—use a secured deployment of the API when moving beyond localhost.

## MCP later

Use a separate read-only credential with the [official GitHub MCP server](https://github.com/github/github-mcp-server) if you want interactive investigation through an MCP-compatible client. Keep that credential separate from the collector's App key. MCP is not configured automatically by this repository.

References: [GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app), [installation-token authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app), [REST API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions).
