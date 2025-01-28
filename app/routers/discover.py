from fastapi import APIRouter

router = APIRouter(prefix="/discover", tags=["discover"])

@router.get("/")
async def get_discover():
    # Example logic
    return {"message": "Discover destinations!"}