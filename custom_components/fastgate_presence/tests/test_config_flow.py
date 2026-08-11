"""Tests for config flow helpers."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.fastgate_presence.config_flow import (
    _merge_monitored_macs,
    _normalise_mac_list,
    _parse_device_names,
)
from custom_components.fastgate_presence.coordinator import (
    FastgatePresenceCoordinator,
)


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
