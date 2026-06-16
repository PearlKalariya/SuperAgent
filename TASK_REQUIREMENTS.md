# SuperAgent AI Agentic Workflow

## Overview

Build a modular SuperAgent retrieval-augmented generation (RAG) system with a responsive Next.js 15 frontend and a FastAPI backend. The platform should enable real-time AI agent interaction for complex, multi-step workflows using Gemini embeddings, ChromaDB vector storage, and Composio-based tool orchestration.

## Goal

Create a general-purpose AI agent platform that can coordinate LLM-driven reasoning, external tool calls, semantic search, and vector retrieval across a TypeScript–Python communication layer.

## Key Technologies

- Next.js 15
- TypeScript
- Tailwind CSS
- FastAPI
- Python 3.13+
- Gemini embeddings
- ChromaDB vector store
- Composio orchestration layer
- SSE / streaming response architecture

## Frontend Requirements

- Responsive UI built with Next.js 15 and Tailwind CSS.
- Real-time agent interaction experience with streaming updates.
- Single-page query input and conversational response area.
- File attachment control for uploading documents into the RAG index.
- Clear display of agent status, citations, and result sections.
- Mobile-friendly layout and keyboard-friendly controls.

## Backend Requirements

- FastAPI application that manages agentic workflows.
- Support for SSE or equivalent streaming response delivery.
- Modular agent service architecture for query understanding, retrieval, tool orchestration, memory, and response generation.
- Conversational memory and previous-chat context tracking across user sessions.
- Gemini embeddings integration for semantic search and context encoding.
- ChromaDB as the vector store for memory and retrieval.
- Document ingestion flow that extracts text, chunks uploaded files, embeds chunks, and stores them for retrieval.
- Clean separation between Python backend logic and TypeScript frontend API calls.

## Tool Orchestration Requirements

- Use Composio to connect LLMs to external APIs and tools.
- Support multi-step workflows where LLM reasoning may call out to:
  - knowledge-base retrieval
  - API-driven data sources
  - custom tool functions
  - memory lookup and storage
- Ensure orchestration is robust and supports modular replacement of tools.
- Maintain traceability of tool calls and intermediate outputs.

## Scope

### In scope

- Real-time UI for query input and streamed results.
- File attachment and document-grounded summarization/question answering.
- Backend orchestration of multiple agents and tool calls.
- Gemini embeddings + ChromaDB vector retrieval.
- Composio-driven external API integration.
- End-to-end data flow across Next.js and FastAPI.

### Out of scope

- Brokerage trading or order execution.
- Authenticated user accounts and login flows.
- Full portfolio management or transaction processing.
- Real-time tick-by-tick market feeds.

## Requirements

1. The system must accept plain-English queries and translate them into structured workflow inputs.
2. The backend must orchestrate agent calls, retrieval, conversational memory, and external API requests in discrete steps.
3. Responses must stream to the frontend in real time where possible.
4. The application must use Gemini embeddings for semantic search and memory retrieval.
5. ChromaDB must store vector embeddings and support fast retrieval.
6. Composio must be used to wire LLM prompts to external tool invocations.
7. The frontend and backend should communicate through a modular TypeScript/Python interface.
8. Generated output should include citations, source metadata, or retrieval provenance when applicable.
9. The architecture must be documented clearly for future extension.
10. Users must be able to upload text-based files that are chunked, embedded, indexed, and available for summarization or question answering.

## Architecture

- Frontend: Next.js 15 app with query input, streaming output display, and status indicators.
- API Layer: FastAPI routes for query submission, history retrieval, and health checks.
- Document Ingestion: FastAPI upload route that extracts text, chunks files, and indexes them in the vector store.
- Orchestration Layer: Composio-managed workflow that connects LLM reasoning to tool adapters.
- Vector Store: ChromaDB for embedding storage, retrieval, and memory search.
- Embeddings: Gemini embeddings used for semantic similarity and retrieval.

## Verification

- Confirm the frontend renders a query interface and streams backend responses.
- Validate that the backend uses FastAPI for the workflow API.
- Confirm Gemini embeddings are created and stored in ChromaDB.
- Upload a text document and confirm its chunks are retrievable as cited context.
- Verify Composio tool orchestration calls external APIs in sequence.
- Check that responses include retrieval provenance or source metadata where appropriate.

## Notes

This document is intended as the primary task and requirements reference for the SuperAgent AI agent workflow implementation.
