from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=schemas.Token, status_code=201)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register an athlete or scout.

    Change: the original returned a bare UserOut, so the client had to make a
    second /auth/login call right after signing up. It now returns a token
    directly, matching what the frontend actually needs.
    """
    # BUGFIX: email comparison was case-sensitive, so "A@b.com" and "a@b.com"
    # could both register and then collide at login.
    email = user_in.email.lower().strip()
    existing = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=user_in.name.strip(),
        email=email,
        hashed_password=auth.hash_password(user_in.password),
        age=user_in.age,
        gender=user_in.gender,
        state=user_in.state,
        district=user_in.district,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """`username` is the athlete's email address."""
    email = form_data.username.lower().strip()
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email)
        .first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(auth.get_current_user)):
    """Lets the frontend restore a session from a stored token."""
    return current_user
