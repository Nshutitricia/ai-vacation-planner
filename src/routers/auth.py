from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from src.database import get_session
from src.models.user import UserResponse, UserCreate, User
from src.utils.auth import hash_password, verify_password, create_access_token

from src.utils.background_tasks import send_welcome_message,track_login_activity


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User.model_validate(
        user_data,
        update={"hashed_password": hash_password(user_data.password)}
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    background_tasks.add_task(
        send_welcome_message,
        username = user.username,
        email = user.email
    )
    return user

@router.post("/login")
def login(background_tasks: BackgroundTasks,form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id)})

    background_tasks.add_task(
        track_login_activity,
        username = form_data.username
    )
    return {"access_token": token, "token_type": "bearer"}
