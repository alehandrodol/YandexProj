from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from db.main import Base, engine
from api.routes import routes

tags_metadata = [
    {
        "name": "main tasks",
        "description": "Classic operations like add/update, delete, show",
    },
    {
        "name": "additional tasks",
        "description": "Information about updates",
    },
]

Base.metadata.create_all(bind=engine)  # Создание всех таблиц, если таблица уже существует, она не обновится, нужен drop
app = FastAPI(openapi_tags=tags_metadata)  # Инициализация приложения
app.include_router(routes)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Сustom validation exception."""
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": "Validation Failed"}
    )


def custom_openapi():
    """Функция для редактирования openapi схемы"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title="MegaMarketApi",
                                 version="1.0",
                                 routes=app.routes)

    # look for the error 422 and removes it
    for method in openapi_schema["paths"]:
        try:
            del openapi_schema["paths"][method]["post"]["responses"]["422"]
        except KeyError:
            pass

        try:
            del openapi_schema["paths"][method]["delete"]["responses"]["422"]
        except KeyError:
            pass

        try:
            del openapi_schema["paths"][method]["get"]["responses"]["422"]
        except KeyError:
            pass

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # Применения новой openapi схемы


