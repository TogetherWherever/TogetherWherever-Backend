from fastapi import FastAPI
from .routers import (
    discover
)

app = FastAPI()

app.include_router(discover.router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to TogetherWherever API!"}
