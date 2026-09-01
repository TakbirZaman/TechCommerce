from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import CommerceError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(CommerceError)
    async def commerce_error_handler(request: Request, exc: CommerceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
