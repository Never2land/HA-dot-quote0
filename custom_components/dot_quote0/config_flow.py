from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DotApi, DotAuthError, DotConnectionError
from .const import CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class DotQuote0ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Dot. Quote/0."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]

            # Prevent duplicate entries for the same API key
            await self.async_set_unique_id(api_key[:16])
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = DotApi(session, api_key)

            try:
                devices = await api.get_devices()
            except DotAuthError:
                errors["base"] = "invalid_auth"
            except DotConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    return self.async_create_entry(
                        title=f"Dot. ({len(devices)} device{'s' if len(devices) > 1 else ''})",
                        data={CONF_API_KEY: api_key},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
