from fastapi import APIRouter, Depends

from src.models.user import UserResponse, User
from src.utils.deps import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User= Depends(get_current_user)):
    return current_user
