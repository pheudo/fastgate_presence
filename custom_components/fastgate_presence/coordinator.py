"""Data Update Coordinator for FASTGate Presence."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from routerscraper.dataTypes import connectedDevice, loginResult
from routerscraper.fastgate_dn8245f2 import fastgate_dn8245f2

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_NAMES,
    CONF_MONITORED_DEVICES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    normalize_mac,
)

_LOGGER = logging.getLogger(__name__)


class FastgatePresenceCoordinator(DataUpdateCoordinator[dict[str, connectedDevice]]):
    """Coordinator that polls the FASTGate router for connected devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._entry = entry
        self._host: str = entry.data[CONF_HOST]
        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]
        self._monitored_macs: list[str] = [
            normalize_mac(mac)
            for mac in entry.options.get(CONF_MONITORED_DEVICES, [])
            if mac.strip()
        ]
        self._device_names: dict[str, str] = {
            normalize_mac(mac): name
            for mac, name in entry.options.get(CONF_DEVICE_NAMES, {}).items()
            if mac.strip()
        }

        scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        self._router_available: bool = False
        self._last_successful_update: datetime | None = None
        
        # Cache of last known hostnames for devices without explicit friendly names.
        # Used to persist the router-reported name when device goes offline.
        self._last_known_hostnames: dict[str, str] = {}

        # Persistent scraper instance reused across polls.
        # Keeping the same instance preserves the session cookie so the router
        # is not asked to create a new authenticated session on every cycle.
        # The session is only re-established when it actually expires.
        self._scraper: fastgate_dn8245f2 | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )

    # ------------------------------------------------------------------
    # Synchronous helpers (always run via async_add_executor_job)
    # ------------------------------------------------------------------

    def _create_scraper(self) -> fastgate_dn8245f2:
        """Instantiate a new RouterScraper (blocking)."""
        return fastgate_dn8245f2(
            host=self._host,
            user=self._username,
            password=self._password,
        )

    def _fetch_devices_sync(self) -> list[connectedDevice]:
        """Fetch the connected device list, reusing the existing session where possible.

        Runs in an executor thread. The coordinator's refresh lock ensures this
        method is never called concurrently with itself.

        Session lifecycle:
        - First call: a new session is established with cleanStart=True.
        - Subsequent calls: the existing session cookie is reused.
          listDevices() handles auto-login internally if the session has
          expired, but that fires at most once per expiry event ? not on
          every poll ? so the router session pool is not exhausted.
        - If listDevices() reports failure even after an internal auto-login,
          the scraper is discarded and a single fresh login is attempted.
        """
        if self._scraper is None:
            self._scraper = self._create_scraper()
            result = self._scraper.login(cleanStart=True)
            if result != loginResult.Success:
                self._scraper = None
                raise UpdateFailed(f"Router login failed: {result.value}")

        devices = self._scraper.listDevices()

        if devices is None:
            # The internal auto-login attempt inside listDevices() failed.
            # Discard the stale scraper and attempt one clean re-login.
            _LOGGER.debug("Session invalid after auto-login attempt; performing fresh login")
            self._scraper = self._create_scraper()
            result = self._scraper.login(cleanStart=True)
            if result != loginResult.Success:
                self._scraper = None
                raise UpdateFailed(f"Router re-login failed: {result.value}")
            devices = self._scraper.listDevices()
            if devices is None:
                self._scraper = None
                raise UpdateFailed("Failed to retrieve device list after re-login")

        return devices

    def _verify_credentials_sync(self) -> loginResult:
        """Verify credentials using a dedicated scraper to avoid disturbing the shared session."""
        scraper = self._create_scraper()
        return scraper.login(cleanStart=True)

    # ------------------------------------------------------------------
    # DataUpdateCoordinator protocol
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, connectedDevice]:
        """Fetch data from the router. Called periodically by HA."""
        _LOGGER.debug("Polling FASTGate router at %s", self._host)

        try:
            devices: list[connectedDevice] = await self.hass.async_add_executor_job(
                self._fetch_devices_sync
            )
        except UpdateFailed:
            self._router_available = False
            raise
        except Exception as err:
            self._router_available = False
            raise UpdateFailed(
                f"Unexpected error communicating with router: {err}"
            ) from err

        self._router_available = True
        self._last_successful_update = datetime.now(tz=timezone.utc)
        _LOGGER.debug("Found %d device(s) connected to router", len(devices))

        new_devices: dict[str, connectedDevice] = {
            normalize_mac(dev.MAC): dev for dev in devices
        }

        previous = self.data or {}
        for mac in set(new_devices) - set(previous):
            _LOGGER.debug("Device joined network: %s (%s)", mac, new_devices[mac].Name)
        for mac in set(previous) - set(new_devices):
            _LOGGER.debug("Device left network: %s", mac)

        return new_devices

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def router_available(self) -> bool:
        """Return True if the router was reachable on the last poll."""
        return self._router_available

    @property
    def all_devices(self) -> dict[str, connectedDevice]:
        """Return all currently connected devices keyed by normalised MAC.

        Always returns a dict (never None) even before the first successful update.
        """
        return self.data or {}

    @property
    def last_successful_update(self) -> datetime | None:
        """Return the UTC timestamp of the last successful poll."""
        return self._last_successful_update

    def get_monitored_macs(self) -> list[str]:
        """Return MAC addresses configured to be monitored."""
        return list(self._monitored_macs)

    def get_device_names(self) -> dict[str, str]:
        """Return dict of MAC -> friendly name for monitored devices."""
        return dict(self._device_names)

    def get_device_display_name(self, mac: str) -> str | None:
        """
        Return the display name for a device.
        
        Priority:
        1. Explicit friendly name (if set in device_names)
        2. Current hostname (if device is online)
        3. Last known hostname (if device was previously online)
        4. None (no name known)
        """
        mac_upper = normalize_mac(mac)
        
        # Explicit friendly name always wins
        if mac_upper in self._device_names:
            return self._device_names[mac_upper]
        
        # If device is currently online, return current hostname
        if mac_upper in self.all_devices:
            hostname = self.all_devices[mac_upper].Name
            # Update last known hostname for future offline use
            self._last_known_hostnames[mac_upper] = hostname
            return hostname
        
        # If device is offline, return last known hostname
        return self._last_known_hostnames.get(mac_upper)

    async def async_verify_credentials(self) -> loginResult:
        """Verify router credentials without affecting the shared scraper session."""
        return await self.hass.async_add_executor_job(self._verify_credentials_sync)

    async def async_fetch_current_devices(self) -> list[connectedDevice]:
        """Return the current device list for the options flow device selector.

        Reuses cached data if it is fresh (< 30 s old) to avoid an unnecessary
        extra poll. Otherwise, triggers a full coordinator refresh and awaits
        its completion so the returned list is always up to date.
        """
        if self._last_successful_update is not None:
            age = (
                datetime.now(tz=timezone.utc) - self._last_successful_update
            ).total_seconds()
            if age < 30 and self.data is not None:
                _LOGGER.debug(
                    "Options flow: reusing cached device list (age %.0fs)", age
                )
                return list(self.data.values())

        # async_refresh() always awaits the full fetch, unlike async_request_refresh()
        # which may return immediately if a refresh is already in progress.
        _LOGGER.debug("Options flow: triggering coordinator refresh for device list")
        await self.async_refresh()
        return list((self.data or {}).values())
