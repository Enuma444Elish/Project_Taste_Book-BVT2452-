from decimal import Decimal
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.app.schemas.category import CategoryRead
from backend.app.schemas.ingredient import IngredientRead


class IngredientAmount(BaseModel):
    ingredient_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        value = " ".join(value.split())

        if not value:
            raise ValueError("Единица измерения не может быть пустой")

        return value


class CookingStep(BaseModel):
    number: int = Field(gt=0)
    description: str = Field(min_length=1)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Описание этапа не может быть пустым")

        return value


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None

    base_servings: int = Field(gt=0)
    total_time_minutes: int = Field(gt=0)
    calories_per_serving: Decimal = Field(ge=0)

    category_ids: list[int] = Field(min_length=1)

    ingredients_with_amounts: list[IngredientAmount] = Field(
        min_length=1
    )

    cooking_steps: list[CookingStep] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = " ".join(value.split())

        if not value:
            raise ValueError("Название рецепта не может быть пустым")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_recipe_structure(self) -> Self:
        if len(self.category_ids) != len(set(self.category_ids)):
            raise ValueError("Категории рецепта не должны повторяться")

        ingredient_ids = [
            item.ingredient_id
            for item in self.ingredients_with_amounts
        ]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValueError("Ингредиенты рецепта не должны повторяться")

        step_numbers = [
            step.number
            for step in self.cooking_steps
        ]

        expected_numbers = list(
            range(1, len(self.cooking_steps) + 1)
        )

        if step_numbers != expected_numbers:
            raise ValueError(
                "Этапы должны идти последовательно: 1, 2, 3 и так далее"
            )

        return self


class RecipeUpdate(RecipeCreate):
    pass


class RecipeRead(BaseModel):
    id: int
    title: str
    description: str | None
    image_path: str | None

    base_servings: int
    total_time_minutes: int
    calories_per_serving: Decimal

    ingredients_with_amounts: list[IngredientAmount]
    cooking_steps: list[CookingStep]

    categories: list[CategoryRead]
    ingredients: list[IngredientRead]

    model_config = ConfigDict(from_attributes=True)


class CalculatedIngredient(BaseModel):
    ingredient_id: int
    name: str
    original_amount: float
    calculated_amount: float
    unit: str


class RecipeCalculationRead(BaseModel):
    recipe_id: int
    title: str

    original_servings: int
    requested_servings: int

    calories_per_serving: float
    total_calories: float

    ingredients: list[CalculatedIngredient]