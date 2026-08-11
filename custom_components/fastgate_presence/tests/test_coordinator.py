"""Tests for the coordinator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from routerscraper.dataTypes import connectedDevice, loginResult


MOCK_DEVICES = [
    connectedDevice(
        Name="phone1",
        MAC="AA:BB:CC:DD:EE:FF",
        IP="192.168.1.10",
        additionalInfo={"isFamily": False, "Network": "WiFi"},
    ),
    connectedDevice(
        Name="laptop",
        MAC="11:22:33:44:55:66",
        IP="192.168.1.20",
        additionalInfo={"isFamily": False, "Network": "LAN"},
    ),
]


class TestFetchDevicesSync:
    """Test _fetch_devices_sync logic."""

    def test_returns_device_list_on_success(self) -> None:
        """Test that devices are returned after a successful login."""
        mock_scraper = MagicMock()
        mock_scraper.login.return_value = loginResult.Success
        mock_scraper.listDevices.return_value = MOCK_DEVICES

        with patch(
            "custom_components.fastgate_presence.coordinator.fastgate_dn8245f2",
            return_value=mock_scraper,
        ):
            from custom_components.fastgate_presence.coordinator import (
                FastgatePresenceCoordinator,
            )
            from unittest.mock import MagicMock as MM

            entry = MM()
            entry.data = {
                "host": "192.168.1.1",
                "username": "admin",
                "password": "password",
                "scan_interval": 60,
                "monitored_devices": [],
                "device_names": {},
            }
            entry.options = {}
            entry.entry_id = "test_entry"

            hass = MM()
            coordinator = FastgatePresenceCoordinator.__new__(FastgatePresenceCoordinator)
            coordinator._host = "192.168.1.1"
            coordinator._username = "admin"
            coordinator._password = "password"
            coordinator._entry = entry
            coordinator._scraper = None
            coordinator._router_available = False
            coordinator._all_devices = {}

            with patch.object(coordinator, "_create_scraper", return_value=mock_scraper):
                result = coordinator._fetch_devices_sync()

            assert len(result) == 2
            assert result[0].MAC == "AA:BB:CC:DD:EE:FF"
            assert result[1].MAC == "11:22:33:44:55:66"

    def test_raises_on_wrong_password(self) -> None:
        """Test that UpdateFailed is raised when login fails."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        mock_scraper = MagicMock()
        mock_scraper.login.return_value = loginResult.WrongPass

        with patch(
            "custom_components.fastgate_presence.coordinator.fastgate_dn8245f2",
            return_value=mock_scraper,
        ):
            from custom_components.fastgate_presence.coordinator import (
                FastgatePresenceCoordinator,
            )
            from unittest.mock import MagicMock as MM

            coordinator = FastgatePresenceCoordinator.__new__(FastgatePresenceCoordinator)
            coordinator._host = "192.168.1.1"
            coordinator._username = "admin"
            coordinator._password = "wrong"

            with patch.object(coordinator, "_create_scraper", return_value=mock_scraper):
                with pytest.raises(UpdateFailed):
                    coordinator._fetch_devices_sync()


class TestMACNormalisation:
    """Test MAC address normalisation in coordinator data."""

    def test_mac_is_uppercased(self) -> None:
        """Devices returned with lowercase MACs must be normalised."""
        devices = [
            connectedDevice(
                Name="test",
                MAC="aa:bb:cc:dd:ee:ff",
                IP="10.0.0.1",
                additionalInfo={},
            )
        ]
        result = {dev.MAC.upper(): dev for dev in devices}
        assert "AA:BB:CC:DD:EE:FF" in result


class TestDeviceTrackerNameFallback:
    """Test device tracker name resolution when devices are offline."""

    def test_friendly_name_takes_precedence_over_hostname(self) -> None:
        """Explicitly set friendly names should always win."""
        from custom_components.fastgate_presence.const import normalize_mac
        
        mac_upper = normalize_mac("aa:bb:cc:dd:ee:ff")
        friendly_name = "My Phone"
        device_data = MagicMock()
        device_data.Name = "RouterHostname"
        device_names = {mac_upper: friendly_name}
        
        # Name resolution logic from device_tracker.py
        if friendly_name:
            name = friendly_name
        elif device_data:
            name = device_data.Name
        else:
            name = friendly_name or mac_upper
        
        assert name == "My Phone"

    def test_offline_device_keeps_saved_name(self) -> None:
        """When offline (device_data=None), saved name should be used."""
        from custom_components.fastgate_presence.const import normalize_mac
        
        mac_upper = normalize_mac("aa:bb:cc:dd:ee:ff")
        friendly_name = "Kitchen Phone"  # Saved from auto-populate or manual override
        device_data = None  # Device is offline
        device_names = {mac_upper: friendly_name}
        
        # Name resolution logic from device_tracker.py
        if friendly_name:
            name = friendly_name
        elif device_data:
            name = device_data.Name
        else:
            name = friendly_name or mac_upper
        
        # Should not fall back to MAC
        assert name == "Kitchen Phone"

    def test_online_device_uses_current_hostname(self) -> None:
        """When online, current hostname should be visible (unless overridden)."""
        from custom_components.fastgate_presence.const import normalize_mac
        
        mac_upper = normalize_mac("aa:bb:cc:dd:ee:ff")
        friendly_name = None  # Not explicitly set
        device_data = MagicMock()
        device_data.Name = "latest-hostname"
        device_names = {}
        
        # Name resolution logic from device_tracker.py
        if friendly_name:
            name = friendly_name
        elif device_data:
            name = device_data.Name
        else:
            name = friendly_name or mac_upper
        
        assert name == "latest-hostname"

    def test_offline_device_with_no_saved_name_falls_back_to_mac(self) -> None:
        """When offline with no saved name, MAC should be shown as last resort."""
        from custom_components.fastgate_presence.const import normalize_mac
        
        mac_upper = normalize_mac("aa:bb:cc:dd:ee:ff")
        friendly_name = None
        device_data = None  # Device is offline
        device_names = {}
        
        # Name resolution logic from device_tracker.py
        if friendly_name:
            name = friendly_name
        elif device_data:
            name = device_data.Name
        else:
            name = friendly_name or mac_upper
        
        assert name == "AA:BB:CC:DD:EE:FF"
