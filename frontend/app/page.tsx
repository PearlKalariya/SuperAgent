"use client";

import { FormEvent, KeyboardEvent, ReactNode, useMemo, useRef, useState } from "react";
import { Bot, CircleStop, Database, FileUp, Play, Search, Wrench } from "lucide-react";
import { streamQuery, uploadDocument } from "@/lib/api";
import type { Citation, DocumentIngestResponse, StreamEvent, ToolTrace } from "@/lib/types";

type RunState = "idle" | "streaming" | "complete" | "error";

export default function Home() {
  const [query, setQuery] = useState("Show me how this SuperAgent workflow should run.");
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState("Ready");
  const [runState, setRunState] = useState<RunState>("idle");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [toolTraces, setToolTraces] = useState<ToolTrace[]>([]);
  const [documents, setDocuments] = useState<DocumentIngestResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const sessionId = useMemo(() => `session-${Math.random().toString(36).slice(2)}`, []);

  async function submitQuery(event?: FormEvent) {
    event?.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || runState === "streaming") {
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;
    setRunState("streaming");
    setAnswer("");
    setEvents([]);
    setCitations([]);
    setToolTraces([]);
    setStatus("Starting workflow");

    try {
      await streamQuery({
        query: trimmedQuery,
        sessionId,
        signal: controller.signal,
        onEvent: handleEvent
      });
      setRunState("complete");
      setStatus("Completed");
    } catch (error) {
      if (controller.signal.aborted) {
        setRunState("idle");
        setStatus("Stopped");
        return;
      }
      setRunState("error");
      setStatus(error instanceof Error ? error.message : "Streaming failed");
    }
  }

  function handleEvent(event: StreamEvent) {
    setEvents((current) => [event, ...current].slice(0, 12));

    if (event.type === "status") {
      setStatus(String(event.payload.message ?? "Working"));
    }

    if (event.type === "retrieval_started") {
      setStatus("Searching vector memory");
    }

    if (event.type === "tool_call_started") {
      setStatus("Running tool orchestration");
    }

    if (event.type === "token") {
      setAnswer((current) => `${current}${String(event.payload.text ?? "")}`);
    }

    if (event.type === "citation") {
      const citation = event.payload.citation as Citation | undefined;
      if (citation) {
        setCitations((current) => dedupeCitations([...current, citation]));
      }
    }

    if (event.type === "tool_call_result") {
      setToolTraces((event.payload.traces as ToolTrace[] | undefined) ?? []);
    }

    if (event.type === "run_completed") {
      setStatus("Completed");
      setRunState("complete");
    }
  }

  function stopStream() {
    controllerRef.current?.abort();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuery();
    }
  }

  async function handleFileUpload(fileList: FileList | null) {
    const file = fileList?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setStatus(`Indexing ${file.name}`);
    try {
      const result = await uploadDocument(file);
      setDocuments((current) => [result, ...current]);
      setStatus(`Indexed ${result.filename}`);
    } catch (error) {
      setRunState("error");
      setStatus(error instanceof Error ? error.message : "Document upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 text-ink sm:px-6 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-3 border-b border-black/10 pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-moss">SuperAgent RAG</p>
            <h1 className="mt-2 text-3xl font-semibold leading-tight sm:text-4xl">Agent workflow console</h1>
          </div>
          <div className="flex items-center gap-2 rounded border border-black/10 bg-white/65 px-3 py-2 text-sm">
            <Bot size={18} aria-hidden="true" />
            <span>{status}</span>
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex min-h-[620px] flex-col rounded border border-black/10 bg-white/72 shadow-sm">
            <div className="flex items-center justify-between border-b border-black/10 px-4 py-3">
              <div>
                <h2 className="text-base font-semibold">Conversation</h2>
                <p className="text-sm text-black/60">Session {sessionId}</p>
              </div>
              <span className={stateBadge(runState)}>{runState}</span>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="rounded border border-black/10 bg-paper p-4">
                <p className="text-sm font-semibold text-black/60">Assistant</p>
                <p className="mt-2 whitespace-pre-wrap text-base leading-7">
                  {answer || "Ask a plain-English question to stream retrieval, tool calls, and response generation."}
                </p>
              </div>
            </div>

            <form onSubmit={submitQuery} className="border-t border-black/10 p-4">
              <label className="sr-only" htmlFor="query">
                Query
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={4}
                className="min-h-28 w-full resize-none rounded border border-black/15 bg-white px-3 py-3 text-base leading-6 shadow-inner"
                placeholder="Ask the agent to research, retrieve, and orchestrate tools..."
              />
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-2">
                  <label
                    className="inline-flex h-10 cursor-pointer items-center gap-2 rounded border border-black/15 bg-white px-3 text-sm font-semibold text-ink"
                    title="Upload a text document"
                  >
                    <FileUp size={17} aria-hidden="true" />
                    Attach
                    <input
                      type="file"
                      className="sr-only"
                      accept=".txt,.md,.markdown,.csv,.json,.log,.py,.js,.ts,.tsx,.html,.css"
                      disabled={isUploading}
                      onChange={(event) => void handleFileUpload(event.target.files)}
                    />
                  </label>
                  <p className="text-sm text-black/55">
                    {isUploading ? "Indexing file..." : "Attach text files for RAG answers."}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={stopStream}
                    disabled={runState !== "streaming"}
                    className="inline-flex h-10 w-10 items-center justify-center rounded border border-black/15 bg-white text-ink disabled:cursor-not-allowed disabled:opacity-45"
                    title="Stop stream"
                  >
                    <CircleStop size={18} aria-hidden="true" />
                  </button>
                  <button
                    type="submit"
                    disabled={runState === "streaming"}
                    className="inline-flex h-10 items-center gap-2 rounded bg-moss px-4 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <Play size={17} aria-hidden="true" />
                    Run
                  </button>
                </div>
              </div>
            </form>
          </div>

          <aside className="flex flex-col gap-5">
            <Panel icon={<Search size={18} />} title="Citations">
              <div className="space-y-3">
                {citations.length === 0 ? (
                  <EmptyState text="Retrieved sources will appear here." />
                ) : (
                  citations.map((citation) => (
                    <div key={citation.id} className="rounded border border-black/10 bg-white p-3">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-semibold">{citation.title}</h3>
                        {typeof citation.score === "number" && (
                          <span className="rounded bg-skyglass px-2 py-1 text-xs">{citation.score}</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs font-medium text-moss">{citation.source}</p>
                      <p className="mt-2 text-sm leading-5 text-black/70">{citation.snippet}</p>
                    </div>
                  ))
                )}
              </div>
            </Panel>

            <Panel icon={<FileUp size={18} />} title="Indexed Files">
              <div className="space-y-3">
                {documents.length === 0 ? (
                  <EmptyState text="Uploaded documents will be chunked and indexed here." />
                ) : (
                  documents.map((document) => (
                    <div key={document.document_id} className="rounded border border-black/10 bg-white p-3">
                      <h3 className="text-sm font-semibold">{document.filename}</h3>
                      <p className="mt-1 text-sm text-black/60">
                        {document.chunks_indexed} chunks · {document.characters_indexed} characters
                      </p>
                    </div>
                  ))
                )}
              </div>
            </Panel>

            <Panel icon={<Wrench size={18} />} title="Tool Traces">
              <div className="space-y-3">
                {toolTraces.length === 0 ? (
                  <EmptyState text="Composio traces will appear here." />
                ) : (
                  toolTraces.map((trace) => (
                    <div key={`${trace.name}-${trace.started_at}`} className="rounded border border-black/10 bg-white p-3">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold">{trace.name}</h3>
                        <span className="rounded bg-paper px-2 py-1 text-xs">{trace.status}</span>
                      </div>
                      <p className="mt-2 text-sm leading-5 text-black/70">{trace.output_summary}</p>
                    </div>
                  ))
                )}
              </div>
            </Panel>

            <Panel icon={<Database size={18} />} title="Event Stream">
              <div className="space-y-2">
                {events.length === 0 ? (
                  <EmptyState text="Live SSE events will appear here." />
                ) : (
                  events.map((event) => (
                    <div key={`${event.timestamp}-${event.type}`} className="rounded border border-black/10 bg-white px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold">{event.type}</span>
                        <span className="text-xs text-black/50">{new Date(event.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Panel>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Panel({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="rounded border border-black/10 bg-white/72 p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="rounded border border-dashed border-black/15 bg-paper p-3 text-sm text-black/55">{text}</p>;
}

function stateBadge(state: RunState) {
  const base = "rounded px-2 py-1 text-xs font-semibold uppercase";
  if (state === "streaming") {
    return `${base} bg-coral text-white`;
  }
  if (state === "complete") {
    return `${base} bg-moss text-white`;
  }
  if (state === "error") {
    return `${base} bg-red-600 text-white`;
  }
  return `${base} bg-paper text-black/65`;
}

function dedupeCitations(citations: Citation[]) {
  return citations.filter((citation, index, all) => all.findIndex((item) => item.id === citation.id) === index);
}
