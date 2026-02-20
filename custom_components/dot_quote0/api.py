from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class DotApiError(Exception):
    """Base exception for Dot API errors."""


class DotAuthError(DotApiError):
    """Authentication error."""


class DotConnectionError(DotApiError):
    """Connection error."""


class DotApi:
    """Async client for the Dot. MindReset cloud API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, json=json
            ) as resp:
                if resp.status == 401:
                    raise DotAuthError("Invalid or expired API key")
                if resp.status == 403:
                    raise DotApiError("Forbidden: no permission for this device")
                if resp.status == 404:
                    raise DotApiError("Device or resource not found")
                if resp.status >= 500:
                    raise DotApiError(f"Server error: {resp.status}")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise DotConnectionError(f"Connection error: {err}") from err

    async def get_devices(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/authV2/open/devices")

    async def get_device_status(self, device_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/api/authV2/open/device/{device_id}/status"
        )

    async def switch_next_content(self, device_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/api/authV2/open/device/{device_id}/next"
        )

    async def list_device_tasks(
        self, device_id: str, task_type: str = "loop"
    ) -> list[dict[str, Any]]:
        return await self._request(
            "GET", f"/api/authV2/open/device/{device_id}/{task_type}/list"
        )

    async def send_text(
        self, device_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key in (
            "refreshNow", "title", "message", "signature", "icon", "link", "taskKey"
        ):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return await self._request(
            "POST", f"/api/authV2/open/device/{device_id}/text", json=payload
        )

    async def send_image(
        self, device_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key in (
            "refreshNow", "image", "link", "border",
            "ditherType", "ditherKernel", "taskKey",
        ):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return await self._request(
            "POST", f"/api/authV2/open/device/{device_id}/image", json=payload
        )
