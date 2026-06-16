from app.models.workflow import StructuredWorkflowInput


class QueryUnderstandingService:
    def structure(self, query: str) -> StructuredWorkflowInput:
        normalized_query = " ".join(query.split())
        lowered = normalized_query.lower()
        intent = "answer_question"
        if any(term in lowered for term in ("summarize", "summary", "tl;dr")):
            intent = "summarize"
        elif any(term in lowered for term in ("compare", "difference", "versus", "vs")):
            intent = "compare"

        return StructuredWorkflowInput(
            original_query=query,
            normalized_query=normalized_query,
            intent=intent,
            retrieval_query=normalized_query,
        )
