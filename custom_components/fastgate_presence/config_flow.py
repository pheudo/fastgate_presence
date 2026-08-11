"""Config Flow for FASTGate Presence."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from routerscraper.dataTypes import loginResult
from routerscraper.fastgate_dn8245f2 import fastgate_dn8245f2

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_DEVICE_NAMES,
    CONF_MONITORED_DEVICES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    normalize_mac,
)

_LOGGER = logging.getLogger(__name__)


def _parse_device_names(raw_names: str) -> dict[str, str]:
    """Parse MAC=name lines into a normalised mapping."""
    names: dict[str, str] = {}
    for line in raw_names.splitlines():
        if "=" not in line:
            continue
        mac, friendly = line.split("=", 1)
        mac_key = normalize_mac(mac)
        friendly_name = friendly.strip()
        if mac_key and friendly_name:
            names[mac_key] = friendly_name
    return names


def _normalise_mac_list(macs: list[str]) -> list[str]:
    """Return unique, uppercased MACs preserving order."""
    return list(dict.fromkeys(normalize_mac(mac) for mac in macs if mac.strip()))


def _merge_monitored_macs(selected_macs: list[str], custom_names: dict[str, str]) -> list[str]:
    """Keep explicit selections and add any MACs that were named manually."""
    return list(dict.fromkeys(selected_macs + list(custom_names)))


def _try_login(host: str, username: str, password: str) -> loginResult:
    """Attempt router login synchronously (runs in executor)."""
    scraper = fastgate_dn8245f2(host=host, user=username, password=password)
    return scraper.login(cleanStart=True)


class FastgatePresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FASTGate Presence."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise config flow."""
        self._host: str = ""
        self._username: str = ""
        self._password: str = ""
        self._scan_interval: int = DEFAULT_SCAN_INTERVAL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._username = user_input[CONF_USERNAME].strip()
            self._password = user_input[CONF_PASSWORD]
            self._scan_interval = user_input[CONF_SCAN_INTERVAL]

            await self.async_set_unique_id(self._host)
            self._abort_if_unique_id_configured()

            try:
                login_result: loginResult = await self.hass.async_add_executor_job(
                    _try_login, self._host, self._username, self._password
                )
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                if login_result == loginResult.Success:
                    # Credentials -> entry.data  |  user preferences -> entry.options
                    return self.async_create_entry(
                        title=f"FASTGate ({self._host})",
                        data={
                            CONF_HOST: self._host,
                            CONF_USERNAME: self._username,
                            CONF_PASSWORD: self._password,
                        },
                        options={
                            CONF_SCAN_INTERVAL: self._scan_interval,
                            CONF_MONITORED_DEVICES: [],
                            CONF_DEVICE_NAMES: {},
                        },
                    )
                elif login_result in (loginResult.WrongUser, loginResult.WrongPass):
                    errors["base"] = "invalid_auth"
                elif login_result == loginResult.Locked:
                    errors["base"] = "login_locked"
                else:
                    errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host or "192.168.1.254"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="url")
                ),
                vol.Required(CONF_USERNAME, default=self._username or "admin"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="username")
                ),
                # Password: masked input, no default value pre-populated
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=self._scan_interval
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return FastgatePresenceOptionsFlow()


class FastgatePresenceOptionsFlow(OptionsFlow):
    """Handle options for FASTGate Presence."""

    def __init__(self) -> None:
        """Initialise options flow."""
        # Initialised here so async_step_select_devices never hits AttributeError
        # even if the frontend somehow skips async_step_init.
        self._new_scan_interval: int = DEFAULT_SCAN_INTERVAL

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: adjust polling interval."""
        if user_input is not None:
            self._new_scan_interval = user_input[CONF_SCAN_INTERVAL]
            return await self.async_step_select_devices()

        current_interval: int = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: choose which devices to monitor and assign friendly names."""
        errors: dict[str, str] = {}

        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        if coordinator is None:
            errors["base"] = "coordinator_unavailable"
            return self.async_show_form(
                step_id="select_devices",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        # Use the coordinator's public method to avoid competing login sessions
        try:
            fresh_devices = await coordinator.async_fetch_current_devices()
        except Exception:
            _LOGGER.debug("Options flow: could not fetch device list", exc_info=True)
            errors["base"] = "cannot_connect"
            fresh_devices = []

        current_monitored: list[str] = self.config_entry.options.get(
            CONF_MONITORED_DEVICES, []
        )
        current_names: dict[str, str] = self.config_entry.options.get(
            CONF_DEVICE_NAMES, {}
        )
        current_monitored = _normalise_mac_list(current_monitored)
        current_names = {
            normalize_mac(mac): name
            for mac, name in current_names.items()
            if mac.strip()
        }

        # Build selector options from currently connected devices
        device_options: dict[str, str] = {}
        for dev in fresh_devices:
            mac = normalize_mac(dev.MAC)
            label = f"{dev.Name} ({mac}) - {dev.IP}"
            device_options[mac] = label

        # Preserve offline monitored devices in the list so they are not lost
        for mac in current_monitored:
            if mac not in device_options:
                name = current_names.get(mac, mac)
                device_options[mac] = f"{name} ({mac}) - [offline]"

        if user_input is not None:
            selected_macs: list[str] = _normalise_mac_list(
                user_input.get(CONF_MONITORED_DEVICES, [])
            )
            raw_names: str = user_input.get(CONF_DEVICE_NAMES, "")
            new_names: dict[str, str] = _parse_device_names(raw_names)
            
            # Auto-populate friendly names for selected devices without explicit names
            for mac in selected_macs:
                if mac not in new_names:
                    # Try to use the hostname from fresh_devices as fallback
                    for dev in fresh_devices:
                        if normalize_mac(dev.MAC) == mac:
                            new_names[mac] = dev.Name
                            break
            
            selected_macs = _merge_monitored_macs(selected_macs, new_names)

            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: self._new_scan_interval,
                    CONF_MONITORED_DEVICES: selected_macs,
                    CONF_DEVICE_NAMES: new_names,
                },
            )

        name_hint = "\n".join(
            f"{mac}={current_names.get(mac, '')}" for mac in current_monitored
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITORED_DEVICES, default=current_monitored
                ): selector.selector(
                    {
                        "select": {
                            "options": [
                                {"value": mac, "label": label}
                                for mac, label in device_options.items()
                            ],
                            "multiple": True,
                            "mode": "list",
                        }
                    }
                ),
                vol.Optional(
                    CONF_DEVICE_NAMES, default=name_hint
                ): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="select_devices",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "name_format": "AA:BB:CC:DD:EE:FF=Primary phone\n11:22:33:44:55:66=Studio laptop"
            },
        )
