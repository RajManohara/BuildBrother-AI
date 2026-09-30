# BuildBrother: two-person delivery plan

## Working MVP delivered

One codebase contains a frontend, API, database migrations, safe demo, GitHub App collector, explicit service/deployment callbacks, deterministic correlation, incident timeline, status/notes, and a cited template analyst. Live GitHub verification requires App credentials configured by the owners.

## Suggested division

| Focus | Teammate A | Teammate B |
| --- | --- | --- |
| Initial integration | GitHub App, collector fixtures, pagination and backoff | Service mapping, deployment callback, runtime fixtures |
| Investigation | Source metadata and component applicability | Timeline, evidence gaps, confidence explanations |
| Quality | Backend/PostgreSQL integration tests | Browser interaction and accessibility tests |
| Next feature | Signed GitHub webhooks and delivery idempotency | Service registration and deployment forms in the UI |

Agree on the Pydantic input contracts first. Work on separate branches, open pull requests, and review each other's changes. Keep the main branch releasable and require CI before merging once branch protections are configured.

## Next milestones

1. Configure the GitHub App and demonstrate one real repository collection twice without duplicates.
2. Register one real service and submit a deployment callback with the exact successful workflow and commit.
3. Send a safe synthetic runtime event for that service, then inspect the evidence chain together.
4. Add verified CycloneDX/SPDX SBOM ingestion and ecosystem-aware version-range evaluation. Until then, do not claim a Dependabot range proves an installed vulnerable version.
5. Add webhook signature validation, delivery deduplication, retry queues, source freshness, and out-of-order reconciliation when GitHub findings arrive after runtime events.
6. Add richer analyst retrieval (component exposure, deployment comparison), optional LLM explanations, and answer-evaluation tests. Keep authoritative confidence in deterministic code.
7. Add user authentication, RBAC, user-attributed audit records, and deployment hardening before hosting for others.

Deferred from the earlier standalone SOC idea: Isolation Forest, MITRE matrix, endpoint-scale ingestion, threat-hunting syntax, and full enterprise SOC analytics. These should follow the combined product's provenance MVP rather than distract from it.
