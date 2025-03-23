from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, Boolean

from app.models import Base


class VoteScores(Base):
    """
    Model for storing vote information
    """
    __tablename__ = "vote_scores"

    vote_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recommended_place_id = Column(Integer, ForeignKey("recommended_places.recommended_place_id"), nullable=False)
    username = Column(String, ForeignKey("users.username"), nullable=False)
    vote_score = Column(Integer, nullable=False, default=0)
    is_voted = Column(Boolean, default=False)

    # Enforce vote_score range
    __table_args__ = (CheckConstraint("vote_score >= 0 AND vote_score <= 10", name="check_vote_score"),)
