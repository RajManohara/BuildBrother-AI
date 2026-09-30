import {
  ArrowRight,
  ArrowUpRight,
  Box,
  GitBranch,
  GitPullRequest,
  Layers,
  Network,
  Radio,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import type { WorkspaceData } from "@/lib/types";
import { Badge, Empty, IncidentTable } from "./evidence-ui";
import { Button } from "./ui/button";
export function Overview({
  data,
  navigate,
  open,
}: {
  data: WorkspaceData;
  navigate: (page: string) => void;
  open: (id: string) => void;
}) {
  const active = data.incidents.filter(
    (i) => !["Resolved", "False Positive"].includes(i.status),
  );
  const featured = [...active].sort((a, b) => b.confidence - a.confidence)[0];
  const failures = data.runs.filter((r) => r.conclusion === "failure").length;
  const linked = data.incidents.filter((i) => i.deployment_id).length;
  const buckets = new Map<
    string,
    { date: string; success: number; failure: number }
  >();
  for (const run of data.runs) {
    const key = run.started_at.slice(0, 10);
    const bucket = buckets.get(key) || { date: key, success: 0, failure: 0 };
    if (run.conclusion === "success") bucket.success++;
    if (run.conclusion === "failure") bucket.failure++;
    buckets.set(key, bucket);
  }
  const days = [...buckets.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-7);
  const maxCount = Math.max(1, ...days.map((d) => d.success + d.failure));
  return (
    <>
      <div className="metrics">
        {[
          {
            label: "Open investigations",
            value: active.length,
            hint: "Security evidence to review",
            icon: ShieldCheck,
          },
          {
            label: "Connected repositories",
            value: data.repositories.length,
            hint: `${data.repositories.filter((r) => r.is_demo).length} synthetic demo repository`,
            icon: GitBranch,
          },
          {
            label: "Tracked deployments",
            value: data.deployments.length,
            hint: "Commit → service provenance",
            icon: Layers,
          },
          {
            label: "Failed workflow runs",
            value: failures,
            hint: "Operational health only",
            icon: Workflow,
          },
        ].map(({ label, value, hint, icon: Icon }) => (
          <div className="metric" key={label}>
            <span>
              {label}
              <Icon size={16} />
            </span>
            <strong>{value.toString().padStart(2, "0")}</strong>
            <small>{hint}</small>
          </div>
        ))}
      </div>
      <div className="overview-grid">
        <section className="panel featured">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PRIORITY INVESTIGATION</span>
              <h2>Follow the evidence.</h2>
            </div>
            <span className="live-dot" />
          </div>
          {featured ? (
            <>
              <div className="feature-title">
                <Badge value={featured.severity} />
                <span>{featured.confidence}% correlation confidence</span>
                <h3>{featured.title}</h3>
                <p>{featured.summary}</p>
              </div>
              <div className="provenance-chain">
                {[
                  { icon: GitPullRequest, name: "Code change" },
                  { icon: Workflow, name: "Build" },
                  { icon: Box, name: "Deployment" },
                  { icon: Radio, name: "Runtime" },
                ].map(({ icon: Icon, name }, index) => (
                  <div className="chain-part" key={name}>
                    <span>
                      <Icon size={20} />
                    </span>
                    <small>{name}</small>
                    {index < 3 && (
                      <ArrowRight className="chain-arrow" size={16} />
                    )}
                  </div>
                ))}
              </div>
              <div className="feature-footer">
                <span>
                  <ShieldCheck size={14} />
                  Evidence-linked. Never assumed.
                </span>
                <Button onClick={() => open(featured.id)}>
                  Investigate <ArrowUpRight size={14} />
                </Button>
              </div>
            </>
          ) : (
            <Empty text="No open incidents. New runtime evidence will appear here." />
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Pipeline pulse</h2>
              <p>Recent workflow outcomes</p>
            </div>
            <span className="muted-tag">OPERATIONS</span>
          </div>
          <div className="pulse-stat">
            <strong>
              {data.runs.length
                ? Math.round(
                    (data.runs.filter((r) => r.conclusion === "success")
                      .length /
                      data.runs.length) *
                      100,
                  )
                : 0}
              <small>%</small>
            </strong>
            <span>
              successful runs
              <br />
              <small>{data.runs.length} stored runs</small>
            </span>
          </div>
          <div
            className="bar-chart"
            role="img"
            aria-label={`${data.runs.length} workflow runs, ${failures} failed`}
          >
            {days.map((day) => (
              <div className="bar-column" key={day.date}>
                <div className="bar-track">
                  <span
                    className="bar-failure"
                    style={{ height: `${(day.failure / maxCount) * 85}px` }}
                  />
                  <span
                    className="bar-success"
                    style={{ height: `${(day.success / maxCount) * 85}px` }}
                  />
                </div>
                <small>
                  {new Date(day.date + "T12:00:00").toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                  })}
                </small>
              </div>
            ))}
          </div>
          <div className="chart-legend">
            <span>
              <i />
              Successful
            </span>
            <span>
              <i />
              Failed
            </span>
            <button onClick={() => navigate("Pipelines")}>
              View pipelines <ArrowRight size={12} />
            </button>
          </div>
        </section>
      </div>
      <section className="panel investigations">
        <div className="panel-heading">
          <div>
            <h2>
              Recent investigations{" "}
              <span className="count">{data.incidents.length}</span>
            </h2>
            <p>
              A clear distinction between observed behavior and inferred
              relationships.
            </p>
          </div>
          <button className="text-button" onClick={() => navigate("Incidents")}>
            View all <ArrowRight size={14} />
          </button>
        </div>
        <IncidentTable items={data.incidents.slice(0, 5)} open={open} />
      </section>
      <div className="bottom-cards">
        <div className="panel small-panel">
          <Network size={24} />
          <div>
            <h3>
              {linked} of {data.incidents.length} investigations have deployment
              provenance
            </h3>
            <p>
              Unlinked evidence stays visible with explicit confidence gaps.
            </p>
          </div>
        </div>
        <div className="panel small-panel">
          <Sparkles size={24} />
          <div>
            <h3>Your investigation companion</h3>
            <p>
              Ask what changed, why evidence was grouped, or what to review.
            </p>
          </div>
          <button
            className="icon-button"
            aria-label="Open AI Analyst"
            onClick={() => navigate("AI Analyst")}
          >
            <ArrowUpRight size={20} />
          </button>
        </div>
      </div>
    </>
  );
}
