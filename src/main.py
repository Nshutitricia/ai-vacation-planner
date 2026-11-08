from fastapi import FastAPI

from src.observability.datadog import init_datadog

init_datadog()  # before the routers import the LLM libraries; a no-op unless enabled

from src.routers import users, auth,trips,itinerary, knowledge, voice



app = FastAPI(
    title="AI Vacation Planner",
    description="A simple API for AI Vacation Planner",
    version="1.0",
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itinerary.router)
app.include_router(knowledge.router)
app.include_router(voice.router)
