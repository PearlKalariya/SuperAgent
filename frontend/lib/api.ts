import type { DocumentIngestResponse, StreamEvent } from "./types";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

type StreamQueryArgs = {
  query: string;
  sessionId: string;
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
};

export async function streamQuery({ query, sessionId, signal, onEvent }: StreamQueryArgs) {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/query/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ query, session_id: sessionId }),
      signal
    });
  } catch (error) {
    if (signal.aborted) {
      throw error;
    }
    throw new Error(
      `Unable to reach the backend at ${backendUrl}. Make sure FastAPI is running on port 8000.`
    );
  }

  if (!response.ok || !response.body) {
    const detail = await response.text();
    throw new Error(detail || `Query stream failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const event = parseSseChunk(chunk);
      if (event) {
        onEvent(event);
        if (event.type === "error") {
          throw new Error(String(event.payload.message ?? "The backend workflow failed."));
        }
      }
    }
  }
}

export async function uploadDocument(file: File): Promise<DocumentIngestResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${backendUrl}/api/documents`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Document upload failed with status ${response.status}`);
  }

  return response.json() as Promise<DocumentIngestResponse>;
}

function parseSseChunk(chunk: string): StreamEvent | null {
  const dataLine = chunk
    .split("\n")
    .find((line) => line.startsWith("data: "));

  if (!dataLine) {
    return null;
  }

  return JSON.parse(dataLine.slice(6)) as StreamEvent;
}
