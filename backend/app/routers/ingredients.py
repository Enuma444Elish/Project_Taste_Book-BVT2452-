from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import get_database_session
from backend.app.models import Ingredient
from backend.app.schemas.ingredient import (
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
)


router = APIRouter(
    prefix="/ingredients",
    tags=["Ингредиенты"],
)


def get_ingredient_or_404(
    ingredient_id: int,
    session: Session,
) -> Ingredient:
    ingredient = session.get(Ingredient, ingredient_id)

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ингредиент не найден",
        )

    return ingredient


@router.get(
    "",
    response_model=list[IngredientRead],
)
def get_ingredients(
    session: Session = Depends(get_database_session),
) -> list[Ingredient]:
    statement = select(Ingredient).order_by(Ingredient.name)

    return list(session.scalars(statement).all())


@router.get(
    "/{ingredient_id}",
    response_model=IngredientRead,
)
def get_ingredient(
    ingredient_id: int,
    session: Session = Depends(get_database_session),
) -> Ingredient:
    return get_ingredient_or_404(ingredient_id, session)


@router.post(
    "",
    response_model=IngredientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ingredient(
    data: IngredientCreate,
    session: Session = Depends(get_database_session),
) -> Ingredient:
    duplicate_statement = select(Ingredient).where(
        func.lower(Ingredient.name) == data.name.lower()
    )

    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ингредиент с таким названием уже существует",
        )

    ingredient = Ingredient(
        name=data.name,
        is_common_allergen=data.is_common_allergen,
    )

    session.add(ingredient)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ингредиент с таким названием уже существует",
        )

    session.refresh(ingredient)

    return ingredient


@router.put(
    "/{ingredient_id}",
    response_model=IngredientRead,
)
def update_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    session: Session = Depends(get_database_session),
) -> Ingredient:
    ingredient = get_ingredient_or_404(ingredient_id, session)

    duplicate_statement = select(Ingredient).where(
        func.lower(Ingredient.name) == data.name.lower(),
        Ingredient.id != ingredient_id,
    )

    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ингредиент с таким названием уже существует",
        )

    ingredient.name = data.name
    ingredient.is_common_allergen = data.is_common_allergen

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось изменить ингредиент",
        )

    session.refresh(ingredient)

    return ingredient


@router.delete(
    "/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ingredient(
    ingredient_id: int,
    session: Session = Depends(get_database_session),
) -> Response:
    ingredient = get_ingredient_or_404(ingredient_id, session)

    session.delete(ingredient)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ингредиент используется в рецептах. "
                "Сначала удалите его из рецептов."
            ),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)