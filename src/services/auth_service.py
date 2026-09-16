from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from src.models.user import User, UserCreate
from src.utils.auth import hash_password, verify_password, create_access_token


class AuthService:

    def register(self, user_data: UserCreate, session: Session) -> User:
        user = User.model_validate(
            user_data,
            update={"hashed_password": hash_password(user_data.password)}
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ValueError("Email or username already registered")
        session.refresh(user)
        return user

    def authenticate(self, username: str, password: str, session: Session) -> User:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Incorrect username or password")
        return user

    def create_token_for(self, user: User) -> str:
        return create_access_token({"sub": str(user.id)})
