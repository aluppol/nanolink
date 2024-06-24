from fastapi import FastAPI
from services.database import database_service
from services.http_service import http_service
from controllers.url_controller import url_router
from exception_handlers import general_exception_handler, db_connection_failure_handler
from pymongo.errors import ConnectionFailure

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    # Initialize the database connection on startup
    await database_service.connect()
    # Initialize the HTTP service session on startup
    await http_service.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # Close the database connection on shutdown
    await database_service.disconnect()
    # Close the HTTP service session on shutdown
    await http_service.disconnect()

app.include_router(url_router)

app.add_exception_handler(ConnectionFailure, db_connection_failure_handler)
app.add_exception_handler(Exception, general_exception_handler)

