import { cpSync } from "node:fs";
import { loadEnvFile } from "node:process";

try {
  loadEnvFile(new URL("../.env.local", import.meta.url));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}

// Next.js standalone output omits static assets; include them for local production runs.
cpSync(
  new URL("../.next/static", import.meta.url),
  new URL("../.next/standalone/.next/static", import.meta.url),
  { recursive: true },
);
process.env.HOSTNAME ||= "127.0.0.1";
await import("../.next/standalone/server.js");
