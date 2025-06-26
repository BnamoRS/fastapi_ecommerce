from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.backend.db_depends import get_db
from app.models.products import Product
from app.models.reviews import Review
from app.routers.auth import (get_current_user, is_current_user_admin,
                              is_current_user_customer)
from app.schemas import CreateReview

router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/')
async def all_reviews(db: Annotated[AsyncSession, Depends(get_db)]):
    reviews = (await db.scalars(select(Review).where(Review.is_active == True))).all()
    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reviews not found')
    return reviews


@router.get('/{product_id}')
async def products_reviews(
        db: Annotated[AsyncSession, Depends(get_db)],
        product_id: int,
):
    product = await db.scalar(select(Product).where(Product.id == product_id, Product.is_active == True))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')
    reviews = (await db.scalars(
        select(Review).where(Review.product_id == product.id, Review.is_active == True))).all()
    if not reviews:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reviews not found')
    return reviews


@router.post('/')
async def add_reviews(
        db: Annotated[AsyncSession, Depends(get_db)],
        create_review: CreateReview,
        get_user: Annotated[dict, Depends(get_current_user)],
):
    if not get_user.get('is_customer'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,  detail='You are not authorized to use this method')
    product_id = await db.scalar(
        select(Product.id).where(Product.id == create_review.product_id, Product.is_active == True))
    if not product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no product found')
    user_id = get_user.get('id')
    if await db.scalar(
            select(Review.id).where(
                Review.product_id == product_id, Review.user_id == user_id, Review.is_active == True)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User review exists')
    await db.execute(insert(Review).values(
        user_id = user_id,
        product_id = product_id,
        comment = create_review.comment,
        grade = create_review.grade,
    ))
    subq = (
        select(func.avg(Review.grade))
        .where(Review.product_id == product_id, Review.is_active == True)
        .group_by(Review.product_id)
        .scalar_subquery()
    )
    # product_rating = await db.scalar(
    #     select(func.avg(Review.grade).label('rating'), Review.product_id)
    #     .where(Review.product_id == product_id, Review.is_active == True)
    #     .group_by(Review.product_id)
    # )
    await db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(rating = subq))
    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
    }


@router.delete('/{review_id}')
async def delete_reviews(
        db: Annotated[AsyncSession, Depends(get_db)],
        review_id: int,
        current_user_is_admin: Annotated[bool, Depends(is_current_user_admin)],
):
    if not current_user_is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to use this method')
    review = await db.scalar(select(Review).where(Review.id == review_id, Review.is_active == True))
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Review not found')
    review.is_active = False
    subq = (
        select(func.avg(Review.grade))
        .where(Review.product_id == review.product_id, Review.is_active == True)
        .group_by(Review.product_id)
        .scalar_subquery()
    )
    await db.execute(
        update(Product)
        .where(Product.id == review.product_id)
        .values(rating=subq)
    )
    # await db.execute(
    #     update(Product).where(Product.id == review.product_id).values(
    #         rating = await db.scalar(
    #             select(func.avg(Review.grade), Review.product_id).where(
    #                 Review.product_id == review.product_id, Review.is_active == True).group_by(Review.product_id)))
    # )
    await db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Review delete is successful',
    }
