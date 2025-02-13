from pydantic import BaseModel


class UserBase(BaseModel):
    """
    Base class for User schema

    username: Username for the user
    email: Email address of the user
    first_name: First name of the user
    last_name: Last name of the user
    """
    username: str
    email: str
    first_name: str
    last_name: str


class UserCreate(UserBase):
    """
    Create class for User schema
    """
    pass


class UserResponse(UserBase):
    """
    Response class for User schema

    user_id: Unique identifier for the user
    """
    id: str
    username: str

    class Config:
        orm_mode = True
