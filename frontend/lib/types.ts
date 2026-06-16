export type Citation = {
  id: string;
  title: string;
  source: string;
  snippet: string;
  score?: number | null;
  metadata: Record<string, string | number | boolean>;
};

export type ToolTrace = {
  name: string;
  status: "started" | "completed" | "failed";
  input: Record<string, unknown>;
  output_summary?: string | null;
  started_at: string;
  completed_at?: string | null;
  error?: string | null;
};

export type StreamEventType =
  | "run_started"
  | "status"
  | "retrieval_started"
  | "retrieval_result"
  | "tool_call_started"
  | "tool_call_result"
  | "token"
  | "citation"
  | "error"
  | "run_completed";

export type StreamEvent = {
  run_id: string;
  session_id: string;
  type: StreamEventType;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type DocumentIngestResponse = {
  document_id: string;
  filename: string;
  chunks_indexed: number;
  characters_indexed: number;
  source: string;
};
