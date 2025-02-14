from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import SessionLocal
from app.routers import (
    discover,
    create_new_trip
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
app.include_router(create_new_trip.router)


@app.get("/")
async def read_root():
    return {"message": "Welcome to TogetherWherever API!"}
