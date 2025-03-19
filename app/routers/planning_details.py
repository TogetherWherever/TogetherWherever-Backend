import os

from dotenv import load_dotenv
from fastapi import APIRouter

router = APIRouter(prefix="/api/planning-details", tags=["planning-details"])

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


