# Changelog

## [0.2.0] - 2026-08-11

### Added

- Offline device creation from custom MAC names
- Raw network type labels and derived network type in diagnostics for debugging firmware-specific variations

### Changed

- Improved network type mapping for router labels
- Device friendly names now persist when devices go offline (not_home state)
- Friendly names are auto-populated for selected devices and preserved across reconnections
- Removed deselected device trackers cleanly from Home Assistant registries

### Fixed

- Device names no longer show as MAC address when offline

## [0.1.0] - 2026-08-09

### Added

- Initial release
- Support for FASTGate DN8245F2 router via the [RouterScraper](https://pypi.org/project/routerscraper/) library
- Full UI-based config flow (no `configuration.yaml` required)
- Options flow for changing the polling interval and selecting monitored devices
- `DataUpdateCoordinator`-based polling (single request loop shared by all trackers)
- `ScannerEntity` device trackers with `home` / `not_home` states
- Device Registry entries backed by MAC address, with `via_device` link to the router
- Custom friendly name support per device (`MAC=Name` format)
- Diagnostics endpoint (no sensitive data exposed)
- English and Italian UI translations
- HACS-compatible project structure
- GitHub Actions CI: HACS validation + hassfest
