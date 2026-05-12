# AI Vacation Planner

Backend API for managing users, trips, and trip itineraries.

## Architecture Overview

This project is a FastAPI service with a simple layered structure:

- **API layer (`src/routers`)**: HTTP endpoints for authentication, users, trips, and itinerary.
- **Domain/data layer (`src/models`)**: SQLModel table models and request/response schemas.
- **Infrastructure layer (`src/database.py`, `src/config.py`)**: DB engine/session handling and environment settings.
- **Shared utilities (`src/utils`)**: JWT auth helpers, dependency injection helpers, and logging background tasks.
- **Schema migrations (`migrations`)**: Alembic migration history for database schema changes.

### Main Components

- `src/main.py`: creates the FastAPI app and registers all routers.
- `src/routers/auth.py`: register/login endpoints.
- `src/routers/users.py`: current authenticated user endpoint.
- `src/routers/trips.py`: create/read/update/delete user trips.
- `src/routers/itinerary.py`: create and fetch itinerary per trip.
- `src/utils/auth.py`: password hashing + JWT create/decode.
- `src/utils/deps.py`: `get_current_user` auth dependency.
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
        └── deps.py
```

## How to Run

### 1) Prerequisites

- Python 3.12+ recommended
- PostgreSQL running locally (or reachable DB URL)

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
- `Itinerary`: create/get itinerary on `/itinerary`

## Notes

- Authentication uses Bearer tokens (JWT).
- Trips are scoped to the authenticated user.
- Itinerary currently supports one itinerary per trip (`trip_id` unique).
