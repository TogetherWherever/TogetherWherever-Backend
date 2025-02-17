from datetime import date

from pydantic import BaseModel


class CreateNewTrip(BaseModel):
    """
    Schema for creating a new trip

    owner: username of the owner of the trip
    trip_name: Name of the trip
    dest_id: Google Places Destination ID
    dest_name: Name of the main destination
    start_date: Start date of the trip
    end_date: End date of the trip
    duration: Number of days for the trip
    companion: Comma-separated string of companion IDs
    """
    owner: str
    trip_name: str
    dest_id: str
    dest_name: str
    start_date: date
    end_date: date
    duration: int
    companion: str  # Keep as string since frontend sends comma-separated IDs

    class Config:
        orm_mode = True
