from sqlalchemy import Column, String, AutoIncrement, Integer, BINARY
from app.models.trips import Base


class User(Base):
    """
    Model for storing user information

    user_id: Unique identifier for the user
    username: Username for the user
    email: Email address of the user
    first_name: First name of the user
    last_name: Last name of the user
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, AutoIncrement=True)
    username = Column(String, unique=True, nullable=False)
    credential_id = Column(String, unique=True)
    public_key = Column(BINARY)
    first_name = Column(String)
    last_name = Column(String)
