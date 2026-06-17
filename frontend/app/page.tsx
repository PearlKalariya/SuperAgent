"use client";

import { FormEvent, KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";
import { Bot, CircleStop, Database, FileUp, Play, Search, Wrench } from "lucide-react";
import { streamQuery, uploadDocument } from "@/lib/api";
import type { Citation, DocumentIngestResponse, StreamEvent, ToolTrace } from "@/lib/types";

type RunState = "idle" | "streaming" | "complete" | "error";
type Message = { id: string; role: "user" | "assistant"; text: string };
const SESSION_STORAGE_KEY = "superagent-session-id";

export default function Home() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const currentAssistantMessageIdRef = useRef<string | null>(null);
  const [status, setStatus] = useState("Ready");
  const [runState, setRunState] = useState<RunState>("idle");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [toolTraces, setToolTraces] = useState<ToolTrace[]>([]);
  const [documents, setDocuments] = useState<DocumentIngestResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const controllerRef = useRef<AbortController | null>(null);

  function createNewSession() {
    const nextSessionId = `session-${crypto.randomUUID()}`;
    window.localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
    setSessionId(nextSessionId);
    setMessages([]);
    setStatus("Ready");
    setRunState("idle");
    setEvents([]);
    setCitations([]);
    setToolTraces([]);
  }

  function startNewChat() {
    controllerRef.current?.abort();
    setQuery("");
    createNewSession();
  }

  useEffect(() => {
    const existingSessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existingSessionId) {
      setSessionId(existingSessionId);
      return;
    }

    const nextSessionId = `session-${crypto.randomUUID()}`;
    window.localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
    setSessionId(nextSessionId);
  }, []);

  async function submitQuery(event?: FormEvent) {
    event?.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || !sessionId || runState === "streaming") {
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;
    setRunState("streaming");
    setEvents([]);
    setCitations([]);
    setToolTraces([]);
    setStatus("Starting workflow");

    const userMessage: Message = {
      id: `msg-${crypto.randomUUID()}`,
      role: "user",
      text: trimmedQuery,
    };

    setMessages((current) => [...current, userMessage]);

    const assistantMessageId = `msg-${crypto.randomUUID()}`;
    currentAssistantMessageIdRef.current = assistantMessageId;
    setMessages((current) => [
      ...current,
      { id: assistantMessageId, role: "assistant", text: "" },
    ]);

    setQuery("");

    try {
      await streamQuery({
        query: trimmedQuery,
        sessionId,
        signal: controller.signal,
        onEvent: handleEvent,
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
      const assistantId = currentAssistantMessageIdRef.current;
      if (assistantId) {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? { ...message, text: `${message.text}${String(event.payload.text ?? "")}` }
              : message,
          ),
        );
      }
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
    <main className="min-h-screen bg-slate-50 px-4 py-6 text-ink sm:px-6 lg:px-10">
      <div className="mx-auto flex max-w-8xl flex-col gap-6">
        <header className="grid gap-4 rounded-[32px] border border-black/10 bg-white/95 p-6 shadow-lg shadow-slate-200/60 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">SuperAgent RAG</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-black sm:text-4xl">Agent workflow console</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Ask questions, ingest documents, and watch retrieval, tool orchestration, and streaming results update live.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 justify-start md:justify-end">
            <div className="rounded-3xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm">
              <span className="mr-2 inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              {status}
            </div>
            <button
              type="button"
              onClick={startNewChat}
              className="rounded-full border border-black/10 bg-white px-5 py-3 text-sm font-semibold text-ink shadow-sm transition hover:bg-slate-50"
            >
              New Chat
            </button>
          </div>
        </header>

        <section className="grid gap-6 xl:grid-cols-[1.75fr_1fr]">
          <div className="flex min-h-[650px] flex-col rounded-[36px] border border-black/10 bg-white/95 shadow-lg shadow-slate-200/50">
            <div className="flex items-center justify-between gap-4 border-b border-black/10 px-6 py-5">
              <div>
                <h2 className="text-lg font-semibold text-black">Conversation</h2>
                <p className="text-sm text-slate-500">Session {sessionId}</p>
              </div>
              <span className={stateBadge(runState)}>{runState.toUpperCase()}</span>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="flex min-h-[360px] flex-col gap-4">
                {messages.length === 0 ? (
                  <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-8 shadow-sm">
                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Assistant</p>
                    <p className="mt-4 text-base leading-7 text-slate-700">
                      Start the conversation by asking a question or uploading a document.
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`max-w-[85%] rounded-[28px] p-5 shadow-sm ${
                        message.role === "user"
                          ? "ml-auto rounded-br-[10px] rounded-tl-[28px] rounded-tr-[28px] bg-emerald-50 text-right text-slate-900"
                          : "mr-auto rounded-bl-[10px] rounded-tl-[28px] rounded-tr-[28px] bg-slate-50 text-left text-slate-900"
                      }`}
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        {message.role === "user" ? "You" : "Assistant"}
                      </p>
                      <p className="mt-3 whitespace-pre-wrap text-base leading-7">{message.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            <form onSubmit={submitQuery} className="sticky bottom-0 rounded-b-[36px] border-t border-black/10 bg-slate-50 px-6 py-6 shadow-lg shadow-black/5">
              <label className="sr-only" htmlFor="query">
                Query
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={4}
                className="min-h-[140px] w-full resize-none rounded-[28px] border border-slate-200 bg-white px-5 py-4 text-base leading-7 text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-moss focus:outline-none focus:ring-2 focus:ring-moss/10"
                placeholder="Ask a question, summarize uploaded notes, or generate a plan..."
              />
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                  <label
                    className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                    title="Upload a text document"
                  >
                    <FileUp size={18} aria-hidden="true" />
                    Attach
                    <input
                      type="file"
                      className="sr-only"
                      accept=".txt,.md,.markdown,.csv,.json,.log,.py,.js,.ts,.tsx,.html,.css,.pdf,.docx"
                      disabled={isUploading}
                      onChange={(event) => void handleFileUpload(event.target.files)}
                    />
                  </label>
                  <p className="text-sm text-slate-500">
                    Attach text or document files for RAG answers.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={stopStream}
                    disabled={runState !== "streaming"}
                    className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-50"
                    title="Stop stream"
                  >
                    <CircleStop size={18} aria-hidden="true" />
                  </button>
                  <button
                    type="submit"
                    disabled={runState === "streaming"}
                    className="inline-flex h-12 items-center gap-2 rounded-full bg-moss px-6 text-sm font-semibold text-white shadow-lg shadow-moss/20 transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Play size={18} aria-hidden="true" />
                    Run
                  </button>
                </div>
              </div>
            </form>
          </div>

          <aside className="space-y-6 max-h-[650px] overflow-y-auto pr-2">
            <Panel icon={<Search size={18} />} title="Citations">
              <div className="space-y-3">
                {citations.length === 0 ? (
                  <EmptyState text="Retrieved sources will appear here." />
                ) : (
                  citations.map((citation) => (
                    <div key={citation.id} className="rounded-[28px] border border-slate-200 bg-slate-50 p-4 shadow-sm">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-slate-900">{citation.title}</h3>
                        {typeof citation.score === "number" && (
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
                            {citation.score}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{citation.source}</p>
                      <p className="mt-3 text-sm leading-6 text-slate-700">{citation.snippet}</p>
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
                    <div key={document.document_id} className="rounded-[28px] border border-slate-200 bg-slate-50 p-4 shadow-sm">
                      <h3 className="text-sm font-semibold text-slate-900">{document.filename}</h3>
                      <p className="mt-2 text-sm text-slate-600">
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
                    <div key={`${trace.name}-${trace.started_at}`} className="rounded-[28px] border border-slate-200 bg-slate-50 p-4 shadow-sm">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-slate-900">{trace.name}</h3>
                        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">{trace.status}</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{trace.output_summary}</p>
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
                    <div key={`${event.timestamp}-${event.type}`} className="rounded-[28px] border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold text-slate-900">{event.type}</span>
                        <span className="text-xs text-slate-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
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
