# AI Vacation Planner

An AI-powered trip planning API. Plan a trip by typing it, speaking it, or
letting an AI agent decide for itself which tools it needs — live weather,
place lookups, cost estimates, and a curated travel knowledge base — to
build a real itinerary, and have it read back to you as speech.

## What it does

- **Accounts & trips** — register/login (JWT), create and manage trips.
- **AI-generated itineraries** — a tool-using agent plans a day-by-day
  itinerary for a trip, deciding on its own which tools (if any) it needs.
- **Retrieval-Augmented Generation (RAG)** — a curated knowledge base of
  travel guides, local tips, hidden gems, FAQs, and destination notes,
  embedded and searchable by meaning, not just keywords.
- **Voice in, voice out** — speak a trip request and get a planned trip
  back; have any saved itinerary read aloud as natural speech.
- **MCP tools** — weather and place lookups are served by a standalone
  MCP (Model Context Protocol) server, not hardcoded into the agent.

## Architecture

```
Client
  │
  ├─ POST /itinerary/generate ──┐
  ├─ POST /voice/plan ───────────┤
  │                              ▼
  │                        ItineraryService / VoiceService
  │                              │
  │                              ▼
  │                     Agent (LangGraph, src/agent/graph.py)
  │                              │
  │              ┌───────────────┼───────────────┬──────────────┐
  │              ▼               ▼                ▼              ▼
  │      get_weather        find_place     estimate_trip_cost  search_travel_knowledge
  │      (MCP tool)          (MCP tool)      (local tool)        (local tool, RAG)
  │              │               │                                    │
  │       ┌──────┴───────────────┘                                    ▼
  │       ▼                                                   pgvector similarity
  │  MCP server (src/mcp_server/, stdio subprocess)            search over Voyage AI
  │  wttr.in / Nominatim APIs                                  embeddings of data/knowledge/
  │
  └─ GET /itinerary/{id}/audio ─► Claude narration (with plain-text fallback) ─► gTTS ─► audio/mpeg
```

### The agent (`src/agent/graph.py`)

Built with **LangGraph** as a small state machine, not a fixed script:

1. **agent** node — calls Claude (`ChatAnthropic`) with all available tools
   bound. Claude decides, per request, whether it needs any tools and
   which ones — there is no hardcoded "always call weather first" logic.
2. **tools** node — runs whichever tool(s) Claude asked for, feeds the
   results back.
3. Repeats until Claude has enough information, then moves to **finalize**.
4. **finalize** node — forces the final answer into a validated
   `ItinerarySchema` via Claude's structured-output support. Falls back to
   a clean error (never a malformed itinerary) if this fails.

Transient failures (rate limits, timeouts, connection errors) are retried
automatically (`src/agent/retry_handler.py`); non-retryable errors
(billing, bad input) fail fast instead of wasting retries.

### RAG — the knowledge base (`src/embeddings/`, `src/services/knowledge_service.py`)

- Source content lives as plain markdown in `data/knowledge/<category>/*.md`.
- `scripts/seed_knowledge_base.py` chunks each file (paragraph-aware,
  sentence-boundary fallback for long paragraphs), embeds each chunk via
  **Voyage AI**, and stores it in Postgres using **pgvector**. Re-running
  it is incremental — unchanged files are skipped via a content hash, so
  it never re-embeds (and re-pays for) content that hasn't changed.
- `KnowledgeService.search()` does the retrieval: embeds the query,
  finds the closest chunks by cosine similarity, and **filters out
  anything below a relevance threshold** — a query with no genuinely
  relevant content returns nothing, rather than the "closest available"
  chunk regardless of how unrelated it actually is.
- As a second line of defense, the agent's system prompt explicitly
  instructs Claude to ignore retrieved content that turns out to be
  about the wrong destination, rather than forcing it into the answer.
- Exposed directly via `GET /knowledge/search` (so retrieval quality can
  be verified independently of generation), and used internally by the
  agent via the `search_travel_knowledge` tool.

### MCP — weather & maps as a separate service (`src/mcp_server/`)

Weather (`wttr.in`) and place lookups (OpenStreetMap/Nominatim) are not
plain functions imported into the agent's process. They're served by a
**standalone MCP server** (`src/mcp_server/server.py`, built with the
official `mcp` SDK's `FastMCP`), launched as a subprocess and reached
over the **stdio transport** — the agent connects to it as an MCP
*client* (via `langchain-mcp-adapters`), the same way an MCP-aware tool
like Claude Code connects to local tool servers.

Since MCP's client is async-only and the rest of this codebase is
synchronous, `src/agent/graph.py` bridges the two with a small,
self-contained helper (`_run_async`) that runs the async MCP work on a
dedicated thread — safe regardless of whether the caller already has its
own event loop running (e.g. the async `/voice/plan` route).

### Voice (`src/agent/voice/`)

- **Speech-to-text**: `POST /voice/plan` accepts an uploaded audio file,
  transcribes it locally with **Whisper** (`faster-whisper`, no API key,
  runs on-device), extracts structured trip details from the transcript
  via Claude, then runs it through the exact same trip/itinerary pipeline
  as the text-based flow — voice is just a second front door, not a
  separate code path.
- **Text-to-speech**: `GET /itinerary/{trip_id}/audio` reads an
  already-generated itinerary and returns it as spoken audio
  (`audio/mpeg`), decoupled from generation itself so any saved
  itinerary can be replayed later regardless of how it was created.
  Claude rewrites the itinerary into a short, natural spoken summary;
  if Claude is unavailable, it falls back to a plain structured summary
  instead of failing outright. Output is capped to a safe length before
  synthesis, since gTTS makes one network request per ~100 characters
  and uncapped text could otherwise take minutes to synthesize.

## Project structure

```
src/
  main.py                  FastAPI app
  config.py                Settings (env-driven)
  database.py               DB engine/session
  models/                  SQLModel tables + request/response schemas
  routers/                 HTTP endpoints (auth, trips, itinerary, knowledge, voice)
  services/                Business logic (one service per domain concept)
  schemas/                 LLM output validation (ItinerarySchema)
  agent/                   The AI agent
    graph.py                LangGraph state machine + MCP client wiring
    prompts.py               Agent system prompt
    retry_handler.py          Shared retry logic
    tools/                    Local LangChain tools (pricing, knowledge/RAG)
    voice/                    Whisper STT, gTTS TTS, Claude narration/extraction
  mcp_server/              Standalone MCP server (weather, maps)
  embeddings/              Chunking + Voyage AI embedding client
  utils/                   Auth, dependencies, background tasks
scripts/
  seed_knowledge_base.py   Ingests data/knowledge/ into the vector DB
data/knowledge/            Source travel content (markdown, by category)
migrations/                Alembic database migrations
```

## API

Full interactive docs at `/docs` (Swagger) once running. Endpoints:

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Get a bearer token |
| GET | `/users/me` | Current user |
| POST | `/trips` | Create a trip |
| GET | `/trips` | List your trips |
| GET | `/trips/{trip_id}` | Get a trip |
| PUT | `/trips/{trip_id}` | Update a trip |
| DELETE | `/trips/{trip_id}` | Delete a trip |
| POST | `/itinerary` | Manually create an itinerary |
| POST | `/itinerary/generate` | Generate an itinerary via the AI agent |
| GET | `/itinerary/{trip_id}` | Get a trip's itinerary |
| GET | `/itinerary/{trip_id}/audio` | Hear the itinerary as spoken audio |
| GET | `/knowledge/search` | Semantic search over the travel knowledge base |
| POST | `/voice/plan` | Speak a trip request, get a planned trip back |

## LLM integration details

- **Provider**: Anthropic Claude, via `langchain-anthropic`. Model is
  configurable (`ANTHROPIC_MODEL` in `.env`, default `claude-haiku-4-5`)
  rather than hardcoded.
- **Structured output**: itinerary generation, trip-detail extraction
  from speech, and knowledge-base chunk schemas all use Claude's native
  structured-output support (`with_structured_output`) to guarantee
  valid, parseable results instead of hand-parsing free text.
- **Tool orchestration**: LangGraph, with four tools available to the
  agent — two served over MCP (weather, maps), two local (pricing
  heuristic, RAG knowledge search).
- **Embeddings**: Voyage AI (`voyage-3.5-lite` by default), used for both
  the knowledge base (document embeddings) and search queries
  (asymmetric query embeddings, per Voyage's recommended approach).
- **Speech**: Whisper (local, via `faster-whisper`) for transcription;
  gTTS for synthesis; Claude for rewriting itineraries into natural
  spoken narration, with a non-AI fallback if Claude is unavailable.

## Setup

1. **Install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment** — copy `.env.example` to `.env` and fill in:
   - `DATABASE_URL` — a running PostgreSQL instance with the
     [pgvector](https://github.com/pgvector/pgvector) extension available
   - `SECRET_KEY` — any random string, used to sign JWTs
   - `ANTHROPIC_API_KEY` — required for itinerary generation, voice
     extraction/narration
   - `VOYAGE_API_KEY` — required for the knowledge base (embeddings)

3. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

4. **Seed the knowledge base** (populates the RAG content)
   ```bash
   python scripts/seed_knowledge_base.py
   ```

5. **Start the server**
   ```bash
   uvicorn src.main:app --reload
   ```
   Then open `http://127.0.0.1:8000/docs`.

   The MCP server (`src/mcp_server/server.py`) does **not** need to be
   started separately — the agent launches it automatically as a
   subprocess whenever it needs weather or maps.

### Notes

- The first voice request downloads the Whisper model (one-time, a few
  hundred MB depending on `WHISPER_MODEL`) and needs enough free RAM to
  load it — a few hundred MB free is normally sufficient.
- Weather/maps use free, keyless public APIs (wttr.in, OpenStreetMap
  Nominatim) — no extra setup needed for those two.
