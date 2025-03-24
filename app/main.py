from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    discover,
    auth,
    create_new_trip,
    planning_details,
    users_data
)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(discover.router)
app.include_router(auth.router)
app.include_router(create_new_trip.router)
app.include_router(planning_details.router)
app.include_router(users_data.router)


@app.get("/")
async def read_root():
    return {"message": "Welcome to TogetherWherever API!"}
