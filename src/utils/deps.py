from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from src.database import get_session
from src.models.user import User
from src.models.trip import Trip
from src.utils.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user

def fetch_owned_trip(trip_id: int, current_user: User, session: Session) -> Trip:
    """
    Fetch a trip by id and verify the current user owns it.
    Plain function so it can be reused both as a path-based
    dependency (get_owned_trip) and from routes where trip_id
    comes from the request body instead of the URL.
    """
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return trip

def get_owned_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Trip:
    """
    Dependency for routes where trip_id is a URL path parameter.
    """
    return fetch_owned_trip(trip_id, current_user, session)
