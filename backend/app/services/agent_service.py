import asyncio
import uuid
from collections.abc import AsyncIterator

from app.core.errors import WorkflowError
from app.core.sse import as_sse
from app.models.citations import Citation
from app.models.query import QueryRequest, QueryResponse
from app.models.streaming import StreamEvent
from app.models.workflow import ToolTrace
from app.services.composio_service import ComposioService
from app.services.memory_service import MemoryService
from app.services.orchestration_service import OrchestrationService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.response_service import ResponseService
from app.services.retrieval_service import RetrievalService
from app.services.tools.composio_tool import ComposioActionTool
from app.services.tools.time_tool import TimeTool
from pydantic import create_model


class AgentService:
    def __init__(
        self,
        query_understanding: QueryUnderstandingService,
        retrieval: RetrievalService,
        memory: MemoryService,
        composio: ComposioService,
        orchestration: OrchestrationService,
        response: ResponseService,
    ) -> None:
        self.query_understanding = query_understanding
        self.retrieval = retrieval
        self.memory = memory
        self.composio = composio
        self.orchestration = orchestration
        self.response = response

    async def run_query(self, request: QueryRequest) -> QueryResponse:
        run_id = self._new_run_id()
        try:
            workflow_input = self.query_understanding.structure(request.query)
            citations = await self._retrieve_context(request.session_id, workflow_input.retrieval_query)
            
            tools = [
                ComposioActionTool(
                    self.composio,
                    action_name="SERPAPI_SEARCH",
                    description="Search the web for real-time information",
                    schema=create_model("SerpApiSchema", q=(str, ...))
                ),
                TimeTool()
            ]
            
            tool_inputs = {
                "serpapi_search": {"q": workflow_input.normalized_query},
                "get_current_time": {}
            }
            
            tool_traces = await self.orchestration.execute_tools(tools, tool_inputs)
            
            answer = self.response.compose_answer(
                workflow_input.normalized_query,
                citations,
                tool_traces,
            )
            await self.memory.add_exchange(request.session_id, request.query, answer)
            return QueryResponse(
                run_id=run_id,
                session_id=request.session_id,
                answer=answer,
                citations=citations,
                tool_traces=tool_traces,
            )
        except Exception as error:
            raise WorkflowError(str(error), step="query_workflow") from error

    async def stream_query(self, request: QueryRequest) -> AsyncIterator[str]:
        async def events() -> AsyncIterator[StreamEvent]:
            run_id = self._new_run_id()
            yield self._event(run_id, request.session_id, "run_started", {"query": request.query})
            try:
                await asyncio.sleep(0.05)

                workflow_input = self.query_understanding.structure(request.query)
                yield self._event(
                    run_id,
                    request.session_id,
                    "status",
                    {
                        "message": "Structured query for retrieval.",
                        "intent": workflow_input.intent,
                        "retrieval_query": workflow_input.retrieval_query,
                    },
                )

                history = self.memory.get_history(request.session_id)
                yield self._event(
                    run_id,
                    request.session_id,
                    "status",
                    {"message": "Loaded previous conversation context.", "messages": len(history)},
                )

                yield self._event(
                    run_id,
                    request.session_id,
                    "retrieval_started",
                    {"query": workflow_input.retrieval_query},
                )
                memory_citations = await self.memory.search(
                    request.session_id,
                    workflow_input.retrieval_query,
                )
                if memory_citations:
                    yield self._event(
                        run_id,
                        request.session_id,
                        "status",
                        {
                            "message": "Retrieved relevant conversation memory.",
                            "memories": len(memory_citations),
                        },
                    )

                citations = await self.retrieval.search(workflow_input.retrieval_query)
                citations = self._dedupe_citations([*memory_citations, *citations])
                yield self._event(
                    run_id,
                    request.session_id,
                    "retrieval_result",
                    {"citations": [citation.model_dump(mode="json") for citation in citations]},
                )
                for citation in citations:
                    yield self._event(
                        run_id,
                        request.session_id,
                        "citation",
                        {"citation": citation.model_dump(mode="json")},
                    )

                yield self._event(
                    run_id,
                    request.session_id,
                    "tool_call_started",
                    {"tool": "composio_orchestrator"},
                )
                tools = [
                    ComposioActionTool(
                        self.composio,
                        action_name="SERPAPI_SEARCH",
                        description="Search the web for real-time information",
                        schema=create_model("SerpApiSchema", q=(str, ...))
                    ),
                    TimeTool()
                ]
                
                tool_inputs = {
                    "serpapi_search": {"q": workflow_input.normalized_query},
                    "get_current_time": {}
                }
                
                tool_traces = await self.orchestration.execute_tools(tools, tool_inputs)
                yield self._event(
                    run_id,
                    request.session_id,
                    "tool_call_result",
                    {"traces": [trace.model_dump(mode="json") for trace in tool_traces]},
                )

                answer_parts: list[str] = []
                async for token in self.response.stream_answer(
                    workflow_input.normalized_query,
                    citations,
                    tool_traces,
                ):
                    answer_parts.append(token)
                    yield self._event(run_id, request.session_id, "token", {"text": token})

                answer = "".join(answer_parts)

                await self.memory.add_exchange(request.session_id, request.query, answer)
                yield self._event(
                    run_id,
                    request.session_id,
                    "run_completed",
                    {
                        "answer": answer,
                        "citations": [citation.model_dump(mode="json") for citation in citations],
                        "tool_traces": [trace.model_dump(mode="json") for trace in tool_traces],
                    },
                )
            except Exception as error:
                yield self._event(
                    run_id,
                    request.session_id,
                    "error",
                    {"message": str(error), "step": "query_workflow"},
                )

        async for encoded in as_sse(events()):
            yield encoded

    async def _retrieve_context(self, session_id: str, query: str) -> list[Citation]:
        memory_citations = await self.memory.search(session_id, query)
        retrieved_citations = await self.retrieval.search(query)
        return self._dedupe_citations([*memory_citations, *retrieved_citations])

    @staticmethod
    def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
        seen: set[str] = set()
        deduped: list[Citation] = []
        for citation in citations:
            if citation.id in seen:
                continue
            seen.add(citation.id)
            deduped.append(citation)
        return deduped

    @staticmethod
    def _new_run_id() -> str:
        return f"run_{uuid.uuid4().hex}"

    @staticmethod
    def _event(
        run_id: str,
        session_id: str,
        event_type: str,
        payload: dict,
    ) -> StreamEvent:
        return StreamEvent(run_id=run_id, session_id=session_id, type=event_type, payload=payload)
