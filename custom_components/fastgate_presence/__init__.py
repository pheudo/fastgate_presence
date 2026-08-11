"""FASTGate Presence - Custom Integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_MONITORED_DEVICES, DOMAIN, normalize_mac
from .coordinator import FastgatePresenceCoordinator
from .device_tracker import tracker_unique_id

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FASTGate Presence from a config entry."""
    coordinator = FastgatePresenceCoordinator(hass, entry)

    # Raises ConfigEntryNotReady automatically on failure; no redundant check needed.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    coordinator: FastgatePresenceCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is not None:
        previous_macs = set(coordinator.get_monitored_macs())
        current_macs = {
            normalize_mac(mac)
            for mac in entry.options.get(CONF_MONITORED_DEVICES, [])
            if mac.strip()
        }
        removed_macs = previous_macs - current_macs
        if removed_macs:
            removed_unique_ids = {tracker_unique_id(mac) for mac in removed_macs}
            removed_identifiers = {(DOMAIN, mac) for mac in removed_macs}
            entity_reg = er.async_get(hass)
            device_reg = dr.async_get(hass)
            for entity_entry in er.async_entries_for_config_entry(entity_reg, entry.entry_id):
                if entity_entry.domain == Platform.DEVICE_TRACKER and entity_entry.unique_id in removed_unique_ids:
                    entity_reg.async_remove(entity_entry.entity_id)
            for device_entry in dr.async_entries_for_config_entry(
                device_reg, entry.entry_id
            ):
                if device_entry.identifiers & removed_identifiers:
                    device_reg.async_remove_device(device_entry.id)
    await hass.config_entries.async_reload(entry.entry_id)
