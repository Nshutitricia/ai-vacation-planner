from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from AI_Vacation_Planner.src.database import get_session
from AI_Vacation_Planner.src.models.user import User
from AI_Vacation_Planner.src.utils.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session())) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user
