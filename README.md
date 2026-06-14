# AI Vacation Planner
Backend API for managing users, trips, and trip itineraries — with AI-powered itinerary generation using Claude AI.

## Architecture Overview
This project is a FastAPI service with a simple layered structure:
- **API layer (`src/routers`)**: HTTP endpoints for authentication, users, trips, and itinerary.
- **Domain/data layer (`src/models`)**: SQLModel table models and request/response schemas.
- **Infrastructure layer (`src/database.py`, `src/config.py`)**: DB engine/session handling and environment settings.
- **Shared utilities (`src/utils`)**: JWT auth helpers, dependency injection helpers, LLM integration, and logging background tasks.
- **Schema migrations (`migrations`)**: Alembic migration history for database schema changes.

### Main Components
- `src/main.py`: creates the FastAPI app and registers all routers.
- `src/routers/auth.py`: register/login endpoints.
- `src/routers/users.py`: current authenticated user endpoint.
- `src/routers/trips.py`: create/read/update/delete user trips.
- `src/routers/itinerary.py`: create, AI-generate, and fetch itinerary per trip.
- `src/utils/auth.py`: password hashing + JWT create/decode.
- `src/utils/deps.py`: `get_current_user` auth dependency.
- `src/utils/llm.py`: Claude AI integration for itinerary generation.
- `src/utils/background_tasks.py`: background logging tasks.
- `src/models/itinerary.py`: itinerary days stored as PostgreSQL JSONB.

## Project Structure
```text
ai-vacation-planner/
├── .env.example
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 34ea9aec2e9c_create_users_trips_itineraries_tables.py
├── requirements.txt
└── src/
    ├── config.py
    ├── database.py
    ├── main.py
    ├── models/
    │   ├── itinerary.py
    │   ├── trip.py
    │   └── user.py
    ├── routers/
    │   ├── auth.py
    │   ├── itinerary.py
    │   ├── trips.py
    │   └── users.py
    └── utils/
        ├── auth.py
        ├── background_tasks.py
        ├── deps.py
        └── llm.py
```

## How to Run

### 1) Prerequisites
- Python 3.12+ recommended
- PostgreSQL running locally (or reachable DB URL)
- Anthropic API key (get one at https://console.anthropic.com)

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
Create a `.env` file in the project root (or copy `.env.example`) and set:
```env
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/vacation_planner
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 4) Run database migrations
```bash
alembic upgrade head
```

### 5) Start the API server
```bash
uvicorn src.main:app --reload
```

Server default URL:
- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Modules
- `Auth`: `/auth/register`, `/auth/login`
- `Users`: `/users/me`
- `Trips`: CRUD on `/trips`
- `Itinerary`: create/get/AI-generate itinerary on `/itinerary`

## LLM Integration

### How it works
When a user hits `POST /itinerary/generate`, the backend:

```
1. Reads trip details from the database
   destination, days, budget, trip_style

2. Builds a prompt using those details:
   "Plan a 3-day trip to London with budget $1500..."

3. Sends prompt to Claude Haiku via Anthropic API

4. Parses Claude's response into JSON

5. Saves the generated itinerary to the database

6. Returns the formatted itinerary to the user
```

### Prompt Engineering Techniques

| Technique | Purpose |
|-----------|---------|
| System prompt | Defines Claude as a travel planner and sets strict rules |
| User prompt | Provides trip-specific details (destination, days, budget, style) |
| Prefill (` ```json `) | Forces Claude to start response directly with JSON |
| Stop sequence (` ``` `) | Stops Claude exactly at the end of the JSON array |
| Low temperature (0.3) | Ensures consistent and predictable JSON structure |

### Example prompt
```python
prompt = f"""
Plan a {days}-day trip to {destination}.
Budget: ${budget}
Travel style: {trip_style}

Return a JSON array with {days} objects.
Each object has "day" (number) and "activities" (list of 3-5 place name strings).
"""
```

### Example AI response
```json
[
    {
        "day": 1,
        "activities": [
            "Oxford Street",
            "Liberty London",
            "Covent Garden"
        ]
    },
    {
        "day": 2,
        "activities": [
            "Victoria and Albert Museum",
            "Harrods",
            "Hyde Park"
        ]
    }
]
```

### LLM Limitations
- Claude may occasionally suggest places that don't exist
- Response quality depends on how well-known the destination is
- Very small budgets may produce unrealistic suggestions
- Claude has a knowledge cutoff and may not know very new attractions

## Notes
- Authentication uses Bearer tokens (JWT).
- Trips are scoped to the authenticated user.
- Itinerary supports one itinerary per trip (`trip_id` unique).
- AI generation reads trip details directly from the database — no extra input needed from the user.
- Background tasks log key events (registration, trip creation, itinerary creation) without blocking the response.
