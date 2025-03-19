from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models import Base


class User(Base):
    """
    Model for storing user information
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    preferences = Column(String)

    # Relationship with Trips
    trips = relationship("Trips", back_populates="users")

    # Relationship with Vote
    votes = relationship("Vote", back_populates="users")
