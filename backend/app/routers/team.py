import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.database import get_session
from app.models import TeamUser
from app.security import check_password, hash_password, team_serializer

router = APIRouter(prefix="/team", tags=["team"])
DUMMY_HASH = hash_password("not-a-real-account")


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(body: Login, session: Session = Depends(get_session)):
    user = session.exec(select(TeamUser).where(TeamUser.username == body.username.strip().lower())).first()
    valid = check_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not user.is_active or not valid:
        raise HTTPException(401, "Invalid credentials")
    token = team_serializer().dumps({"id": user.id, "version": hashlib.sha256(user.password_hash.encode()).hexdigest()})
    return {"token": token, "display_name": user.display_name}
