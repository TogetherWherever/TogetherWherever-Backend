from typing import Dict

from pydantic import BaseModel


class PatchVoteScore(BaseModel):
    """
    Pydantic model for updating the vote score of a trip.

    trip_id: The ID of the trip.
    trip_day_number: The day number of the trip. e.g. 1, 2, 3, ...
    voted_person: The username of the person who voted.
    scores: The scores given by the user for the destinations. e.g. {"01A": 10, "02A": 8, "03A": 7}
    """
    trip_id: int
    trip_day_number: int
    voted_person: str
    scores: Dict[str, int]
