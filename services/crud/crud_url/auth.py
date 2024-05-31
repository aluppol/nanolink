from fastapi import HTTPException, Security
from fastapi.security  import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.public_key = os.getenv("JWT_PUBLIC_KEY")
        self.algorithm = os.getenv("JWT_ALGORITHM")

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            token = credentials.credentials
            return 'test'
            # return self.decode_token(token)

    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
            return payload.get('id')
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token has expired")
        except jwt.PyJWTError:
            raise HTTPException(status_code=403, detail="Invalid token")
