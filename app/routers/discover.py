import os
import requests
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/discover-place-details", tags=["discover"])

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

@router.get("/")
async def discover_place_details(place_id: str = Query(..., min_length=1)):
    """
    Fetch place details from Google Places API.

    :return:
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"

    payload = {}
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': '*'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # check if the response is successful
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    return response.json()