"use client";

import { useMemo, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || "http://localhost:8000";

export default function Home() {
  const [prompt, setPrompt] = useState("Build an FAQ chatbot with a clean UI.");
  const [jobId, setJobId] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [status, setStatus] = useState<string>("idle");

  const outputLines = useMemo(() => logs.join("\n"), [logs]);

  const generate = async () => {
    setLogs([]);
    setResult(null);
    const start = await fetch(`${apiBase}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await start.json();
    setJobId(data.job_id);
    setStatus("running");

    const evt = new EventSource(`${apiBase}/api/stream/${data.job_id}`);
    evt.addEventListener("log", (event: MessageEvent) => {
      setLogs((prev) => [...prev, event.data]);
    });
    evt.addEventListener("done", async () => {
      evt.close();
      const st = await fetch(`${apiBase}/api/status/${data.job_id}`);
      const payload = await st.json();
      setStatus(payload.status);
      setResult(payload.result);
    });
  };

  const copy = async (value: string) => navigator.clipboard.writeText(value);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: 20 }}>
      <h1>AI App Factory Console</h1>
      <p>Describe your app and generate a full stack AI application.</p>
      <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={6} style={{ width: "100%" }} />
      <button onClick={generate} style={{ marginTop: 12 }}>Generate App</button>
      <p>Status: {status} {jobId ? `(${jobId})` : ""}</p>
      <h3>Live Logs</h3>
      <pre style={{ background: "#111", color: "#0f0", minHeight: 220, padding: 12 }}>{outputLines}</pre>

      {result && (
        <section>
          <h3>Output URLs</h3>
          <ul>
            <li>Frontend: {result.frontend_url} <button onClick={() => copy(result.frontend_url)}>Copy</button></li>
            <li>Backend: {result.backend_url} <button onClick={() => copy(result.backend_url)}>Copy</button></li>
            <li>Docs: {result.docs_url} <button onClick={() => copy(result.docs_url)}>Copy</button></li>
          </ul>
          <h4>Validation Checklist</h4>
          <ul>{result.validation?.map((item: string) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}
    </main>
  );
}
