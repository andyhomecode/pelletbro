import hmac
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from petlibro import PetlibroClient

PETLIBRO_EMAIL = os.environ["PETLIBRO_EMAIL"]
PETLIBRO_PASSWORD = os.environ["PETLIBRO_PASSWORD"]
PETLIBRO_DEVICE_SN = os.environ.get("PETLIBRO_DEVICE_SN")
API_KEY = os.environ.get("API_KEY")

client: PetlibroClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = PetlibroClient(PETLIBRO_EMAIL, PETLIBRO_PASSWORD)
    yield


app = FastAPI(title="Pelletbro", lifespan=lifespan, docs_url=None, redoc_url=None)
bearer = HTTPBearer(auto_error=False)


def require_api_key(
    creds: Optional[HTTPAuthorizationCredentials] = Security(bearer),
    key: Optional[str] = Query(default=None, alias="api_key"),
):
    if not API_KEY:
        return  # no key configured → open access (fine on a private network)
    provided = (creds.credentials if creds else None) or key
    if not provided or not hmac.compare_digest(provided, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/feed", dependencies=[Depends(require_api_key)])
async def feed(portions: int = Query(default=1, ge=1, le=10), device_sn: Optional[str] = Query(default=None)):
    sn = device_sn or PETLIBRO_DEVICE_SN
    if not sn:
        raise HTTPException(status_code=400, detail="No device_sn provided and PETLIBRO_DEVICE_SN not set")
    try:
        await client.feed(sn, portions)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "device_sn": sn, "portions": portions}


@app.get("/devices", dependencies=[Depends(require_api_key)])
async def devices():
    try:
        return await client.list_devices()
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
async def health():
    return {"ok": True}
