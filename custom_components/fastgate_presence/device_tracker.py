"""Device Tracker platform for FASTGate Presence."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import (
    ScannerEntity,
    SourceType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_HOSTNAME,
    ATTR_IP,
    ATTR_MAC,
    ATTR_NETWORK_TYPE,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    NETWORK_TYPE_LAN,
    NETWORK_TYPE_WIFI,
    ROUTER_MODEL,
    normalize_mac,
)
from .coordinator import FastgatePresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker entities from config entry."""
    coordinator: FastgatePresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Register the router itself as a parent device so that the via_device
    # reference on each tracker resolves correctly in the device registry.
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"FASTGate Router ({coordinator._host})",
        manufacturer=MANUFACTURER,
        model=ROUTER_MODEL,
    )

    monitored_macs = coordinator.get_monitored_macs()
    device_names = coordinator.get_device_names()

    entities: list[FastgateDeviceTracker] = []
    for mac in monitored_macs:
        mac_upper = normalize_mac(mac)
        friendly_name = device_names.get(mac_upper)
        device_data = coordinator.all_devices.get(mac_upper)
        hostname = device_data.Name if device_data else mac_upper
        name = friendly_name or hostname

        entities.append(
            FastgateDeviceTracker(
                coordinator=coordinator,
                mac=mac_upper,
                name=name,
            )
        )

    if entities:
        async_add_entities(entities)
        _LOGGER.debug(
            "Added %d device tracker(s): %s",
            len(entities),
            [e.unique_id for e in entities],
        )


class FastgateDeviceTracker(CoordinatorEntity[FastgatePresenceCoordinator], ScannerEntity):
    """Represent a device tracked via the FASTGate router."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: FastgatePresenceCoordinator,
        mac: str,
        name: str,
    ) -> None:
        """Initialise the device tracker."""
        super().__init__(coordinator)
        self._mac = normalize_mac(mac)
        self._friendly_name = name
        self._attr_unique_id = f"{DOMAIN}_{self._mac.replace(':', '_')}"
        self._attr_name = name

    # ------------------------------------------------------------------
    # ScannerEntity required properties
    # ------------------------------------------------------------------

    @property
    def source_type(self) -> SourceType:
        """Return the source type (router)."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return True when the device MAC is present in the router client list."""
        # Use all_devices (never None) rather than coordinator.data directly.
        return self._mac in self.coordinator.all_devices

    @property
    def mac_address(self) -> str:
        """Return the MAC address of the tracked device."""
        return self._mac

    @property
    def hostname(self) -> str | None:
        """Return the hostname reported by the router."""
        device = self.coordinator.all_devices.get(self._mac)
        return device.Name if device else None

    @property
    def ip_address(self) -> str | None:
        """Return the current IP address of the device."""
        device = self.coordinator.all_devices.get(self._mac)
        return device.IP if device else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device = self.coordinator.all_devices.get(self._mac)
        attrs: dict[str, Any] = {ATTR_MAC: self._mac}
        if device:
            attrs[ATTR_HOSTNAME] = device.Name
            attrs[ATTR_IP] = device.IP
            network_raw: str = device.additionalInfo.get("Network", "")
            if network_raw:
                attrs[ATTR_NETWORK_TYPE] = (
                    NETWORK_TYPE_WIFI if "wifi" in network_raw.lower() else NETWORK_TYPE_LAN
                )
        return attrs

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return device info for the tracked client device."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            connections={(dr.CONNECTION_NETWORK_MAC, self._mac)},
            name=self._friendly_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            # via_device resolves because the router device is explicitly
            # registered in async_setup_entry before trackers are created.
            via_device=(DOMAIN, self.coordinator._entry.entry_id),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
