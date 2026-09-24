import uvicorn
from fastapi import FastAPI

GRACEFUL_SHUTDOWN_SECONDS = 5


def serve_http(app: FastAPI, port: int, log_level: str) -> None:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=log_level.lower(),
        loop="uvloop",
        http="httptools",
        proxy_headers=False,
        server_header=False,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
    )
