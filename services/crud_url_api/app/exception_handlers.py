from fastapi import Request
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure


async def db_connection_failure_handler(request: Request, exc: ConnectionFailure) -> JSONResponse:
    print(f"Database connection error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"message": "A database error occurred, please try again later"}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    print(f"Unhandled exception: {exc} - Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"message": "An issue occurred, and we are looking into it."}
    )
