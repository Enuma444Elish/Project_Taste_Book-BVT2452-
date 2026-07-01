from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import get_database_session
from backend.app.models import Category
from backend.app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)


router = APIRouter(
    prefix="/categories",
    tags=["Категории"],
)


def get_category_or_404(
    category_id: int,
    session: Session,
) -> Category:
    category = session.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    return category


@router.get(
    "",
    response_model=list[CategoryRead],
)
def get_categories(
    session: Session = Depends(get_database_session),
) -> list[Category]:
    statement = select(Category).order_by(Category.name)

    return list(session.scalars(statement).all())


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
)
def get_category(
    category_id: int,
    session: Session = Depends(get_database_session),
) -> Category:
    return get_category_or_404(category_id, session)


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: CategoryCreate,
    session: Session = Depends(get_database_session),
) -> Category:
    duplicate_statement = select(Category).where(
        func.lower(Category.name) == data.name.lower()
    )

    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким названием уже существует",
        )

    category = Category(name=data.name)

    session.add(category)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким названием уже существует",
        )

    session.refresh(category)

    return category


@router.put(
    "/{category_id}",
    response_model=CategoryRead,
)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    session: Session = Depends(get_database_session),
) -> Category:
    category = get_category_or_404(category_id, session)

    duplicate_statement = select(Category).where(
        func.lower(Category.name) == data.name.lower(),
        Category.id != category_id,
    )

    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким названием уже существует",
        )

    category.name = data.name

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось изменить категорию",
        )

    session.refresh(category)

    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category_id: int,
    session: Session = Depends(get_database_session),
) -> Response:
    category = get_category_or_404(category_id, session)

    session.delete(category)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)