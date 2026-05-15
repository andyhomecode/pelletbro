import time
import uuid
from hashlib import md5
from typing import Optional

import httpx

BASE_URL = "https://api.us.petlibro.com"
APP_ID = 1
APP_SN = "c35772530d1041699c87fe62348507a8"


def _headers(token: Optional[str] = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "source": "ANDROID",
        "language": "EN",
        "timezone": "America/New_York",
        "version": "1.3.45",
    }
    if token:
        h["token"] = token
    return h


def _check(data: dict) -> dict:
    if data.get("code") != 0:
        raise RuntimeError(f"Petlibro API error {data.get('code')}: {data.get('msg')}")
    return data


class PetlibroClient:
    def __init__(self, email: str, password: str):
        self._email = email
        self._password_hash = md5(password.encode("utf-8")).hexdigest()
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    async def _login(self) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/member/auth/login",
                json={
                    "appId": APP_ID,
                    "appSn": APP_SN,
                    "country": "US",
                    "email": self._email,
                    "password": self._password_hash,
                    "phoneBrand": "",
                    "phoneSystemVersion": "",
                    "timezone": "America/New_York",
                    "thirdId": None,
                    "type": None,
                },
                headers=_headers(),
                timeout=15,
            )
        data = _check(resp.json())
        token = data["data"]["token"]
        expires_in = data["data"].get("expiresIn", 86400)
        self._token = token
        # refresh 5 minutes before expiry
        self._token_expiry = time.time() + expires_in - 300
        return token

    async def _get_token(self) -> str:
        if not self._token or time.time() >= self._token_expiry:
            await self._login()
        return self._token

    async def list_devices(self) -> list:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/device/device/list",
                json={},
                headers=_headers(token),
                timeout=15,
            )
        data = _check(resp.json())
        return data.get("data") or []

    async def feed(self, device_sn: str, portions: int = 1) -> None:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/device/device/manualFeeding",
                json={
                    "deviceSn": device_sn,
                    "grainNum": portions,
                    "requestId": uuid.uuid4().hex,
                },
                headers=_headers(token),
                timeout=20,
            )
        # some firmware returns bare 0 instead of a JSON object
        raw = resp.text.strip()
        if raw == "0":
            return
        _check(resp.json())
