# FASTGate Presence (DN8245F2)

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Home Assistant][ha-badge]][ha-url]
[![Validate][validate-badge]][validate-url]

Home Assistant custom integration that detects device presence by querying a **FASTGate Huawei DN8245F2** router through [RouterScraper](https://pypi.org/project/routerscraper/).

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://hacs.xyz
[release-badge]: https://img.shields.io/github/v/release/pheudo/fastgate_presence
[release-url]: https://github.com/pheudo/fastgate_presence/releases
[license-badge]: https://img.shields.io/github/license/pheudo/fastgate_presence
[license-url]: LICENSE
[ha-badge]: https://img.shields.io/badge/Home%20Assistant-2026.8%2B-blue
[ha-url]: https://www.home-assistant.io
[validate-badge]: https://github.com/pheudo/fastgate_presence/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/pheudo/fastgate_presence/actions/workflows/validate.yml

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pheudo&repository=fastgate_presence)

---

## Why this integration?

| Problem with Ping-based tracking | Solution with this integration |
|---|---|
| Android stops responding to pings while staying on Wi-Fi | The router knows who is associated: zero false negatives |
| Variable latency produces spurious `not_home` states | Direct polling of the router API |
| `device_tracker.see` is deprecated | Uses `ScannerEntity` (modern HA API) |
| One probe per device, competing polls | A single `DataUpdateCoordinator` feeds all trackers |

---

## Features

- No ping, no Companion App, no MQTT
- Fully UI-driven configuration (no `configuration.yaml` changes required)
- Selective device monitoring: you choose which devices get a tracker
- Custom friendly names per device
- Device Registry entries backed by MAC address
- Single `DataUpdateCoordinator` polling loop shared by all trackers
- Installable via HACS

---

## Compatibility and support scope

This integration is intentionally narrow in scope.

- Implemented backend: `routerscraper.fastgate_dn8245f2`
- Supported target in this project: **FASTGate Huawei DN8245F2**
- Other operator routers (including other FASTGate variants and newer non-DN8245F2 models such as NeXXT families) are **not supported** at the moment.

From RouterScraper 0.3.1 metadata and README (PyPI), the Fastgate support is model-specific (`fastgate_dn8245f2`) and `listDevices()` support is declared for that model.

### Default router address

For FASTGate deployments, the router admin UI is commonly reachable on:

- `http://192.168.1.254`
- `http://myfastgate`

For many non-operator / generic Huawei routers, the common default is instead:

- `http://192.168.1.1`

If these addresses do not work in your network, use the gateway shown by your DHCP lease or router label/manual.

---

## Requirements

| Requirement | Version |
|---|---|
| Home Assistant | >= 2026.8.0 |
| Python | >= 3.11 |
| [routerscraper](https://pypi.org/project/routerscraper/) | 0.3.1 |

> `routerscraper` is installed automatically by Home Assistant via the `requirements` field in `manifest.json`. No manual installation needed.

---

## Installation

### Via HACS (recommended)

1. Open **HACS** -> **Integrations** -> three-dot menu -> **Custom repositories**
2. Add the URL `https://github.com/pheudo/fastgate_presence`, category: **Integration**
3. Search for **FASTGate Presence (DN8245F2)** and install
4. Restart Home Assistant

### Manual installation

```bash
# inside the config/ directory of your Home Assistant instance
mkdir -p custom_components
cp -r fastgate_presence/ custom_components/
```

Restart Home Assistant.

---

## Initial configuration

1. Go to **Settings -> Devices & Services -> Add integration**
2. Search for **FASTGate Presence (DN8245F2)**
3. Fill in the following fields:

| Field | Description | Default |
|---|---|---|
| Router IP address | IP of the FASTGate DN8245F2 | `192.168.1.254` |
| Username | Web interface username | `admin` |
| Password | Web interface password | - |
| Polling interval | Seconds between updates | `60` |

4. The integration verifies the credentials before saving.

> **Security note:** the password is stored by Home Assistant in its encrypted storage (`config/.storage/`). It is never written to logs or included in diagnostics.

---

## Selecting devices to monitor

After the initial setup no device trackers are created yet.

1. Go to **Settings -> Devices & Services -> FASTGate Presence (DN8245F2) -> Configure**
2. Adjust the polling interval if needed, then press **Next**
3. A list of all devices **currently connected** to the router is displayed
4. **Select** the ones you want to turn into Device Trackers
5. In the **Friendly name overrides** text box assign human-readable names:

```
AA:BB:CC:DD:EE:FF=Primary phone
11:22:33:44:55:66=Studio laptop
FC:AA:14:55:01:23=Living room TV
```

6. **Save** - Home Assistant reloads and the Device Trackers are created

> **Offline devices:** if a device is not connected at configuration time it will not appear in the list. Wait for it to connect and repeat step 1, or add it manually in the name overrides box (the tracker will be created in `not_home` state and switch to `home` on the next successful poll).

---

## Device Tracker

For each selected device a `device_tracker` entity is created:

| State | When |
|---|---|
| `home` | The device MAC is present in the router's connected client list |
| `not_home` | The MAC is no longer listed as connected |

### Extra state attributes

| Attribute | Content |
|---|---|
| `mac_address` | Normalised uppercase MAC address |
| `hostname` | Name reported by the router |
| `ip_address` | DHCP-assigned IP address |
| `network_type` | `WiFi` or `LAN` |

### Example entity

With friendly name `Primary phone`:

```yaml
device_tracker.primary_phone:
  state: home
  mac_address: AA:BB:CC:DD:EE:FF
  hostname: phone-main
  ip_address: 192.168.1.42
  network_type: WiFi
```

---

## Device Registry

Every tracker registers a **Device** in Home Assistant with:

| Field | Value |
|---|---|
| Manufacturer | Huawei |
| Model | Router Client |
| Connections | MAC Address |
| Name | Custom friendly name or router hostname |
| Via device | The router (DN8245F2) |

---

## Updating options

To change the polling interval or add/remove monitored devices:

**Settings -> Devices & Services -> FASTGate Presence (DN8245F2) -> Configure**

No need to delete and re-add the integration.

---

## Diagnostics

**Settings -> Devices & Services -> FASTGate Presence (DN8245F2) -> ... -> Diagnostics**

Includes:
- Router connection status
- Number of connected devices
- Monitored devices and their current state
- Timestamp of the last successful update

**Never includes:** password, tokens, or any other sensitive data.

---

## Security

- The **password** is stored in HA's encrypted format (`config/.storage/core.config_entries`), never in plain text
- Communication with the router uses **local HTTP** (LAN only) - traffic never leaves your home network
- RouterScraper performs a **new login on every poll cycle** - there are no long-lived sessions to protect
- Log output never contains credentials; DEBUG level only logs MAC addresses and hostnames
- The diagnostics payload is safe to share in bug reports and GitHub issues

---

## Troubleshooting

### Router not reachable

```
cannot_connect
```

- Verify the IP address is correct
- Try opening `http://192.168.1.254` or `http://myfastgate` from the same network
- Ensure Home Assistant is on the same LAN (not on a VPN or different subnet)

### Login failed

```
invalid_auth
```

- Credentials are the same as for the router web interface
- The default FASTGate username is usually `admin`
- The default password is printed on the label on the back of the router

### Login locked

```
login_locked
```

The router temporarily blocks logins after too many failed attempts. Wait 5-10 minutes.

### Device switches to `not_home` while still connected

1. Verify the device appears in the router web interface (`http://192.168.1.254` or `http://myfastgate`)
2. Check HA logs: **Settings -> System -> Logs**, filter by `fastgate_presence`
3. Lower the polling interval to 30 s to check for stability
4. Confirm the selected MAC matches the one shown by the router (some devices use randomised MACs)

### Randomised MAC addresses (Android / iOS)

Android 10+ and iOS 14+ use per-network randomised MAC addresses. The MAC may change on every reconnection.

**Solutions:**
- **Android:** Wi-Fi -> network -> Advanced -> Privacy -> **Use device MAC**
- **iOS:** Settings -> Wi-Fi -> network -> **Private Wi-Fi Address -> off**

---

## Known issues

| Issue | Note |
|---|---|
| RouterScraper is synchronous | Polling runs in a thread pool via `async_add_executor_job` to avoid blocking the HA event loop |
| Login on every poll cycle | The library does not maintain persistent sessions for the DN8245F2 |
| Variable `Network` field format | Depends on router firmware; normalised to `WiFi` / `LAN` at runtime |

---

## Branding and legal disclaimer

This is an **unofficial** community project and is not endorsed, certified, sponsored, or supported by Huawei, Fastweb, or any other router vendor.

The integration is provided "as is", without warranties of any kind, and users remain responsible for verifying local network, legal, and compliance requirements before deployment.

`routerscraper` is a third-party dependency; router firmware changes and upstream library changes may affect compatibility at any time.

Product names, logos, and trademarks (including Huawei, Fastweb, and FASTGate) remain the property of their respective owners and are used strictly for nominative identification of compatible hardware.

---

## Project structure

```
custom_components/
+-- fastgate_presence/
    +-- __init__.py          # Entry setup / unload
    +-- manifest.json        # HA / HACS manifest
    +-- const.py             # Constants
    +-- config_flow.py       # ConfigFlow + OptionsFlow
    +-- coordinator.py       # DataUpdateCoordinator
    +-- device_tracker.py    # device_tracker platform (ScannerEntity)
    +-- entity.py            # Shared base entity
    +-- diagnostics.py       # Diagnostics endpoint
    +-- strings.json         # UI strings (base / English)
    +-- brand/
    |   +-- icon.png         # Adapted icon derived from Fastweb visual base
    +-- translations/
    |   +-- en.json
    |   +-- it.json
    +-- icons.json
    +-- tests/
        +-- __init__.py
        +-- test_coordinator.py
.github/
+-- workflows/
    +-- validate.yml         # HACS + hassfest CI
CHANGELOG.md
LICENSE
README.md
hacs.json
```

---

## Contributing

Pull requests and issues are welcome.

Before opening a PR:
1. Ensure the **HACS Action** and **hassfest** checks pass (GitHub Actions)
2. Run `python -m py_compile` on all modified files
3. Update `CHANGELOG.md`

---

## License

[MIT](LICENSE) (c) 2026 Rodolfo Candido
