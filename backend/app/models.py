

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# Таблица 4: связь рецептов и категорий.
recipe_categories = Table(
    "recipe_categories",
    Base.metadata,
    Column(
        "recipe_id",
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index(
        "ix_recipe_categories_category_id",
        "category_id",
    ),
)


# Таблица 5: связь рецептов и ингредиентов.
# Количество и единицы здесь не хранятся.
recipe_ingredients = Table(
    "recipe_ingredients",
    Base.metadata,
    Column(
        "recipe_id",
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "ingredient_id",
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Index(
        "ix_recipe_ingredients_ingredient_id",
        "ingredient_id",
    ),
)


# Таблица 1: основные данные рецептов.
class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Количество порций, на которое записан рецепт.
    base_servings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    total_time_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Калорийность одной порции.
    calories_per_serving: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    # Список ингредиентов с количеством.
    # Пример:
    # [
    #     {"ingredient_id": 1, "amount": 500, "unit": "г"},
    #     {"ingredient_id": 2, "amount": 2, "unit": "ст. л."}
    # ]
    ingredients_with_amounts: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    # Пошаговое приготовление.
    # Пример:
    # [
    #     {"number": 1, "description": "Нарезать овощи"},
    #     {"number": 2, "description": "Варить 20 минут"}
    # ]
    cooking_steps: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    categories: Mapped[list["Category"]] = relationship(
        secondary=recipe_categories,
        back_populates="recipes",
        passive_deletes=True,
    )

    ingredients: Mapped[list["Ingredient"]] = relationship(
        secondary=recipe_ingredients,
        back_populates="recipes",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "base_servings > 0",
            name="ck_recipes_base_servings_positive",
        ),
        CheckConstraint(
            "total_time_minutes > 0",
            name="ck_recipes_total_time_positive",
        ),
        CheckConstraint(
            "calories_per_serving >= 0",
            name="ck_recipes_calories_not_negative",
        ),
        CheckConstraint(
            "jsonb_typeof(ingredients_with_amounts) = 'array'",
            name="ck_recipes_ingredients_is_array",
        ),
        CheckConstraint(
            "jsonb_typeof(cooking_steps) = 'array'",
            name="ck_recipes_steps_is_array",
        ),
    )


# Таблица 2: категории.
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    recipes: Mapped[list["Recipe"]] = relationship(
        secondary=recipe_categories,
        back_populates="categories",
        passive_deletes=True,
    )


# Таблица 3: ингредиенты.
class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    # Пометка распространённых аллергенов.
    # Исключать при поиске можно будет любой ингредиент.
    is_common_allergen: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    recipes: Mapped[list["Recipe"]] = relationship(
        secondary=recipe_ingredients,
        back_populates="ingredients",
        passive_deletes=True,
    )