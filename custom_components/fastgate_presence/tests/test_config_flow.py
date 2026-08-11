"""Tests for config flow helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.fastgate_presence as integration
from custom_components.fastgate_presence.config_flow import (
    _merge_monitored_macs,
    _normalise_mac_list,
    _parse_device_names,
)
from custom_components.fastgate_presence.const import (
    NETWORK_TYPE_LAN,
    NETWORK_TYPE_UNKNOWN,
    NETWORK_TYPE_WIFI,
    classify_network_type,
)
from custom_components.fastgate_presence.coordinator import (
    FastgatePresenceCoordinator,
)
from custom_components.fastgate_presence.device_tracker import tracker_unique_id


class TestConfigFlowHelpers:
    """Test helper functions used by the options flow."""

    def test_parse_device_names_normalises_mac_case(self) -> None:
        """MAC keys from the text area should be treated case-insensitively."""
        result = _parse_device_names(
            "aa:bb:cc:dd:ee:ff=Primary phone\n11:22:33:44:55:66=Studio laptop"
        )

        assert result == {
            "AA:BB:CC:DD:EE:FF": "Primary phone",
            "11:22:33:44:55:66": "Studio laptop",
        }

    def test_parse_device_names_ignores_empty_lines(self) -> None:
        """Empty lines should be skipped gracefully."""
        result = _parse_device_names(
            "aa:bb:cc:dd:ee:ff=Phone\n\n11:22:33:44:55:66=Laptop"
        )

        assert result == {
            "AA:BB:CC:DD:EE:FF": "Phone",
            "11:22:33:44:55:66": "Laptop",
        }

    def test_merge_monitored_macs_includes_custom_names(self) -> None:
        """Custom MACs entered as names should become monitored trackers."""
        result = _merge_monitored_macs(
            ["AA:BB:CC:DD:EE:FF"],
            {"11:22:33:44:55:66": "Studio laptop"},
        )

        assert result == ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]

    def test_normalise_mac_list_deduplicates_and_uppercases(self) -> None:
        """Selected devices should be canonicalised before saving options."""
        result = _normalise_mac_list(
            ["aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
        )

        assert result == ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]


class TestCoordinatorOptionNormalisation:
    """Test that stored options are read in a canonical form."""

    def test_monitored_macs_and_names_are_normalised(self) -> None:
        """Legacy lowercase option values should still resolve correctly."""
        coordinator = FastgatePresenceCoordinator.__new__(FastgatePresenceCoordinator)
        coordinator._entry = MagicMock()
        coordinator._entry.options = {
            "monitored_devices": ["aa:bb:cc:dd:ee:ff"],
            "device_names": {"aa:bb:cc:dd:ee:ff": "Primary phone"},
        }

        assert coordinator.get_monitored_macs() == ["AA:BB:CC:DD:EE:FF"]
        assert coordinator.get_device_names() == {
            "AA:BB:CC:DD:EE:FF": "Primary phone"
        }

    def test_tracker_unique_id_uses_uppercase_mac(self) -> None:
        """Entity unique IDs should stay canonical for MAC matching."""
        assert tracker_unique_id("aa:bb:cc:dd:ee:ff") == "fastgate_presence_AA_BB_CC_DD_EE_FF"

    def test_classify_network_type_maps_router_labels(self) -> None:
        """Router labels should map to WiFi, LAN, or Unknown consistently."""
        assert classify_network_type("SSID5") == NETWORK_TYPE_WIFI
        assert classify_network_type("LAN2") == NETWORK_TYPE_LAN
        assert classify_network_type("bridge") == NETWORK_TYPE_UNKNOWN


class TestDeviceFriendlyNamePersistence:
    """Test that friendly names persist when devices go offline."""

    def test_explicit_name_always_wins(self) -> None:
        """Explicit friendly names should always be used, ignoring router hostname."""
        coordinator = MagicMock()
        coordinator.get_device_display_name.return_value = "My Custom Phone"
        
        mac = "AA:BB:CC:DD:EE:FF"
        # When coordinator returns explicit name, use it
        name = coordinator.get_device_display_name(mac)
        assert name == "My Custom Phone"

    def test_online_device_uses_router_hostname(self) -> None:
        """Online devices without explicit name should use router hostname."""
        coordinator = MagicMock()
        coordinator.get_device_display_name.return_value = "kitchen-phone"
        
        mac = "AA:BB:CC:DD:EE:FF"
        name = coordinator.get_device_display_name(mac)
        assert name == "kitchen-phone"

    def test_offline_device_persists_last_hostname(self) -> None:
        """Offline devices should persist the last hostname seen from router."""
        coordinator = MagicMock()
        # Device was online, we cached its hostname
        coordinator.get_device_display_name.return_value = "office-laptop"
        
        mac = "11:22:33:44:55:66"
        # Even though device is now offline, we return cached hostname
        name = coordinator.get_device_display_name(mac)
        assert name == "office-laptop"

    def test_offline_device_with_no_prior_hostname_falls_back_to_mac(self) -> None:
        """If device never went online, fall back to MAC."""
        coordinator = MagicMock()
        coordinator.get_device_display_name.return_value = None
        
        mac = "AA:BB:CC:DD:EE:FF"
        name = coordinator.get_device_display_name(mac) or mac.upper()
        assert name == "AA:BB:CC:DD:EE:FF"




class TestReloadCleanup:
    """Test cleanup of deselected trackers during reload."""

    @pytest.mark.asyncio
    async def test_async_reload_entry_removes_deselected_tracker_entries(self, monkeypatch) -> None:
        """Deselected MACs should be removed from entity and device registries."""
        removed_mac = "AA:BB:CC:DD:EE:FF"
        kept_mac = "11:22:33:44:55:66"

        coordinator = MagicMock()
        coordinator.get_monitored_macs.return_value = [removed_mac, kept_mac]

        hass = MagicMock()
        hass.data = {
            "fastgate_presence": {
                "entry-1": coordinator,
            }
        }
        hass.config_entries.async_reload = AsyncMock()

        entry = SimpleNamespace(
            entry_id="entry-1",
            options={"monitored_devices": [kept_mac]},
        )

        entity_reg = MagicMock()
        device_reg = MagicMock()
        removed_entity = SimpleNamespace(
            domain="device_tracker",
            unique_id=tracker_unique_id(removed_mac),
            entity_id="device_tracker.removed",
        )
        kept_entity = SimpleNamespace(
            domain="device_tracker",
            unique_id=tracker_unique_id(kept_mac),
            entity_id="device_tracker.kept",
        )
        removed_device = SimpleNamespace(
            identifiers={("fastgate_presence", removed_mac)},
            id="device-removed",
        )
        kept_device = SimpleNamespace(
            identifiers={("fastgate_presence", kept_mac)},
            id="device-kept",
        )

        monkeypatch.setattr(
            integration.er,
            "async_get",
            lambda _hass: entity_reg,
        )
        monkeypatch.setattr(
            integration.er,
            "async_entries_for_config_entry",
            lambda _reg, _entry_id: [removed_entity, kept_entity],
        )
        monkeypatch.setattr(
            integration.dr,
            "async_get",
            lambda _hass: device_reg,
        )
        monkeypatch.setattr(
            integration.dr,
            "async_entries_for_config_entry",
            lambda _reg, _entry_id: [removed_device, kept_device],
        )

        await integration.async_reload_entry(hass, entry)

        entity_reg.async_remove.assert_called_once_with("device_tracker.removed")
        device_reg.async_update_device.assert_called_once_with(
            "device-removed", remove_config_entry_id="entry-1"
        )
        hass.config_entries.async_reload.assert_called_once_with("entry-1")

    @pytest.mark.asyncio
    async def test_async_reload_entry_ignores_device_names_for_retention(self, monkeypatch) -> None:
        """A MAC kept only in device_names should still be removed if deselected."""
        removed_mac = "AA:BB:CC:DD:EE:FF"
        kept_mac = "11:22:33:44:55:66"

        coordinator = MagicMock()
        coordinator.get_monitored_macs.return_value = [removed_mac, kept_mac]

        hass = MagicMock()
        hass.data = {
            "fastgate_presence": {
                "entry-1": coordinator,
            }
        }
        hass.config_entries.async_reload = AsyncMock()

        entry = SimpleNamespace(
            entry_id="entry-1",
            options={
                "monitored_devices": [kept_mac],
                "device_names": {removed_mac: "Legacy phone"},
            },
        )

        entity_reg = MagicMock()
        device_reg = MagicMock()
        removed_entity = SimpleNamespace(
            domain="device_tracker",
            unique_id=tracker_unique_id(removed_mac),
            entity_id="device_tracker.removed",
        )
        kept_entity = SimpleNamespace(
            domain="device_tracker",
            unique_id=tracker_unique_id(kept_mac),
            entity_id="device_tracker.kept",
        )
        removed_device = SimpleNamespace(
            identifiers={("fastgate_presence", removed_mac)},
            id="device-removed",
        )
        kept_device = SimpleNamespace(
            identifiers={("fastgate_presence", kept_mac)},
            id="device-kept",
        )

        monkeypatch.setattr(integration.er, "async_get", lambda _hass: entity_reg)
        monkeypatch.setattr(
            integration.er,
            "async_entries_for_config_entry",
            lambda _reg, _entry_id: [removed_entity, kept_entity],
        )
        monkeypatch.setattr(integration.dr, "async_get", lambda _hass: device_reg)
        monkeypatch.setattr(
            integration.dr,
            "async_entries_for_config_entry",
            lambda _reg, _entry_id: [removed_device, kept_device],
        )

        await integration.async_reload_entry(hass, entry)

        entity_reg.async_remove.assert_called_once_with("device_tracker.removed")
        device_reg.async_update_device.assert_called_once_with(
            "device-removed", remove_config_entry_id="entry-1"
        )
        hass.config_entries.async_reload.assert_called_once_with("entry-1")
