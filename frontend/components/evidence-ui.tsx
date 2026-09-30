import { ArrowUpRight, Box, ExternalLink } from "lucide-react";
import type { Incident } from "@/lib/types";
export const formatTime = (value: string) =>
  new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
export const short = (value: string) => value.slice(0, 8);
export function SourceLink({ url }: { url?: string }) {
  if (!url?.startsWith("https://github.com/")) return null;
  return (
    <a className="source-link" href={url} target="_blank" rel="noreferrer">
      Source <ExternalLink size={12} />
    </a>
  );
}
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge badge-${value.toLowerCase().replaceAll(" ", "-")}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function Empty({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <Box size={28} />
      <p>{text}</p>
    </div>
  );
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Request validation failed. Check the submitted fields.",
    );
  return data;
}
export function IncidentTable({
  items,
  open,
}: {
  items: Incident[];
  open: (id: string) => void;
}) {
  return items.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Investigation</th>
            <th>Severity</th>
            <th>Correlation</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id}>
              <td>
                <button className="row-link" onClick={() => open(i.id)}>
                  {i.title}
                </button>
                <small>
                  {formatTime(i.created_at)} · {short(i.id)}
                </small>
              </td>
              <td>
                <Badge value={i.severity} />
              </td>
              <td>
                <div className="confidence-mini">
                  <span>{i.confidence}%</span>
                  <div>
                    <i style={{ width: `${i.confidence}%` }} />
                  </div>
                </div>
              </td>
              <td>
                <Badge value={i.status} />
              </td>
              <td>
                <button
                  className="icon-button"
                  aria-label={`Investigate ${i.title}`}
                  onClick={() => open(i.id)}
                >
                  <ArrowUpRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty text="No matching investigations. Runtime evidence creates an investigation when ingested." />
  );
}
