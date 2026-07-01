import json
from typing import Any

import requests

from pathlib import Path

class APIClientError(Exception):
    pass


class APIClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        self.session.close()

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=(3, 20),
                **kwargs,
            )
        except requests.Timeout as error:
            raise APIClientError(
                "Сервер не ответил вовремя"
            ) from error
        except requests.ConnectionError as error:
            raise APIClientError(
                "Не удалось подключиться к серверу"
            ) from error
        except requests.RequestException as error:
            raise APIClientError(
                f"Ошибка запроса: {error}"
            ) from error

        if not response.ok:
            try:
                detail = response.json().get(
                    "detail",
                    response.text,
                )
            except ValueError:
                detail = response.text

            if isinstance(detail, (dict, list)):
                detail = json.dumps(
                    detail,
                    ensure_ascii=False,
                )

            raise APIClientError(
                f"Ошибка сервера {response.status_code}: {detail}"
            )

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise APIClientError(
                "Сервер вернул некорректный JSON"
            ) from error

    def check_database(self) -> dict:
        return self._request(
            "GET",
            "/health/database",
        )

    def get_categories(self) -> list[dict]:
        return self._request(
            "GET",
            "/api/v1/categories",
        )

    def get_ingredients(self) -> list[dict]:
        return self._request(
            "GET",
            "/api/v1/ingredients",
        )

    def get_recipe(self, recipe_id: int) -> dict:
        return self._request(
            "GET",
            f"/api/v1/recipes/{recipe_id}",
        )
    
    def calculate_recipe(
        self,
        recipe_id: int,
        servings: int,
    ) -> dict:
        return self._request(
            "GET",
            f"/api/v1/recipes/{recipe_id}/calculate",
            params={"servings": servings},
        )

    def download_image(
        self,
        image_path: str,
    ) -> bytes:
        image_url = self.get_media_url(image_path)

        if image_url is None:
            raise APIClientError(
                "У рецепта отсутствует фотография"
            )

        try:
            response = self.session.get(
                image_url,
                timeout=(3, 20),
            )
        except requests.Timeout as error:
            raise APIClientError(
                "Не удалось загрузить фотографию вовремя"
            ) from error
        except requests.RequestException as error:
            raise APIClientError(
                "Не удалось загрузить фотографию"
            ) from error

        if not response.ok:
            raise APIClientError(
                f"Фотография недоступна: {response.status_code}"
            )

        return response.content

    def get_recipes(
        self,
        *,
        query: str | None = None,
        ingredient_query: str | None = None,
        category_ids: list[int] | None = None,
        ingredient_ids: list[int] | None = None,
        excluded_ingredient_ids: list[int] | None = None,
        ingredient_match: str = "all",
        exclude_common_allergens: bool = False,
        max_time_minutes: int | None = None,
        max_calories: float | None = None,
        sort: str = "title_asc",
    ) -> list[dict]:
        params: list[tuple[str, str | int | float]] = []

        if query:
            params.append(("query", query))

        if ingredient_query:
            params.append(
                ("ingredient_query", ingredient_query)
            )

        for category_id in category_ids or []:
            params.append(
                ("category_ids", category_id)
            )

        for ingredient_id in ingredient_ids or []:
            params.append(
                ("ingredient_ids", ingredient_id)
            )

        if ingredient_ids:
            params.append(
                ("ingredient_match", ingredient_match)
            )

        for ingredient_id in excluded_ingredient_ids or []:
            params.append(
                ("excluded_ingredient_ids", ingredient_id)
            )

        if exclude_common_allergens:
            params.append(
                ("exclude_common_allergens", "true")
            )

        if max_time_minutes is not None:
            params.append(
                ("max_time_minutes", max_time_minutes)
            )

        if max_calories is not None:
            params.append(
                ("max_calories", max_calories)
            )

        params.append(("sort", sort))
        params.append(("limit", 100))

        return self._request(
            "GET",
            "/api/v1/recipes",
            params=params,
        )

    def get_media_url(
        self,
        image_path: str | None,
    ) -> str | None:
        if not image_path:
            return None

        return f"{self.base_url}{image_path}"

    def create_category(
        self,
        name: str,
    ) -> dict:
        return self._request(
            "POST",
            "/api/v1/categories",
            json={"name": name},
        )

    def update_category(
        self,
        category_id: int,
        name: str,
    ) -> dict:
        return self._request(
            "PUT",
            f"/api/v1/categories/{category_id}",
            json={"name": name},
        )

    def delete_category(
        self,
        category_id: int,
    ) -> None:
        self._request(
            "DELETE",
            f"/api/v1/categories/{category_id}",
        )

    def create_ingredient(
        self,
        name: str,
        is_common_allergen: bool,
    ) -> dict:
        return self._request(
            "POST",
            "/api/v1/ingredients",
            json={
                "name": name,
                "is_common_allergen": is_common_allergen,
            },
        )

    def update_ingredient(
        self,
        ingredient_id: int,
        name: str,
        is_common_allergen: bool,
    ) -> dict:
        return self._request(
            "PUT",
            f"/api/v1/ingredients/{ingredient_id}",
            json={
                "name": name,
                "is_common_allergen": is_common_allergen,
            },
        )

    def delete_ingredient(
        self,
        ingredient_id: int,
    ) -> None:
        self._request(
            "DELETE",
            f"/api/v1/ingredients/{ingredient_id}",
        )

    def create_recipe(
        self,
        recipe_data: dict,
    ) -> dict:
        return self._request(
            "POST",
            "/api/v1/recipes",
            json=recipe_data,
        )

    def update_recipe(
        self,
        recipe_id: int,
        recipe_data: dict,
    ) -> dict:
        return self._request(
            "PUT",
            f"/api/v1/recipes/{recipe_id}",
            json=recipe_data,
        )

    def delete_recipe(
        self,
        recipe_id: int,
    ) -> None:
        self._request(
            "DELETE",
            f"/api/v1/recipes/{recipe_id}",
        )

    def upload_recipe_image(
        self,
        recipe_id: int,
        image_path: str,
    ) -> dict:
        path = Path(image_path)

        with path.open("rb") as image_file:
            return self._request(
                "POST",
                f"/api/v1/recipes/{recipe_id}/image",
                files={
                    "file": (
                        path.name,
                        image_file,
                        "image/jpeg",
                    )
                },
            )

    def delete_recipe_image(
        self,
        recipe_id: int,
    ) -> None:
        self._request(
            "DELETE",
            f"/api/v1/recipes/{recipe_id}/image",
        )    