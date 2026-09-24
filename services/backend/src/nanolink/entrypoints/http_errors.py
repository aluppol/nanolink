import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from httpx import HTTPError
from nats.errors import Error as NatsError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError
from starlette.exceptions import HTTPException

from nanolink.domain.errors import (
    DependencyUnavailable,
    DuplicateLongUrl,
    InvalidLongUrl,
    LinkNotFound,
    NanolinkError,
    NotAuthenticated,
    NotAuthorized,
    QuotaExceeded,
    TaskNotFound,
)
from nanolink.entrypoints.http_views import ErrorView

logger = logging.getLogger(__name__)

DOMAIN_ERRORS: Mapping[type, tuple[int, str, str]] = {
    InvalidLongUrl: (422, "invalid_long_url", "the URL cannot be shortened"),
    DuplicateLongUrl: (409, "duplicate_long_url", "you already have an active link to this URL"),
    LinkNotFound: (404, "not_found", "there is no such link"),
    TaskNotFound: (404, "not_found", "there is no such task"),
    QuotaExceeded: (429, "quota_exceeded", "your daily link quota is used up; try again tomorrow"),
    NotAuthenticated: (401, "unauthenticated", "your session is missing or has expired; sign in again"),
    NotAuthorized: (403, "forbidden", "your account is not allowed to do this"),
    DependencyUnavailable: (503, "unavailable", "a backing service is unavailable; try again shortly"),
}
INFRASTRUCTURE_ERRORS = (PyMongoError, NatsError, RedisError, HTTPError)
HTTP_ERROR_CODES: Mapping[int, str] = {404: "not_found", 405: "method_not_allowed"}


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NanolinkError, _domain_error)
    app.add_exception_handler(RequestValidationError, _invalid_request)
    app.add_exception_handler(HTTPException, _http_error)
    for error_type in INFRASTRUCTURE_ERRORS:
        app.add_exception_handler(error_type, _infrastructure_error)
    app.add_exception_handler(Exception, _unexpected_error)


def error_response(status: int, error: str, message: str) -> JSONResponse:
    headers = {"WWW-Authenticate": 'Bearer realm="nanolink"'} if status == 401 else None
    return JSONResponse(
        ErrorView(error=error, message=message).model_dump(), status_code=status, headers=headers
    )


async def _domain_error(request: Request, error: Exception) -> JSONResponse:
    mapping = _mapping_for(error)
    if mapping is None:
        return await _unexpected_error(request, error)
    status, code, message = mapping
    if isinstance(error, InvalidLongUrl):
        message = error.reason
    return error_response(status, code, message)


async def _invalid_request(_request: Request, _error: Exception) -> JSONResponse:
    return error_response(422, "invalid_request", "the request is malformed")


async def _http_error(_request: Request, error: Exception) -> JSONResponse:
    status = error.status_code if isinstance(error, HTTPException) else 500
    detail = error.detail if isinstance(error, HTTPException) else "error"
    return error_response(status, HTTP_ERROR_CODES.get(status, "http_error"), str(detail))


async def _infrastructure_error(request: Request, error: Exception) -> JSONResponse:
    logger.warning("backing service failed on %s %s: %r", request.method, request.url.path, error)
    status, code, message = DOMAIN_ERRORS[DependencyUnavailable]
    return error_response(status, code, message)


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("unexpected error on %s %s", request.method, request.url.path, exc_info=error)
    return error_response(500, "internal", "something went wrong on our side")


def _mapping_for(error: Exception) -> tuple[int, str, str] | None:
    return next((DOMAIN_ERRORS[kind] for kind in type(error).__mro__ if kind in DOMAIN_ERRORS), None)
