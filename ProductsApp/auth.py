from fastapi import FastAPI, Depends, HTTPException,status
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = 'glz0sTnsbsoAAW2l5PVegb9Rf9Vi49JF1NCw_HIz5J0'
ALGORITHM = 'HS256'

app = FastAPI()
models.Base.metadata.create_all(bind=engine)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oAuth_bearer = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_hashed_password(password):
    return bcrypt_context.hash(password)


def verify_user(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(user_name: str, password: str, db):
    user = db.query(models.User).filter(models.User.username == user_name).first()
    if not user or not verify_user(password, user.password):
        return False
    return True


def generate_jwt_token(user_name: str, user_id: int, expire_delta: Optional[timedelta]):
    encode = {"sub":user_name, "id": user_id}
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=20)
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, ALGORITHM)


def get_current_user(token: oAuth_bearer = Depends()):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        userid: int = payload.get("id")
        if not username or not userid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized")
        return {"user_name": username, "user_id": userid }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized")


class Users(BaseModel):
    id: Optional[int]
    username: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    password: str


@app.post("/users/create_user")
async def creating_user(new_user: Users, db: Session = Depends(get_db)):
    user = models.User()

    user.username = new_user.username
    user.email = new_user.email
    user.first_name = new_user.first_name
    user.last_name = new_user.last_name
    user.password = get_hashed_password(new_user.password)

    db.add(user)
    db.commit()
    return get_status(201)


@app.post("/generate_token")
async def generate_token(user_form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    if not authenticate_user(user.username, user_form.password, db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized")

    time_expires = timedelta(minutes=15)
    token = generate_jwt_token(user.username, user.id, time_expires)

    return {"token": token}


@app.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


def get_status(status_code):
    return {
        "status code": status_code,
        "transaction": "successful"
    }



