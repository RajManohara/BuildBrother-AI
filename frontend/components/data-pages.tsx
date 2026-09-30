import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Code2,
  GitBranch,
  GitCommitHorizontal,
  Layers,
  Radio,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import type { WorkspaceData } from "@/lib/types";
import { Badge, Empty, SourceLink, formatTime, short } from "./evidence-ui";
import { Button } from "./ui/button";
type Props = {
  data: WorkspaceData;
  search: string;
  navigate: (page: string) => void;
  open: (id: string) => void;
};
export function Repositories({ data, search, navigate }: Props) {
  const match = (v: unknown) =>
    JSON.stringify(v).toLowerCase().includes(search.toLowerCase());
  return (
    <div className="repository-grid">
      {data.repositories.filter(match).map((repo) => (
        <section className="panel repository-card" key={repo.id}>
          <div className="repo-header">
            <GitBranch size={23} />
            <Badge value={repo.is_demo ? "synthetic" : "GitHub"} />
          </div>
          <h2>{repo.full_name}</h2>
          <p>
            {repo.default_branch} ·{" "}
            {repo.collected_at
              ? `Collected ${formatTime(repo.collected_at)}`
              : "Safe synthetic demonstration"}
          </p>
          <div className="repo-stats">
            <div>
              <strong>
                {data.runs.filter((r) => r.repository_id === repo.id).length}
              </strong>
              <small>Workflow runs</small>
            </div>
            <div>
              <strong>
                {
                  data.findings.filter(
                    (f) => f.repository_id === repo.id && f.state === "open",
                  ).length
                }
              </strong>
              <small>Stored open findings</small>
            </div>
            <div>
              <strong>
                {data.commits.filter((c) => c.repository_id === repo.id).length}
              </strong>
              <small>Commits</small>
            </div>
          </div>
          <h3>Recent changes</h3>
          {data.commits
            .filter((c) => c.repository_id === repo.id)
            .slice(0, 4)
            .map((c) => (
              <div className="change-row" key={c.id}>
                <GitCommitHorizontal size={17} />
                <div>
                  {c.message}
                  <small>
                    <code>{short(c.sha)}</code> ·{" "}
                    {c.changed_paths.join(", ") || "Paths not collected"}
                  </small>
                </div>
                <SourceLink url={data.source_urls[c.id]} />
              </div>
            ))}
          <h3>Security findings</h3>
          {data.findings
            .filter((f) => f.repository_id === repo.id)
            .map((f) => (
              <div className="change-row" key={f.id}>
                <ShieldCheck size={17} />
                <div>
                  {f.title}
                  <small>
                    {f.package_name || "Commit finding"} · {f.state}
                  </small>
                </div>
                <Badge value={f.severity} />
              </div>
            ))}
          <div className="card-footer">
            <SourceLink url={repo.source_url} />
            <button
              className="text-button"
              onClick={() => navigate("Pipelines")}
            >
              Explore pipelines <ArrowRight size={14} />
            </button>
          </div>
        </section>
      ))}
      {!data.repositories.filter(match).length && (
        <Empty text="No matching repositories. Configure the GitHub App and run the collector to import yours." />
      )}
      <section className="panel connection-card">
        <Code2 size={27} />
        <h2>Bring your own repository</h2>
        <p>
          Connect a GitHub App with read-only permissions, then run the
          collector. No repository changes or workflow reruns are performed.
        </p>
        <code>{data.settings.github_repository}</code>
        <Button variant="outline" onClick={() => navigate("Settings")}>
          Connection setup <ArrowRight size={14} />
        </Button>
      </section>
    </div>
  );
}
export function Pipelines({ data, search }: Props) {
  const [selected, setSelected] = useState("");
  const runs = data.runs.filter((r) =>
    JSON.stringify(r).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Workflow runs</h2>
          <p>Failures affect operational health, never security severity.</p>
        </div>
        <Workflow size={20} />
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Workflow</th>
              <th>Commit / branch</th>
              <th>Outcome</th>
              <th>Started</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <button
                    className="row-link"
                    onClick={() =>
                      setSelected(selected === run.id ? "" : run.id)
                    }
                  >
                    {run.name} #{run.source_run_id}
                  </button>
                  <small>
                    {
                      data.repositories.find((r) => r.id === run.repository_id)
                        ?.full_name
                    }
                  </small>
                  {selected === run.id && (
                    <div className="job-list">
                      {data.jobs
                        .filter((j) => j.workflow_run_id === run.id)
                        .map((j) => (
                          <div key={j.id}>
                            <strong>{j.name}</strong>
                            <Badge value={j.conclusion || "pending"} />
                            {j.steps.map((s, index) => (
                              <small key={index}>
                                {s.name}: {s.conclusion || "pending"}
                              </small>
                            ))}
                          </div>
                        ))}
                    </div>
                  )}
                </td>
                <td>
                  <code>{short(run.head_sha)}</code>
                  <small>{run.branch}</small>
                </td>
                <td>
                  <Badge value={run.conclusion || run.status} />
                </td>
                <td>{formatTime(run.started_at)}</td>
                <td>
                  <SourceLink url={data.source_urls[run.id]} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!runs.length && <Empty text="No workflow runs match this search." />}
    </section>
  );
}
export function Services({ data, search }: Props) {
  const [selected, setSelected] = useState("");
  const match = (v: unknown) =>
    JSON.stringify(v).toLowerCase().includes(search.toLowerCase());
  return (
    <>
      <div className="service-grid">
        {data.services.filter(match).map((service) => {
          const current = data.deployments.find(
            (d) =>
              d.service_key === service.key &&
              d.status === "succeeded" &&
              new Date(d.deployed_at) <= new Date(),
          );
          return (
            <button
              className={`panel service-card ${selected === service.key ? "selected" : ""}`}
              onClick={() =>
                setSelected(selected === service.key ? "" : service.key)
              }
              key={service.key}
            >
              <div>
                <Layers size={22} />
                <Badge
                  value={service.is_demo ? "synthetic" : service.environment}
                />
              </div>
              <h2>{service.name}</h2>
              <p>
                {service.key} · {service.environment}
              </p>
              <div className="deployed-commit">
                <span>ACTIVE COMMIT</span>
                <strong>
                  {current ? short(current.commit_sha) : "Unlinked"}
                </strong>
                <small>
                  {current
                    ? formatTime(current.deployed_at)
                    : "No successful deployment recorded"}
                </small>
              </div>
            </button>
          );
        })}
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Deployment ledger</h2>
            <p>
              {selected
                ? `Filtered to ${selected}; click the service again to clear.`
                : "Each record links a commit, artifact, and service."}
            </p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Service / environment</th>
                <th>Commit</th>
                <th>Artifact digest</th>
                <th>Outcome</th>
                <th>Deployed</th>
              </tr>
            </thead>
            <tbody>
              {data.deployments
                .filter(
                  (d) => (!selected || d.service_key === selected) && match(d),
                )
                .map((d) => (
                  <tr key={d.id}>
                    <td>
                      {d.service_key}
                      <small>{d.environment}</small>
                    </td>
                    <td>
                      <code>{short(d.commit_sha)}</code>
                    </td>
                    <td>
                      <code title={d.artifact_digest || "Not supplied"}>
                        {d.artifact_digest
                          ? `${d.artifact_digest.slice(0, 19)}…`
                          : "Not supplied"}
                      </code>
                      <small>
                        {d.workflow_run_id
                          ? "Verified workflow linked"
                          : "Workflow not linked"}
                      </small>
                    </td>
                    <td>
                      <Badge value={d.status} />
                    </td>
                    <td>{formatTime(d.deployed_at)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
export function Runtime({ data, search, open }: Props) {
  const events = data.events.filter((e) =>
    JSON.stringify(e).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Runtime evidence</h2>
          <p>Synthetic demo sources are identified explicitly.</p>
        </div>
        <Radio size={20} />
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Service / asset</th>
              <th>Severity</th>
              <th>Observed</th>
              <th>Investigation</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>
                  {event.event_type}
                  <small>
                    <Badge value={event.source} />
                  </small>
                </td>
                <td>
                  {event.service_key}
                  <small>{event.asset_key}</small>
                </td>
                <td>
                  <Badge value={event.severity} />
                </td>
                <td>{formatTime(event.occurred_at)}</td>
                <td>
                  {data.incidents.find(
                    (i) => i.runtime_event_id === event.id,
                  ) && (
                    <button
                      className="text-button"
                      onClick={() =>
                        open(
                          data.incidents.find(
                            (i) => i.runtime_event_id === event.id,
                          )!.id,
                        )
                      }
                    >
                      View incident <ArrowUpRight size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!events.length && <Empty text="No runtime events match this search." />}
    </section>
  );
}
export function WorkspaceSettings({ data }: { data: WorkspaceData }) {
  return (
    <div className="settings-grid">
      <section className="panel settings-panel">
        <h2>GitHub integration</h2>
        <p>
          One repository, read-only collection. Credentials remain on the
          server.
        </p>
        <dl>
          <dt>Repository</dt>
          <dd>{data.settings.github_repository}</dd>
          <dt>GitHub App</dt>
          <dd>
            <Badge
              value={
                data.settings.github_configured
                  ? "configured"
                  : "not configured"
              }
            />
          </dd>
          <dt>Collection interval</dt>
          <dd>Worker default: 5 minutes</dd>
          <dt>Deployment linking</dt>
          <dd>Authenticated callback and registered service</dd>
        </dl>
        <div className="setup-guide">
          <h3>Connect your repository</h3>
          <ol>
            <li>
              Create a GitHub App with read access to Contents, Pull requests,
              Actions, Deployments, Dependabot alerts, and Code scanning alerts.
            </li>
            <li>Install it only on the repository you want to investigate.</li>
            <li>
              Set GITHUB_APP_ID, GITHUB_INSTALLATION_ID, and GITHUB_PRIVATE_KEY
              in your local environment file.
            </li>
            <li>
              Run the collector worker. See docs/GITHUB_SETUP.md in the
              repository.
            </li>
          </ol>
        </div>
      </section>
      <section className="panel settings-panel">
        <h2>Workspace safeguards</h2>
        <dl>
          <dt>Data mode</dt>
          <dd>
            {data.settings.demo_mode
              ? "Includes labeled synthetic demo"
              : "Collected data only"}
          </dd>
          <dt>Runtime ingestion</dt>
          <dd>
            <Badge
              value={
                data.settings.ingestion_configured
                  ? "configured"
                  : "not configured"
              }
            />
          </dd>
          <dt>AI Analyst</dt>
          <dd>Deterministic evidence templates</dd>
          <dt>Access scope</dt>
          <dd>{data.settings.scope}</dd>
          <dt>External actions</dt>
          <dd>None. Recommendations only.</dd>
        </dl>
        <div className="setup-guide">
          <h3>For you and your teammate</h3>
          <p>
            Clone the repository and run the demo locally. Use your own
            gitignored environment file. Never commit private keys or ingestion
            credentials.
          </p>
          <p>
            This MVP has no user accounts or tenant isolation. Keep it on
            localhost.
          </p>
        </div>
      </section>
      <section className="panel collection-panel">
        <div className="panel-heading">
          <div>
            <h2>Collector status</h2>
            <p>
              Unavailable permissions remain visible; they never mean zero
              findings.
            </p>
          </div>
        </div>
        {data.collection.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>State</th>
                  <th>Last success</th>
                  <th>Requests remaining</th>
                </tr>
              </thead>
              <tbody>
                {data.collection.map((c) => (
                  <tr key={c.resource}>
                    <td>
                      <code>{c.resource}</code>
                    </td>
                    <td>
                      <Badge value={c.state} />
                    </td>
                    <td>
                      {c.last_success_at
                        ? formatTime(c.last_success_at)
                        : "Never"}
                    </td>
                    <td>{c.rate_remaining ?? "Unknown"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty text="No GitHub collection has run. The current demo does not require GitHub credentials." />
        )}
      </section>
    </div>
  );
}
