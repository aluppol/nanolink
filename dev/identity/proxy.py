import json
import os
import secrets
import time
from typing import Any

import httpx
import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from jwt.algorithms import RSAAlgorithm
from starlette.background import BackgroundTask

ISSUER = os.environ["DEV_ISSUER"]
UPSTREAM = os.environ.get("DEV_UPSTREAM", "http://web:8080")
AUDIENCE = "nanolink"
KEY_ID = f"nanolink-dev-{secrets.token_hex(6)}"
USER_COOKIE = "nanolink_dev_user"
TOKEN_HEADER = "x-forwarded-access-token"
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
    }
)
NOT_FORWARDED = HOP_BY_HOP | {TOKEN_HEADER}
DEV_USERS: dict[str, dict[str, Any]] = {
    "alice": {"sub": "0b7d4c1e-0000-4000-8000-00000000a11c", "roles": ["USER"], "email": "alice@example.org"},
    "bob": {"sub": "0b7d4c1e-0000-4000-8000-000000000b0b", "roles": ["USER"], "email": "bob@example.org"},
    "admin": {
        "sub": "0b7d4c1e-0000-4000-8000-00000000ad31",
        "roles": ["ADMIN"],
        "email": "admin@example.org",
    },
    "guest": {
        "sub": "0b7d4c1e-0000-4000-8000-00000000c0e5",
        "roles": ["guest"],
        "email": "guest@example.org",
    },
}
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
upstream = httpx.AsyncClient(base_url=UPSTREAM, timeout=httpx.Timeout(10.0, read=None))


def access_token(username: str) -> str:
    user, now = DEV_USERS[username], int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": [AUDIENCE],
        "azp": AUDIENCE,
        "typ": "Bearer",
        "sub": user["sub"],
        "preferred_username": username,
        "email": user["email"],
        "email_verified": True,
        "realm_access": {"roles": user["roles"]},
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": KEY_ID})


@app.get("/realms/dev/protocol/openid-connect/certs")
async def signing_keys() -> JSONResponse:
    public_key = json.loads(RSAAlgorithm.to_jwk(SIGNING_KEY.public_key()))
    return JSONResponse({"keys": [{**public_key, "kid": KEY_ID, "use": "sig", "alg": "RS256"}]})


@app.get("/__dev/login")
async def choose_user() -> HTMLResponse:
    links = "".join(
        f'<li><a href="/__dev/login/{name}">{name}</a> ({", ".join(user["roles"])})</li>'
        for name, user in DEV_USERS.items()
    )
    return HTMLResponse(
        f"<!doctype html><title>NanoLink dev sign-in</title><h1>Sign in as</h1><ul>{links}</ul>"
    )


@app.get("/__dev/login/{username}")
async def sign_in(username: str) -> Response:
    if username not in DEV_USERS:
        return RedirectResponse("/__dev/login", status_code=302)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(USER_COOKIE, username, httponly=True, samesite="lax")
    return response


@app.get("/oauth2/sign_out")
async def sign_out() -> Response:
    response = RedirectResponse("/__dev/login", status_code=302)
    response.delete_cookie(USER_COOKIE)
    return response


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE"])
async def forward(request: Request, path: str) -> Response:
    username = request.cookies.get(USER_COOKIE)
    if username not in DEV_USERS:
        return signed_out_answer(path)
    headers = {
        name.lower(): value for name, value in request.headers.items() if name.lower() not in NOT_FORWARDED
    }
    headers.setdefault("accept-encoding", "identity")
    headers[TOKEN_HEADER] = access_token(username)
    outgoing = upstream.build_request(
        request.method, f"/{path}", params=request.query_params, headers=headers, content=await request.body()
    )
    answer = await upstream.send(outgoing, stream=True)
    passed = {name: value for name, value in answer.headers.items() if name.lower() not in HOP_BY_HOP}
    return StreamingResponse(
        answer.aiter_raw(),
        status_code=answer.status_code,
        headers=passed,
        background=BackgroundTask(answer.aclose),
    )


def signed_out_answer(path: str) -> Response:
    if path.startswith("api/"):
        return JSONResponse({"error": "unauthenticated", "message": "sign in first"}, status_code=401)
    return RedirectResponse("/__dev/login", status_code=302)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning")
