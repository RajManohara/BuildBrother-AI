import { useState } from "react";
import {
  ArrowUpRight,
  Box,
  Check,
  CircleAlert,
  GitCommitHorizontal,
  GitPullRequest,
  LoaderCircle,
  Network,
  Radio,
  Send,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import type { AnalystAnswer, Incident, IncidentDetail } from "@/lib/types";
import { api, Badge, formatTime, short, SourceLink } from "./evidence-ui";
import { Button } from "./ui/button";
export function Investigation({
  detail,
  canWrite,
  back,
  onUpdate,
  discuss,
  onError,
}: {
  detail: IncidentDetail;
  canWrite: boolean;
  back: () => void;
  onUpdate: (value: IncidentDetail) => void;
  discuss: () => void;
  onError: (message: string) => void;
}) {
  const [status, setStatus] = useState(detail.status);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    try {
      onUpdate(
        await api<IncidentDetail>(`incidents/${detail.id}`, "PATCH", {
          status,
          note,
        }),
      );
      setNote("");
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="investigation-heading">
        <button className="text-button" onClick={back}>
          ← All investigations
        </button>
        <div>
          <Badge value={detail.runtime_event.source} />
          <Badge value={detail.severity} />
          <Badge value={detail.status} />
        </div>
      </div>
      <section className="panel incident-summary">
        <div>
          <span className="eyebrow">INCIDENT · {short(detail.id)}</span>
          <h2>{detail.title}</h2>
          <p>{detail.summary}</p>
        </div>
        <div className="score-ring">
          <strong>
            {detail.confidence}
            <small>/100</small>
          </strong>
          <span>Correlation confidence</span>
        </div>
      </section>
      <div className="investigation-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>The evidence trail</h2>
              <p>Ordered by source time. Follow each relationship.</p>
            </div>
            <Network size={20} />
          </div>
          <div className="timeline">
            {detail.timeline.map((e) => (
              <div className="timeline-item" key={e.evidence_id}>
                <span className={`timeline-dot dot-${e.kind}`}>
                  <EvidenceIcon kind={e.kind} />
                </span>
                <div>
                  <div className="timeline-meta">
                    <span>{e.kind.replaceAll("_", " ")}</span>
                    <time>{formatTime(e.occurred_at)}</time>
                  </div>
                  <h3>{e.label}</h3>
                  <p>{e.relationship}</p>
                  <div className="evidence-id">
                    <code>{short(e.evidence_id)}</code>
                    <SourceLink url={e.source_url} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
        <div className="investigation-aside">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Why these items were grouped</h2>
                <p>Deterministic contributions, not an AI verdict.</p>
              </div>
            </div>
            <div className="contributions">
              {detail.contributions.map((c) => (
                <div key={c.label}>
                  <span>{c.label}</span>
                  <strong>+{c.points}</strong>
                  <div>
                    <i style={{ width: `${(c.points / 30) * 100}%` }} />
                  </div>
                </div>
              ))}
              {!detail.contributions.length && (
                <p>No verified provenance. Confidence remains zero.</p>
              )}
            </div>
          </section>
          <section className="panel gaps">
            <h2>
              <CircleAlert size={17} />
              Evidence gaps
            </h2>
            {detail.gaps.map((g) => (
              <p key={g}>{g}</p>
            ))}
            {!detail.gaps.length && (
              <p>
                The recorded chain is complete. This still does not establish
                causation or independently verify source truth.
              </p>
            )}
          </section>
        </div>
      </div>
      <div className="investigation-grid">
        <section className="panel actions-panel">
          <h2>Recommended investigation</h2>
          {detail.recommended_actions.map((action, index) => (
            <div key={action}>
              <span>{index + 1}</span>
              <p>{action}</p>
            </div>
          ))}
          <Button variant="outline" onClick={discuss}>
            Discuss with AI Analyst <Sparkles size={15} />
          </Button>
        </section>
        <section className="panel workflow-panel">
          <h2>Investigation workflow</h2>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {[
                "New",
                "Investigating",
                "Contained",
                "Resolved",
                "False Positive",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Analyst note
            <textarea
              maxLength={2000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="What did you verify?"
            />
          </label>
          <Button onClick={save} disabled={busy || !canWrite}>
            {busy ? "Saving…" : "Save investigation"}
          </Button>
          <small>
            Updates the record only. No infrastructure action is taken.
          </small>
          {detail.notes.map((n) => (
            <div className="audit-note" key={n.id}>
              <time>{formatTime(n.created_at)}</time>
              <p>{n.text}</p>
            </div>
          ))}
        </section>
      </div>
      <details className="panel raw-evidence">
        <summary>Raw runtime evidence</summary>
        <pre>{JSON.stringify(detail.runtime_event, null, 2)}</pre>
      </details>
    </>
  );
}
function EvidenceIcon({ kind }: { kind: string }) {
  const Icon =
    kind === "pull_request"
      ? GitPullRequest
      : kind === "commit"
        ? GitCommitHorizontal
        : kind === "workflow"
          ? Workflow
          : kind === "deployment"
            ? Box
            : kind === "finding"
              ? ShieldCheck
              : Radio;
  return <Icon size={17} />;
}
export function Analyst({
  incidents,
  initialIncident,
  onError,
}: {
  incidents: Incident[];
  initialIncident: string;
  onError: (message: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [context, setContext] = useState(initialIncident);
  const [answer, setAnswer] = useState<AnalystAnswer>();
  const [busy, setBusy] = useState(false);
  async function ask(text = question) {
    if (!text.trim()) return;
    setQuestion(text);
    setBusy(true);
    try {
      setAnswer(
        await api<AnalystAnswer>("analyst", "POST", {
          question: text,
          incident_id: context || undefined,
        }),
      );
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="analyst-layout">
      <section className="panel analyst-main">
        <div className="analyst-brand">
          <span>
            <Sparkles size={26} />
          </span>
          <Badge value="Evidence templates" />
        </div>
        <h2>Let’s connect the dots.</h2>
        <p>
          Choose an investigation and ask what happened, why it was grouped, or
          what to review next.
        </p>
        <label className="context-select">
          INVESTIGATION CONTEXT
          <select
            value={context}
            onChange={(e) => {
              setContext(e.target.value);
              setAnswer(undefined);
            }}
          >
            <option value="">Highest-confidence open investigation</option>
            {incidents.map((i) => (
              <option value={i.id} key={i.id}>
                {i.title}
              </option>
            ))}
          </select>
        </label>
        <div className="question-chips">
          {[
            "What changed before this event?",
            "Why were these items grouped?",
            "What should I investigate next?",
            "Summarize this incident",
          ].map((q) => (
            <button key={q} onClick={() => ask(q)} disabled={busy}>
              {q}
              <ArrowUpRight size={13} />
            </button>
          ))}
        </div>
        {answer && (
          <div className="analyst-answer" aria-live="polite">
            <div>
              <Sparkles size={17} />
              <strong>BuildBrother AI</strong>
              <span>Retrieved evidence · deterministic</span>
            </div>
            <p>{answer.answer}</p>
            <h3>Evidence cited</h3>
            <div className="citations">
              {answer.citations.map((c) => (
                <span key={c.id}>
                  <code>{short(c.id)}</code>
                  {c.label}
                  <SourceLink url={c.url} />
                </span>
              ))}
            </div>
          </div>
        )}
        <form
          className="ask-form"
          onSubmit={(e) => {
            e.preventDefault();
            void ask();
          }}
        >
          <input
            aria-label="Ask the analyst"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={1500}
            placeholder="Ask about the evidence…"
          />
          <button
            aria-label="Send question"
            disabled={busy || !question.trim()}
          >
            {busy ? (
              <LoaderCircle size={18} className="spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>
        <small className="analyst-disclaimer">
          Answers use stored records. No external model, code execution, or
          autonomous remediation.
        </small>
      </section>
      <aside className="panel analyst-guide">
        <ShieldCheck size={25} />
        <h2>A second set of eyes.</h2>
        <p>
          The analyst helps explain evidence; it does not decide whether a
          system is compromised.
        </p>
        <div>
          <Check size={16} />
          Cites stored evidence IDs
        </div>
        <div>
          <Check size={16} />
          Explains confidence gaps
        </div>
        <div>
          <Check size={16} />
          Keeps actions human-approved
        </div>
        <div>
          <Check size={16} />
          Works without an AI API key
        </div>
      </aside>
    </div>
  );
}
