"""Diagnostics support for FASTGate Presence."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN, classify_network_type


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry. Never includes sensitive data."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    monitored_macs = coordinator.get_monitored_macs()
    device_names = coordinator.get_device_names()
    all_devices = coordinator.all_devices

    monitored_details: list[dict[str, Any]] = []
    for mac in monitored_macs:
        device = all_devices.get(mac.upper())
        detail: dict[str, Any] = {
            "mac": mac,
            "friendly_name": device_names.get(mac, mac),
            "connected": device is not None,
        }
        if device:
            detail["hostname"] = device.Name
            detail["ip"] = device.IP
            network_raw = device.additionalInfo.get("Network", "")
            detail["network"] = network_raw or "unknown"
            detail["network_type"] = classify_network_type(network_raw)
        monitored_details.append(detail)

    last_update = coordinator.last_successful_update

    return {
        "router": {
            "host": entry.data.get(CONF_HOST),
            "username": entry.data.get(CONF_USERNAME),
            # password intentionally omitted
            "available": coordinator.router_available,
        },
        "last_update_success": coordinator.last_update_success,
        "last_update_time": last_update.isoformat() if last_update is not None else None,
        "total_connected_devices": len(all_devices),
        "monitored_devices_count": len(monitored_macs),
        "monitored_devices": monitored_details,
        "all_connected_macs": sorted(all_devices.keys()),
    }
