export type Repository = {
  id: string;
  full_name: string;
  source_url: string;
  default_branch: string;
  is_demo: boolean;
  collected_at: string | null;
};
export type Run = {
  id: string;
  repository_id: string;
  source_run_id: number;
  name: string;
  head_sha: string;
  status: string;
  conclusion: string | null;
  branch: string;
  started_at: string;
};
export type Finding = {
  id: string;
  repository_id: string;
  title: string;
  severity: string;
  state: string;
  commit_sha: string | null;
  package_name: string | null;
  package_version: string | null;
};
export type Service = {
  key: string;
  name: string;
  environment: string;
  criticality: string;
  is_demo: boolean;
};
export type Deployment = {
  id: string;
  source_event_id: string;
  repository_id: string;
  service_key: string;
  environment: string;
  commit_sha: string;
  workflow_run_id: string | null;
  artifact_digest: string | null;
  artifact_uri: string | null;
  deployed_at: string;
  status: string;
  source: string;
};
export type RuntimeEvent = {
  id: string;
  source: string;
  source_event_id: string;
  service_key: string;
  asset_key: string;
  environment: string;
  event_type: string;
  severity: string;
  occurred_at: string;
  attributes: Record<string, unknown>;
};
export type Incident = {
  id: string;
  title: string;
  severity: string;
  confidence: number;
  status: string;
  created_at: string;
  runtime_event_id: string;
  deployment_id: string | null;
  contributions: { label: string; points: number }[];
  gaps: string[];
  summary: string;
};
export type Evidence = {
  evidence_id: string;
  kind: string;
  label: string;
  occurred_at: string;
  relationship: string;
  source_url: string;
};
export type IncidentDetail = Incident & {
  timeline: Evidence[];
  runtime_event: RuntimeEvent;
  deployment: Deployment | null;
  notes: { id: string; text: string; created_at: string }[];
  recommended_actions: string[];
};
export type WorkspaceData = {
  repositories: Repository[];
  runs: Run[];
  findings: Finding[];
  services: Service[];
  deployments: Deployment[];
  events: RuntimeEvent[];
  incidents: Incident[];
  commits: {
    id: string;
    repository_id: string;
    sha: string;
    message: string;
    changed_paths: string[];
  }[];
  pull_requests: {
    id: string;
    repository_id: string;
    number: number;
    title: string;
    state: string;
    changed_paths: string[];
  }[];
  jobs: {
    id: string;
    workflow_run_id: string;
    name: string;
    conclusion: string | null;
    steps: { name: string; conclusion: string }[];
  }[];
  source_urls: Record<string, string>;
  collection: {
    resource: string;
    state: string;
    last_success_at: string | null;
    next_attempt_at: string | null;
    rate_remaining: number | null;
  }[];
  settings: {
    demo_mode: boolean;
    github_repository: string;
    github_configured: boolean;
    ingestion_configured: boolean;
    analyst_mode: string;
    scope: string;
    limit: number;
  };
};
export type AnalystAnswer = {
  answer: string;
  citations: { id: string; label: string; url: string }[];
  mode: string;
  incident_id?: string;
};
