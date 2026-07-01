from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_database_session


app = FastAPI(
    title="Книга рецептов API",
    version="0.2.0",
)

app.mount(
    "/media",
    StaticFiles(directory="media"),
    name="media",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database")
def database_health_check(
    session: Session = Depends(get_database_session),
) -> dict[str, str]:
    session.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }; from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_database_session
from backend.app.routers import categories, ingredients, recipes


app = FastAPI(
    title="Книга рецептов API",
    version="0.4.0",
)

app.mount(
    "/media",
    StaticFiles(directory="media"),
    name="media",
)

app.include_router(
    categories.router,
    prefix="/api/v1",
)

app.include_router(
    ingredients.router,
    prefix="/api/v1",
)

app.include_router(
    recipes.router,
    prefix="/api/v1",
)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database")
def database_health_check(
    session: Session = Depends(get_database_session),
) -> dict[str, str]:
    session.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }