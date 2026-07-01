from enum import Enum
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.app.database import get_database_session
from backend.app.models import Category, Ingredient, Recipe
from backend.app.schemas.recipe import (
    CalculatedIngredient,
    RecipeCalculationRead,
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
)
from backend.app.services.image_service import (
    MAX_IMAGE_FILE_SIZE,
    ImageTooLargeError,
    ImageValidationError,
    delete_recipe_image,
    save_recipe_image,
)


router = APIRouter(
    prefix="/recipes",
    tags=["Рецепты"],
)

class IngredientMatchMode(str, Enum):
    ALL = "all"
    ANY = "any"


class RecipeSort(str, Enum):
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"
    TIME_ASC = "time_asc"
    TIME_DESC = "time_desc"
    CALORIES_ASC = "calories_asc"
    CALORIES_DESC = "calories_desc"


def make_search_pattern(value: str) -> str:
    value = value.strip()

    # Экранируем специальные символы SQL LIKE.
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")

    return f"%{value}%"

def get_recipe_or_404(
    recipe_id: int,
    session: Session,
) -> Recipe:
    statement = (
        select(Recipe)
        .options(
            selectinload(Recipe.categories),
            selectinload(Recipe.ingredients),
        )
        .where(Recipe.id == recipe_id)
    )

    recipe = session.scalar(statement)

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рецепт не найден",
        )

    return recipe


def get_categories_by_ids(
    category_ids: list[int],
    session: Session,
) -> list[Category]:
    statement = select(Category).where(
        Category.id.in_(category_ids)
    )

    categories = list(session.scalars(statement).all())
    found_ids = {category.id for category in categories}
    missing_ids = sorted(set(category_ids) - found_ids)

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Некоторые категории не найдены",
                "missing_category_ids": missing_ids,
            },
        )

    return categories


def get_ingredients_by_ids(
    ingredient_ids: list[int],
    session: Session,
) -> list[Ingredient]:
    statement = select(Ingredient).where(
        Ingredient.id.in_(ingredient_ids)
    )

    ingredients = list(session.scalars(statement).all())
    found_ids = {ingredient.id for ingredient in ingredients}
    missing_ids = sorted(set(ingredient_ids) - found_ids)

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Некоторые ингредиенты не найдены",
                "missing_ingredient_ids": missing_ids,
            },
        )

    return ingredients


def apply_recipe_data(
    recipe: Recipe,
    data: RecipeCreate | RecipeUpdate,
    categories: list[Category],
    ingredients: list[Ingredient],
) -> None:
    recipe.title = data.title
    recipe.description = data.description
    recipe.base_servings = data.base_servings
    recipe.total_time_minutes = data.total_time_minutes
    recipe.calories_per_serving = data.calories_per_serving

    recipe.ingredients_with_amounts = [
        item.model_dump(mode="json")
        for item in data.ingredients_with_amounts
    ]

    recipe.cooking_steps = [
        step.model_dump(mode="json")
        for step in data.cooking_steps
    ]

    recipe.categories = categories
    recipe.ingredients = ingredients


@router.get(
    "",
    response_model=list[RecipeRead],
)
def get_recipes(
    query: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Поиск по названию рецепта",
    ),
    ingredient_query: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
        description="Поиск по названию ингредиента",
    ),
    category_ids: list[int] | None = Query(
        default=None,
        description="Категории рецепта",
    ),
    ingredient_ids: list[int] | None = Query(
        default=None,
        description="Ингредиенты, которые должны быть в рецепте",
    ),
    ingredient_match: IngredientMatchMode = Query(
        default=IngredientMatchMode.ALL,
        description=(
            "all — должны присутствовать все ингредиенты; "
            "any — достаточно одного"
        ),
    ),
    excluded_ingredient_ids: list[int] | None = Query(
        default=None,
        description="Ингредиенты, которых не должно быть",
    ),
    exclude_common_allergens: bool = Query(
        default=False,
        description="Исключить распространённые аллергены",
    ),
    max_time_minutes: int | None = Query(
        default=None,
        gt=0,
        description="Максимальное время приготовления",
    ),
    max_calories: float | None = Query(
        default=None,
        ge=0,
        description="Максимальная калорийность одной порции",
    ),
    sort: RecipeSort = Query(
        default=RecipeSort.TITLE_ASC,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    session: Session = Depends(get_database_session),
) -> list[Recipe]:
    statement = select(Recipe).options(
        selectinload(Recipe.categories),
        selectinload(Recipe.ingredients),
    )

    # Поиск по названию рецепта.
    if query and query.strip():
        title_pattern = make_search_pattern(query)

        statement = statement.where(
            Recipe.title.ilike(
                title_pattern,
                escape="\\",
            )
        )

    # Поиск по названию ингредиента.
    if ingredient_query and ingredient_query.strip():
        ingredient_pattern = make_search_pattern(
            ingredient_query
        )

        statement = statement.where(
            Recipe.ingredients.any(
                Ingredient.name.ilike(
                    ingredient_pattern,
                    escape="\\",
                )
            )
        )

    # Рецепт должен относиться хотя бы к одной
    # из выбранных категорий.
    if category_ids:
        unique_category_ids = list(set(category_ids))

        statement = statement.where(
            Recipe.categories.any(
                Category.id.in_(unique_category_ids)
            )
        )

    # Фильтрация по выбранным ингредиентам.
    if ingredient_ids:
        unique_ingredient_ids = list(
            set(ingredient_ids)
        )

        if ingredient_match == IngredientMatchMode.ALL:
            # Добавляем отдельное условие для каждого ингредиента.
            # В результате рецепт должен содержать их все.
            for ingredient_id in unique_ingredient_ids:
                statement = statement.where(
                    Recipe.ingredients.any(
                        Ingredient.id == ingredient_id
                    )
                )
        else:
            # Достаточно одного ингредиента из списка.
            statement = statement.where(
                Recipe.ingredients.any(
                    Ingredient.id.in_(
                        unique_ingredient_ids
                    )
                )
            )

    # Режим исключения ингредиентов и аллергенов.
    if excluded_ingredient_ids:
        unique_excluded_ids = list(
            set(excluded_ingredient_ids)
        )

        statement = statement.where(
            ~Recipe.ingredients.any(
                Ingredient.id.in_(unique_excluded_ids)
            )
        )

    # Исключаем рецепты, содержащие ингредиенты
    # с флагом is_common_allergen=True.
    if exclude_common_allergens:
        statement = statement.where(
            ~Recipe.ingredients.any(
                Ingredient.is_common_allergen.is_(True)
            )
        )

    if max_time_minutes is not None:
        statement = statement.where(
            Recipe.total_time_minutes
            <= max_time_minutes
        )

    if max_calories is not None:
        statement = statement.where(
            Recipe.calories_per_serving
            <= max_calories
        )

    sort_expressions = {
        RecipeSort.TITLE_ASC: Recipe.title.asc(),
        RecipeSort.TITLE_DESC: Recipe.title.desc(),
        RecipeSort.TIME_ASC: Recipe.total_time_minutes.asc(),
        RecipeSort.TIME_DESC: Recipe.total_time_minutes.desc(),
        RecipeSort.CALORIES_ASC:
            Recipe.calories_per_serving.asc(),
        RecipeSort.CALORIES_DESC:
            Recipe.calories_per_serving.desc(),
    }

    statement = (
        statement
        .order_by(
            sort_expressions[sort],
            Recipe.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(
        session.scalars(statement).unique().all()
    )


@router.get(
    "/{recipe_id}",
    response_model=RecipeRead,
)
def get_recipe(
    recipe_id: int,
    session: Session = Depends(get_database_session),
) -> Recipe:
    return get_recipe_or_404(recipe_id, session)


@router.post(
    "",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recipe(
    data: RecipeCreate,
    session: Session = Depends(get_database_session),
) -> Recipe:
    categories = get_categories_by_ids(
        data.category_ids,
        session,
    )

    ingredient_ids = [
        item.ingredient_id
        for item in data.ingredients_with_amounts
    ]

    ingredients = get_ingredients_by_ids(
        ingredient_ids,
        session,
    )

    recipe = Recipe()

    apply_recipe_data(
        recipe=recipe,
        data=data,
        categories=categories,
        ingredients=ingredients,
    )

    session.add(recipe)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось создать рецепт",
        )

    return get_recipe_or_404(recipe.id, session)


@router.put(
    "/{recipe_id}",
    response_model=RecipeRead,
)
def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    session: Session = Depends(get_database_session),
) -> Recipe:
    recipe = get_recipe_or_404(recipe_id, session)

    categories = get_categories_by_ids(
        data.category_ids,
        session,
    )

    ingredient_ids = [
        item.ingredient_id
        for item in data.ingredients_with_amounts
    ]

    ingredients = get_ingredients_by_ids(
        ingredient_ids,
        session,
    )

    apply_recipe_data(
        recipe=recipe,
        data=data,
        categories=categories,
        ingredients=ingredients,
    )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось изменить рецепт",
        )

    return get_recipe_or_404(recipe_id, session)

@router.post(
    "/{recipe_id}/image",
    response_model=RecipeRead,
)
async def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_database_session),
) -> Recipe:
    recipe = get_recipe_or_404(recipe_id, session)

    try:
        content = await file.read(
            MAX_IMAGE_FILE_SIZE + 1
        )
    finally:
        await file.close()

    try:
        new_image_path = save_recipe_image(
            content=content,
            recipe_id=recipe.id,
        )
    except ImageTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from error
    except ImageValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    old_image_path = recipe.image_path
    recipe.image_path = new_image_path

    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        delete_recipe_image(new_image_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить фотографию рецепта",
        ) from error

    # Старый файл удаляем только после успешного обновления базы.
    delete_recipe_image(old_image_path)

    return get_recipe_or_404(recipe_id, session)

@router.delete(
    "/{recipe_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_recipe_image(
    recipe_id: int,
    session: Session = Depends(get_database_session),
) -> Response:
    recipe = get_recipe_or_404(recipe_id, session)
    old_image_path = recipe.image_path

    if old_image_path is None:
        return Response(
            status_code=status.HTTP_204_NO_CONTENT
        )

    recipe.image_path = None

    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить фотографию рецепта",
        ) from error

    delete_recipe_image(old_image_path)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )

@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recipe(
    recipe_id: int,
    session: Session = Depends(get_database_session),
) -> Response:
    recipe = get_recipe_or_404(recipe_id, session)
    image_path = recipe.image_path

    session.delete(recipe)

    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить рецепт",
        ) from error

    delete_recipe_image(image_path)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/{recipe_id}/calculate",
    response_model=RecipeCalculationRead,
)
def calculate_recipe(
    recipe_id: int,
    servings: int = Query(gt=0, le=1000),
    session: Session = Depends(get_database_session),
) -> RecipeCalculationRead:
    recipe = get_recipe_or_404(recipe_id, session)

    coefficient = servings / recipe.base_servings

    ingredient_names = {
        ingredient.id: ingredient.name
        for ingredient in recipe.ingredients
    }

    calculated_ingredients: list[CalculatedIngredient] = []

    for item in recipe.ingredients_with_amounts:
        ingredient_id = item["ingredient_id"]
        original_amount = float(item["amount"])

        calculated_ingredients.append(
            CalculatedIngredient(
                ingredient_id=ingredient_id,
                name=ingredient_names.get(
                    ingredient_id,
                    "Неизвестный ингредиент",
                ),
                original_amount=original_amount,
                calculated_amount=round(
                    original_amount * coefficient,
                    3,
                ),
                unit=item["unit"],
            )
        )

    calories_per_serving = float(
        recipe.calories_per_serving
    )

    return RecipeCalculationRead(
        recipe_id=recipe.id,
        title=recipe.title,
        original_servings=recipe.base_servings,
        requested_servings=servings,
        calories_per_serving=calories_per_serving,
        total_calories=round(
            calories_per_serving * servings,
            2,
        ),
        ingredients=calculated_ingredients,
    )