"""Composio tool orchestration service.

When ``COMPOSIO_API_KEY`` is configured, the service initialises the Composio
toolset and can execute actions registered through the Composio platform.

Without an API key (or when the SDK is not installed) the service returns a
deterministic mock trace so the rest of the workflow remains testable.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.models.citations import Citation
from app.models.workflow import ToolTrace

logger = logging.getLogger(__name__)


class ComposioService:
    """Composio boundary.

    The service returns a deterministic trace when credentials or SDK setup are not
    present, keeping the app useful in local development while preserving the
    integration boundary for real tool calls.
    """

    def __init__(self) -> None:
        self._toolset = None
        if settings.composio_api_key:
            try:
                from composio import ComposioToolSet

                self._toolset = ComposioToolSet(api_key=settings.composio_api_key)
                logger.info("Composio toolset initialised.")
            except ImportError:
                logger.warning(
                    "composio package not installed — mock traces will be returned."
                )
            except Exception:
                logger.exception("Composio initialisation failed — falling back to mocks.")

    @property
    def is_live(self) -> bool:
        """True when backed by a real Composio connection."""
        return self._toolset is not None

    def execute_action(self, action: str, params: dict[str, Any] | None = None):
        """Public wrapper to execute a Composio action via the underlying toolset.

        This preserves encapsulation and allows callers to invoke actions without
        directly referencing the private `_toolset` attribute.
        """
        if self._toolset is None:
            raise RuntimeError("Composio toolset not initialised")
        return self._toolset.execute_action(action=action, params=params or {})

    async def run_tools(
        self,
        query: str,
        citations: list[Citation],
    ) -> list[ToolTrace]:
        """Execute tool actions and return traces.

        Currently runs a ``SERPAPI_SEARCH`` action when the Composio toolset
        is available, otherwise returns a mock trace.  Additional actions can
        be wired in by extending the ``_live_actions`` list below.
        """
        started_at = datetime.now(UTC)

        if self._toolset is None:
            return self._mock_traces(query, citations, started_at)

        traces: list[ToolTrace] = []

        # -----------------------------------------------------------
        # Live tool actions — extend this list with more Composio
        # actions as you register them on the platform.
        # -----------------------------------------------------------
        live_actions: list[dict] = [
            {
                "action": "SERPAPI_SEARCH",
                "params": {"q": query},
                "label": "composio_web_search",
            },
        ]

        for action_spec in live_actions:
            action_name: str = action_spec["action"]
            params: dict = action_spec.get("params", {})
            label: str = action_spec.get("label", action_name)
            action_started = datetime.now(UTC)
            try:
                result = self._toolset.execute_action(
                    action=action_name,
                    params=params,
                )
                output_text = str(result)[:500]
                traces.append(
                    ToolTrace(
                        name=label,
                        status="completed",
                        input={"action": action_name, **params},
                        output_summary=output_text,
                        started_at=action_started,
                        completed_at=datetime.now(UTC),
                    )
                )
            except Exception as exc:
                logger.exception("Composio action %s failed.", action_name)
                traces.append(
                    ToolTrace(
                        name=label,
                        status="failed",
                        input={"action": action_name, **params},
                        output_summary=None,
                        started_at=action_started,
                        completed_at=datetime.now(UTC),
                        error=str(exc)[:300],
                    )
                )

        if not traces:
            traces = self._mock_traces(query, citations, started_at)

        return traces

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _mock_traces(
        query: str,
        citations: list[Citation],
        started_at: datetime,
    ) -> list[ToolTrace]:
        return [
            ToolTrace(
                name="composio_mock_context_summary",
                status="completed",
                input={"query": query, "citation_count": len(citations)},
                output_summary=(
                    "Mock orchestration completed. "
                    "Set COMPOSIO_API_KEY to enable live tools."
                ),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        ]
