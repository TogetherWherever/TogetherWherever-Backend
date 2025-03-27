from pydantic import BaseModel


class PatchActivitiesOrder(BaseModel):
    """
    Pydantic model for updating the order of activities in a trip day.

    action: The action to be performed. e.g. "move-up", "move-down".
    destinationID: The ID of the destination.
    newOrder: The new order of the activity.
    oldOrder: The old order of the activity.
    tripDay: The day number of the trip. e.g. 1, 2, 3, ...
    tripId: The ID of the trip.
    """
    action: str
    destinationID: str
    newOrder: int
    oldOrder: int
    tripDay: int
    tripId: int
