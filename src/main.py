from fastapi import FastAPI

from src.routers import users, auth,trips,itinerary, knowledge



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
