from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngredientCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=150,
    )

    is_common_allergen: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(value.split())

        if not value:
            raise ValueError("Название ингредиента не может быть пустым")

        return value


class IngredientUpdate(IngredientCreate):
    pass


class IngredientRead(BaseModel):
    id: int
    name: str
    is_common_allergen: bool

    model_config = ConfigDict(from_attributes=True)