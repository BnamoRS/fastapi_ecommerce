from datetime import datetime, timedelta,timezone

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from sqlalchemy.util import deprecated
import jwt

from app.models.user import User
from app.schemas import CreateUser
from app.backend.db_depends import get_db

SECRET_KEY = 'dad47613223298ae5801b72045ab46aa2b69838e5047f58d7b56566e246626a4'
ALGORITHM = 'HS256'


router = APIRouter(prefix='/auth', tags=['auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
# security = HTTPBasic() базовая авторизация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# для базовой авторизации имя пользователя и пароль
# async def get_current_username(
#         db: Annotated[AsyncSession, Depends(get_db)],
#         credentials: HTTPBasicCredentials = Depends(security),
# ):
#     # не помогло против зависания без авторизации по пользователю и паролю
#     # if not credentials.username:
#     #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не предоставлен')
#     user = await db.scalar(select(User).where(User.username == credentials.username))
#     if not user or not bcrypt_context.verify(credentials.password, user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#     return user


async def create_access_token(username: str, user_id: int, is_admin: bool, is_supplier: bool, is_customer: bool,
                              expires_delta: timedelta):
    payload = {
        'sub': username,
        'id': user_id,
        'is_admin': is_admin,
        'is_supplier': is_supplier,
        'is_customer': is_customer,
        'exp': datetime.now(timezone.utc) + expires_delta,
    }
    # Преобразование datetime в timestamp (колличество секунд с начала эпохи)
    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY,algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get('sub')
        user_id: int | None = payload.get('id')
        is_admin: bool | None = payload.get('is_admin')
        is_supplier: bool | None = payload.get('is_supplier')
        is_customer: bool | None = payload.get('is_customer')
        expire: int | None = payload.get('exp')

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')
        if expire is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No acceess token supplied')
        if not isinstance(expire, int):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid token format')
        # Проверка срока действия токена
        current_time = datetime.now(timezone.utc).timestamp()

        if expire < current_time:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired!')
        return {
            'username': username,
            'id': user_id,
            'is_admin': is_admin,
            'is_supplier': is_supplier,
            'is_customer': is_customer,
        }
    # except:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail='Could not validate user'
    #     )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail= 'Token expired!')
    except jwt.exceptions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')


async def is_current_user_admin(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user.get('is_admin', False)


async def is_current_user_customer(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user.get('is_customer', False)


async def authenticate_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        username: str,
        password: str,
):
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not bcrypt_context.verify(password, user.hashed_password) or user.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    return user


@router.get('/read_current_user')
async def read_current_user(user: dict = Depends(get_current_user)):
    return {'User': user}


@router.post('/token')
async def login(
        db: Annotated[AsyncSession, Depends(get_db)],
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    # добавление для токена
    token = await create_access_token(
        user.username, user.id, user.is_admin, user.is_supplier, user.is_customer, expires_delta=timedelta(minutes=30))
    return {
        'access_token': token,    # изменит user.username на token
        'token_type': 'bearer',
    }


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_user(db: Annotated[AsyncSession, Depends(get_db)], create_user: CreateUser):
    await db.execute(
        insert(User).values(
        first_name = create_user.first_name,
        last_name = create_user.last_name,
        username = create_user.username,
        email = create_user.email,
        hashed_password = bcrypt_context.hash(create_user.password),
        )
    )
    await db.commit()
    return {'status_code': status.HTTP_201_CREATED, 'transaction': 'Successful'}


# для базовой авторизации имя пользователя и пароль
# @router.get('/user/me')
# async def read_current_user(user: dict = Depends(get_current_username)):
#     return {'User': user}
