from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    Pydantic model for creating a new user.

    username: Username of the user
    email: Email of the user
    first_name: First name of the user
    last_name: Last name of the user
    password: Password of the user
    preferences: User preferences
    """
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    preferences: str
