from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from src.database import get_session
from src.models.user import UserResponse, UserCreate

from src.utils.background_tasks import send_welcome_message, track_login_activity
from src.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])

auth_service = AuthService()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    try:
        user = auth_service.register(user_data, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(
        send_welcome_message,
        email=user.email,
        username=user.username
    )

    return user

@router.post("/login")
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    try:
        user = auth_service.authenticate(form_data.username, form_data.password, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = auth_service.create_token_for(user)

    background_tasks.add_task(
        track_login_activity,
        username=form_data.username
    )
    return {"access_token": token, "token_type": "bearer"}
