# from sqlalchemy.orm import Session
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from slugify import slugify
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db_depends import get_db
from app.models.category import Category
from app.models.products import Product
from app.routers.auth import get_current_user
from app.schemas import CreateProduct

router = APIRouter(prefix='/products', tags=['products'])


@router.get('/')
async def all_products(db: Annotated[AsyncSession, Depends(get_db)]):
    res = await db.scalars(select(Product).where(Product.is_active==True, Product.stock > 0))
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There are no products')
    return res.all()


@router.post('/')
async def create_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_product: CreateProduct,
    get_user: Annotated[dict, Depends(get_current_user)],
):
    if not (get_user.get('is_admin') or get_user.get('is_supplier')):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to use this method')
    if not await db.scalar(select(Category.id).where(Category.id == create_product.category)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no category found')
    await db.execute(
        insert(Product).values(
            name=create_product.name,
            description=create_product.description,
            price=create_product.price,
            image_url=create_product.image_url,
            stock=create_product.stock,
            category_id=create_product.category, # ошибка была здесь -- указал category вместо category_id понять relationship()
            slug=slugify(create_product.name),
            rating=0,
            is_active=True,
            supplier_id=get_user.get('id'),
        )
    )
    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
    }


@router.get('/{category_slug}')
async def product_by_category(db: Annotated[AsyncSession, Depends(get_db)], category_slug: str):
    categories = list((await db.scalars(select(Category.id).where(Category.slug == category_slug))).all())
    print(categories)
    if not categories:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    categories.extend((await db.scalars(select(Category.id).where(Category.parent_id.in_(categories)))).all())
    print(categories)
    products = await db.scalars(select(Product).where(
        Product.category_id.in_(categories), Product.is_active == True, Product.stock > 0))
    return products.all()


@router.get('/detail/{product_slug}')
async def product_detail(db: Annotated[AsyncSession, Depends(get_db)], product_slug: str):
    product = await db.scalar(select(Product).where(
        Product.slug == product_slug, Product.is_active == True, Product.stock > 0))
    if product:
        return product # как здесь объект продукта превращается в JSON
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no product found')

@router.put('/{product_slug}')
async def update_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    update_product: CreateProduct,
    product_slug: str,
    get_user: Annotated[dict, Depends(get_current_user)],
):
    product = await db.scalar(select(Product).where(Product.slug == product_slug))
    print(product.supplier_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no product found')
    # здесь косяк с доступом
    if not (get_user.get('is_admin') or get_user.get('id') == product.supplier_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to use this method')
    if not await db.scalar(select(Category.id).where(Category.id == update_product.category)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no category found')
    await db.execute(update(Product).where(Product.slug == product_slug).values(
        name=update_product.name,
        description=update_product.description,
        price=update_product.price,
        image_url=update_product.image_url,
        stock=update_product.stock,
        category_id=update_product.category,
        slug=slugify(update_product.name),
        rating=0,
        is_active=True,
    ))
    await db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product update is successful',
    }


@router.delete('/{product_slug}')
async def delete_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    product_slug: str,
    get_user: Annotated[dict, Depends(get_current_user)],
):
    product = await db.scalar(select(Product).where(
        Product.slug == product_slug, Product.is_active == True))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='There is no product found')
    if not (get_user.get('is_admin') or get_user.get('id') == product.supplier_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to use this method')
    # db.execute(update(Product).where(Product.slug == product_slug).values(is_active=False))
    product.is_active = False
    await db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product delete is successful',
    }
