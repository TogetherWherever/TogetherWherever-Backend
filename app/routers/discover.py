import asyncio
import json
import os
from typing import List, Dict

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query

load_dotenv()

router = APIRouter(prefix="/api/discover-place-details", tags=["discover"])

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def get_photo(photo_name: str) -> str:
    """
    Get a single photo from Google Places API (Place Photo).
    :param photo_name: Photo name
    :return: Photo URL
    """
    headers = {'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY}
    url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=300&maxWidthPx=300"
    res = requests.get(url, headers=headers, allow_redirects=False)

    if res.status_code == 302:  # Google redirects to actual image
        return res.headers["Location"]
    else:
        print(f"Error fetching photo: {res.text}")  # Debugging
        return None


async def get_nearby_places(lat: float, lon: float, max_result: int, radius: int, g_fields: str) -> List[Dict]:
    """
    Get nearby places from Google Places API (Nearby Search).
    :param lat: Latitude
    :param lon: Longitude
    :param max_result: The number of maximum results to return.
    :param radius: The radius in meters to search within.
    :param g_fields: The fields to fetch.
    :return: List of nearby places
    """
    response = await get_nearby_places_from_api(g_fields, lat, lon, max_result, radius)

    nearby_places = []
    for place in response.get("places", []):
        photo = None
        if place.get("photos"):
            photo_name = place["photos"][0]["name"]
            photo = await get_photo(photo_name)

        place_data = {
            "destID": place.get("id"),
            "destName": place.get("displayName")["text"],
            "photos": photo if photo else ""
        }
        nearby_places.append(place_data)

    return nearby_places


async def get_nearby_places_from_api(g_fields, lat, lon, max_result, radius):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = json.dumps({
        # Exclude certain place types to avoid irrelevant results
        "excludedTypes": ["car_dealer", "car_rental", "car_repair", "car_wash", "electric_vehicle_charging_station",
                          "gas_station", "parking", "rest_stop", "city_hall", "courthouse", "embassy", "fire_station",
                          "government_office", "local_government_office", "police", "post_office", "chiropractor",
                          "dental_clinic", "dentist", "doctor", "drugstore", "hospital", "pharmacy", "physiotherapist",
                          "medical_lab", "apartment_building", "apartment_complex", "condominium_complex",
                          "housing_complex", "bed_and_breakfast", "hotel", "motel", "lodging", "accounting", "atm",
                          "bank", "funeral_home", "insurance_agency", "lawyer", "real_estate_agency", "storage",
                          "telecommunications_service_provider", "department_store", "electronics_store",
                          "grocery_store", "hardware_store", "supermarket", "warehouse_store", "airport",
                          "train_station"],
        "maxResultCount": max_result,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": radius
            }
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': g_fields
    }
    res = requests.request("POST", url, headers=headers, data=payload)
    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")
    return response


def open_hours_format(opening_hours: List[Dict]) -> Dict[str, Dict[str, str]]:
    """
    Format opening hours from Google Places API.
    :param opening_hours: Opening hours data
    :return: Formatted opening hours
    """
    if not opening_hours:
        return {
            "Sunday": {"open": "00:00", "close": "23:59"},
            "Monday": {"open": "00:00", "close": "23:59"},
            "Tuesday": {"open": "00:00", "close": "23:59"},
            "Wednesday": {"open": "00:00", "close": "23:59"},
            "Thursday": {"open": "00:00", "close": "23:59"},
            "Friday": {"open": "00:00", "close": "23:59"},
            "Saturday": {"open": "00:00", "close": "23:59"}
        }

    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    formatted_hours = {}
    for period in opening_hours:
        day = period["open"]["day"]
        open_time = f"{period['open']['hour']:02d}:{period['open']['minute']:02d}"
        close_time = f"{period['close']['hour']:02d}:{period['close']['minute']:02d}"
        formatted_hours[day_names[day]] = {"open": open_time, "close": close_time}

    return formatted_hours


async def get_place_details(dest_id: str, g_fields: str) -> Dict:
    """
    Fetch place details from Google Places API.

    :param dest_id: Google Places Destination ID
    :param g_fields: Fields to fetch
    :return: Place details
    """
    url = f"https://places.googleapis.com/v1/places/{dest_id}?fields={g_fields}"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_PLACES_API_KEY
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=f"Google Places API error: {res.text}")
    try:
        response = res.json()
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Google Places API")
    return response


@router.get("/")
async def discover_place_details(dest_id: str = Query(..., min_length=1)) -> Dict:
    """
    Fetch place details from Google Places API (Place Details).
    :param dest_id: Google Places Destination ID
    :return: Place details
    """
    g_fields = "id,displayName,types,editorialSummary,rating,formattedAddress,internationalPhoneNumber,goodForChildren,accessibilityOptions,photos,location,regularOpeningHours"
    response = await get_place_details(dest_id, g_fields)

    # Fetch photos and nearby places concurrently
    photo_names = [photo["name"] for photo in response.get("photos", [])]
    lat = response.get("location", {}).get("latitude")
    lon = response.get("location", {}).get("longitude")

    g_fields_for_nearby = 'places.id,places.displayName,places.photos'
    photos, nearby_places = await asyncio.gather(
        asyncio.gather(*(get_photo(photo_name) for photo_name in photo_names)) if photo_names else [],
        get_nearby_places(lat, lon, 8, 5000, g_fields_for_nearby) if lat and lon else []
    )

    return {
        "destID": dest_id,
        "destName": response.get("displayName")["text"],
        "destType": response.get("types"),
        "desc": response.get("editorialSummary")["text"] if response.get("editorialSummary") else "",
        "rating": response.get("rating"),
        "address": response.get("formattedAddress"),
        "phoneNum": response.get("internationalPhoneNumber"),
        "fac": {
            "goodForChildren": response.get("goodForChildren"),
            "accessibility": response.get("accessibilityOptions"),
        },
        "photos": photos,
        "lat": lat,
        "lon": lon,
        "nearbyPlaces": nearby_places,
        "openingHours": open_hours_format(
            response.get("regularOpeningHours")["periods"] if response.get("regularOpeningHours") else [])
    }
