"""Response generation service.

Uses Gemini for live LLM answers when GEMINI_API_KEY is configured.
Falls back to a deterministic scaffold answer otherwise.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.core.config import settings
from app.models.citations import Citation
from app.models.workflow import ToolTrace

logger = logging.getLogger(__name__)


class ResponseService:
    """Builds the final answer for a workflow run."""

    def __init__(self) -> None:
        self._client = None
        if settings.gemini_api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("Gemini generation client initialised (model=%s).", settings.gemini_model)
            except ImportError:
                logger.warning("google-genai not installed — falling back to scaffold answers.")

    @property
    def is_live(self) -> bool:
        """True when backed by a real Gemini model."""
        return self._client is not None

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(
        query: str,
        citations: list[Citation],
        tool_traces: list[ToolTrace],
        history_summary: str | None = None,
    ) -> str:
        sections: list[str] = []

        sections.append(
            "You are SuperAgent, a helpful and precise AI assistant. "
            "Answer the user's question using the retrieved context and tool outputs below. "
            "Cite sources by title when you reference them. "
            "If the context is insufficient, say so honestly.\n"
        )

        if history_summary:
            sections.append(f"### Conversation History\n{history_summary}\n")

        if citations:
            ctx_parts = []
            for idx, c in enumerate(citations, 1):
                score_str = f" (relevance {c.score})" if c.score is not None else ""
                ctx_parts.append(f"[{idx}] **{c.title}** — {c.source}{score_str}\n{c.snippet}")
            sections.append("### Retrieved Context\n" + "\n\n".join(ctx_parts) + "\n")
        else:
            sections.append("### Retrieved Context\nNo documents were retrieved.\n")

        if tool_traces:
            tool_parts = []
            for t in tool_traces:
                tool_parts.append(f"- **{t.name}** ({t.status}): {t.output_summary or 'no output'}")
            sections.append("### Tool Outputs\n" + "\n".join(tool_parts) + "\n")

        sections.append(f"### User Question\n{query}")

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Non-streaming answer (used by POST /api/query)
    # ------------------------------------------------------------------
    def compose_answer(
        self,
        query: str,
        citations: list[Citation],
        tool_traces: list[ToolTrace],
    ) -> str:
        prompt = self._build_prompt(query, citations, tool_traces)

        if self._client is not None:
            try:
                response = self._client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                )
                return response.text or self._scaffold_answer(query, citations, tool_traces)
            except Exception:
                logger.exception("Gemini generation failed — returning scaffold answer.")
                self._client = None

        return self._scaffold_answer(query, citations, tool_traces)

    # ------------------------------------------------------------------
    # Streaming answer (used by POST /api/query/stream)
    # ------------------------------------------------------------------
    async def stream_answer(
        self,
        query: str,
        citations: list[Citation],
        tool_traces: list[ToolTrace],
    ) -> AsyncIterator[str]:
        """Yield answer tokens one piece at a time.

        When Gemini is available the response is streamed from the model.
        Otherwise the scaffold answer is split into word-level tokens.
        """
        prompt = self._build_prompt(query, citations, tool_traces)

        if self._client is not None:
            try:
                response = self._client.models.generate_content_stream(
                    model=settings.gemini_model,
                    contents=prompt,
                )
                for chunk in response:
                    text = chunk.text
                    if text:
                        yield text
                return
            except Exception:
                logger.exception("Gemini streaming failed — falling back to scaffold tokens.")
                self._client = None

        # Fallback: yield scaffold answer word-by-word
        for token in self._stream_tokens_sync(
            self._scaffold_answer(query, citations, tool_traces)
        ):
            yield token

    # ------------------------------------------------------------------
    # Deterministic fallback (no API key)
    # ------------------------------------------------------------------
    @staticmethod
    def _scaffold_answer(
        query: str,
        citations: list[Citation],
        tool_traces: list[ToolTrace],
    ) -> str:
        source_summary = "no retrieved sources"
        if citations:
            source_summary = ", ".join(citation.title for citation in citations[:3])

        tool_summary = "no external tools"
        if tool_traces:
            tool_summary = ", ".join(trace.name for trace in tool_traces)

        return (
            f"I analyzed your request: {query}. "
            f"The workflow retrieved context from {source_summary} and ran {tool_summary}. "
            "This scaffold is ready for live Gemini generation once the model call is connected."
        )

    @staticmethod
    def _stream_tokens_sync(answer: str) -> list[str]:
        return [f"{word} " for word in answer.split(" ")]

    # Keep backward-compatible public name
    def stream_tokens(self, answer: str) -> list[str]:
        return self._stream_tokens_sync(answer)
