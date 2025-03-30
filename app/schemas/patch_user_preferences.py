from typing import List

from pydantic import BaseModel


class PatchUserPreferences(BaseModel):
    """
    The schema for updating the user's preferences.

    :param username: The username of the user who is updating the preferences.
    :param preferences: The list of preferences to update.
    """
    username: str
    preferences: List[str]
