from fastapi import APIRouter, HTTPException
from fastapi import Depends
from sqlalchemy.orm import Session
from webauthn import generate_registration_options, verify_registration_response
from webauthn.helpers import base64url_to_bytes
from typing import Dict

from app.database.connection import get_db
from app.models import User

router = APIRouter(prefix="/api/register", tags=["register"])


# Helper functions to get user from DB
def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()


# WebAuthn functions
def get_registration_options(username: str, db):
    user = get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    registration_options = generate_registration_options(
        rp_name="TogetherWherever App",
        rp_id="localhost",
        user_id=user.user_id,
        user_name=user.username,
        user_display_name=f"{user.first_name} {user.last_name}",
        user_email=user.email,
    )
    return registration_options


@router.post("/register/{username}")
async def register(username: str, db: Session = Depends(get_db)):
    registration_options = get_registration_options(username, db)
    return {"options": registration_options}


@router.post("/register/response")
async def register_response(response: Dict, db: Session = Depends(get_db)):
    try:
        verification = verify_registration_response(response)
        user_data = verification["user"]

        new_user = User(
            username=user_data["name"],
            user_id=user_data["id"],
            public_key=base64url_to_bytes(user_data["publicKey"]),
            credential_id=user_data["id"]
        )

        db.add(new_user)
        db.commit()
        return {"status": "Registration successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Registration failed")
