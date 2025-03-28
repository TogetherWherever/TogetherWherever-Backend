from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    discover,
    auth,
    create_new_trip,
    planning_details,
    users_data,
    vote,
    recently_view,
    your_trips,
    user_profile
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
app.include_router(vote.router)
app.include_router(recently_view.router)
app.include_router(your_trips.router)
app.include_router(user_profile.router)

connected_clients: List[WebSocket] = []


@app.get("/")
async def read_root():
    return {"message": "Welcome to TogetherWherever API!"}



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            for client in connected_clients:
                await client.send_json(data)  # Broadcast to all clients
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
