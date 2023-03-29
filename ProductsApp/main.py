from fastapi import FastAPI, Depends, HTTPException,status
import models
from database import engine, SessionLocal
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from auth import get_current_user

app = FastAPI()
models.Base.metadata.create_all(bind=engine)


class Products(BaseModel):
    id: Optional[int]
    product_name: str = Field(min_length=1, max_length=100)
    product_price: int = Field(gt=0)
    product_rating: int = Field(gt=0, lt=6)
    product_verified: bool
    owner_id: Optional[int]


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.post("/product/create_product")
async def create_new_product(new_product: Products, user:dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authorized!')
    product_model = models.Products()

    product_model.product_name = new_product.product_name
    product_model.product_price = new_product.product_price
    product_model.product_rating = new_product.product_rating
    product_model.product_verified = new_product.product_verified
    product_model.owner_id = user.get("user_id")

    db.add(product_model)
    db.commit()

    return get_status(201)


@app.get("/get_all_products")
async def get_all_products(db: Session = Depends(get_db)):
    return db.query(models.Products).all()


@app.get("/products/user")
async def get_products_by_user(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized")
    return db.query(models.Products).filter(models.Products.owner_id == user.get("user_id")).all()


@app.put("/products/update_product")
async def update_products(update_product: Products,
                          user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authorized!')

    product_model = db.query(models.Products).filter(models.Products.id == update_product.id).\
        filter(models.Products.owner_id == user.get("user_id")).first()

    product_model.product_name = update_product.product_name
    product_model.product_price = update_product.product_price
    product_model.product_rating = update_product.product_rating
    product_model.product_verified = update_product.product_verified

    db.add(product_model)
    db.commit()

    return get_status(200)


@app.delete("/products/delete_product/{product_id}")
async def delete_products(product_id: int,
                          user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authorized')

    product = db.query(models.Products).filter(models.Products.id == product_id).\
        filter(models.Products.owner_id == user.get("user_id")).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product Not found!")

    db.query(models.Products).filter(models.Products.id == product_id).\
        filter(models.Products.owner_id == user.get("user_id")).delete()
    db.commit()

    return get_status(200)


def get_status(status_code):
    return {
        "status": status_code,
        "transaction": "successful"
    }
