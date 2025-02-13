from fastapi import APIRouter, HTTPException
from fastapi import Depends
from sqlalchemy.orm import Session
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import AuthenticationCredential

from app.database.connection import get_db
from app.models import User
from app.schemas.user import UserCreate

router = APIRouter(prefix="/api/login", tags=["register"])

@router.post("/start")
def start_authentication(user: UserCreate, db: Session = Depends(get_db)):
    """
    Start the authentication process for a user
    """
    user = db.query(User).filter(User.username == user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    options = generate_authentication_options(rp_id="localhost")
    return options


@router.post("/finish")
def finish_authentication(response: AuthenticationCredential, user: UserCreate, db: Session = Depends(get_db)):
    """
    Finish the authentication process for a user
    """
    user = db.query(User).filter(User.username == user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    verified_authentication = verify_authentication_response(response, credential_public_key=user.public_key)
    if not verified_authentication:
        raise HTTPException(status_code=400, detail="Authentication failed")
    return {"message": "User authenticated successfully"}