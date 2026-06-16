from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, health, history, query
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(query.router, prefix="/api", tags=["query"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    return app


app = create_app()
