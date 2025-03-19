from sqlalchemy import Column, Integer, String, ForeignKey, Enum, CheckConstraint
from sqlalchemy.orm import relationship

from app.models import Base


class Vote(Base):
    """
    Model for storing vote information
    """
    __tablename__ = "votes"

    vote_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, ForeignKey("users.username"), nullable=False)
    trip_day_id = Column(Integer, ForeignKey("trip_days.trip_day_id"), nullable=False)
    vote_status = Column(Enum("pending", "voting", "complete", name="vote_status_enum"), nullable=False)
    vote_score = Column(Integer, nullable=False, default=0)

    # Enforce vote_score range
    __table_args__ = (CheckConstraint("vote_score >= 0 AND vote_score <= 10", name="check_vote_score"),)

    # Relationship with User
    user = relationship("User", back_populates="votes")

    # Relationship with Activities
    trip_days = relationship("TripDays", back_populates="votes")
