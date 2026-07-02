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


def describe_device_status(device: dict) -> str:
    """Turn a raw device record into a plain-English summary."""
    name = device.get("name") or "The feeder"
    notes = []

    if device.get("online") is False:
        notes.append(
            f"{name} is offline — it isn't currently connected to Petlibro's cloud, "
            "even if it still responds to physical button presses. Try power-cycling "
            "it or checking its WiFi connection."
        )
    if device.get("errorState") or device.get("barnDoorError") or device.get("doorErrorState") not in (None, "NORMAL"):
        notes.append(f"{name} is reporting a hardware or door error.")
    if device.get("surplusGrain") is False:
        notes.append(f"{name} is out of food — refill the hopper.")
    if device.get("deviceStoppedWorking"):
        notes.append(f"{name} has stopped working.")
    exception_message = device.get("exceptionMessage")
    if exception_message:
        notes.append(f"Device reported: {exception_message}")
    if device.get("batteryState") == "low":
        notes.append(
            "Its backup battery is low — separate from AC power, shouldn't affect "
            "operation while plugged in, but worth replacing if you rely on it during outages."
        )

    if not notes:
        return f"{name} looks online and healthy."
    return " ".join(notes)


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

    def _invalidate_token(self):
        self._token = None
        self._token_expiry = 0

    async def list_devices(self) -> list:
        for attempt in range(2):
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{BASE_URL}/device/device/list",
                    json={},
                    headers=_headers(token),
                    timeout=15,
                )
            data = resp.json()
            if data.get("code") == 1009 and attempt == 0:
                self._invalidate_token()
                continue
            return _check(data).get("data") or []

    async def get_device(self, device_sn: str) -> Optional[dict]:
        for device in await self.list_devices():
            if device.get("deviceSn") == device_sn:
                return device
        return None

    async def feed(self, device_sn: str, portions: int = 1) -> None:
        for attempt in range(2):
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
            data = resp.json()
            if data.get("code") == 1009 and attempt == 0:
                self._invalidate_token()
                continue
            _check(data)
            return
