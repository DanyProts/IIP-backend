from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.user_service import models, schemas, security, db

router = APIRouter(tags=["Authentication"])

@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_data: schemas.UserCreate, db: Session = Depends(db.get_db)):
    """Register a new user."""
    # Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")
    # Create new User record
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=security.get_password_hash(user_data.password),
        role="student"
    )
    new_user.join_date = datetime.utcnow()
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user  # FastAPI will convert this to UserOut schema
@router.post("/login", response_model=schemas.Token)
def login(form: schemas.UserLogin, db: Session = Depends(db.get_db)):

    """Authenticate a user and return a JWT token."""
    # Note: Using UserCreate schema for form dependency to parse email & password from body.
    # In request body, provide {"email": "...", "password": "..."}.
    email = form.email
    password = form.password
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not security.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Update last_visit timestamp
    user.last_visit = datetime.utcnow()
    db.commit()
    # Create JWT token with user ID and role
    token_data = {"user_id": user.id, "role": user.role}
    token = security.create_access_token(token_data)
    return {"access_token": token, "token_type": "bearer"}

# OAuth2 scheme for getting the token from the Authorization header (Bearer token)
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(db: Session = Depends(db.get_db), token: str = Depends(oauth2_scheme)):
    """Validate JWT and return the current user (for protected routes)."""
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")
    # Get the user from database
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    """Get current logged-in user's info."""
    return current_user
