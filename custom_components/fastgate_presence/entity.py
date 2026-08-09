"""Base entity for FASTGate Presence."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, ROUTER_MODEL
from .coordinator import FastgatePresenceCoordinator


class FastgatePresenceEntity(CoordinatorEntity[FastgatePresenceCoordinator]):
    """Base entity for FASTGate Presence, shared by all platforms."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FastgatePresenceCoordinator,
        mac: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._mac = mac.upper()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the router itself."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator._entry.entry_id)},
            name=f"FASTGate Router ({self.coordinator._host})",
            manufacturer=MANUFACTURER,
            model=ROUTER_MODEL,
        )
