# FASTGate Presence (DN8245F2)

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Home Assistant][ha-badge]][ha-url]
[![Validate][validate-badge]][validate-url]

**Track which devices are connected to your FASTGate Huawei DN8245F2 router in Home Assistant.**

Unlike ping-based tracking, this integration queries the router directly for reliable home/away presence detection. No ping, no app, no MQTT—just simple, accurate device tracking.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pheudo&repository=fastgate_presence)

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

---

## Features

- **No ping, no Companion App, no MQTT** — pure router API polling
- **Reliable detection** — Android devices won't randomly show as away while on Wi-Fi
- **Fully UI-driven** — no `configuration.yaml` needed
- **Selective monitoring** — choose which devices get a tracker
- **Custom names** — assign friendly names to each device
- **Single polling loop** — efficient with a shared `DataUpdateCoordinator`
- **Installable via HACS**

---

## Why this integration vs. ping-based tracking?

| Problem with Ping | This Integration |
|---|---|
| Android stops responding to pings while on Wi-Fi | Router knows who is associated—zero false negatives |
| Variable latency causes spurious `not_home` states | Direct router API polling—stable and fast |
| `device_tracker.see` is deprecated | Uses modern `ScannerEntity` API |
| One probe per device creates polling conflicts | Single `DataUpdateCoordinator` for all devices |

---

## Compatibility

- **Supported:** FASTGate Huawei **DN8245F2**
- **Not supported:** Other FASTGate variants, NeXXT, or other Huawei models

Uses [RouterScraper](https://pypi.org/project/routerscraper/) 0.3.1 with the `fastgate_dn8245f2` backend.

Source: [RouterScraper GitHub repository](https://github.com/fra87/RouterScraper)

### Default router address

- `http://192.168.1.254` (FASTGate)
- `http://myfastgate` (FASTGate)
- `http://192.168.1.1` (other Huawei routers)

If these don't work, check your router label or DHCP gateway.

---

## Requirements

| Requirement | Version |
|---|---|
| Home Assistant | >= 2026.8.0 |
| Python | >= 3.11 |
| [routerscraper](https://pypi.org/project/routerscraper/) | 0.3.1 |

> `routerscraper` is installed automatically via Home Assistant. No manual setup needed.

---

## Installation

### Via HACS (recommended)

1. Open **HACS** → **Integrations** → three-dot menu → **Custom repositories**
2. Add `https://github.com/pheudo/fastgate_presence` (category: Integration)
3. Search for **FASTGate Presence (DN8245F2)** and install
4. Restart Home Assistant

### Manual installation

```bash
mkdir -p ~/config/custom_components
cp -r fastgate_presence/ ~/config/custom_components/
```

Restart Home Assistant.

---

## Setup

### 1. Initial Configuration

1. **Settings → Devices & Services → Create Integration**
2. Search for **FASTGate Presence (DN8245F2)**
3. Fill in:

| Field | Description | Default |
|---|---|---|
| Router IP | FASTGate IP address | `192.168.1.254` |
| Username | Router web login | `admin` |
| Password | Router web password | — |
| Polling interval | Seconds between updates | `60` |

The integration verifies credentials before saving.

> **Security:** Passwords are encrypted in Home Assistant's secure storage, never logged or exposed in diagnostics.

### 2. Select Devices to Monitor

1. **Settings → Devices & Services → FASTGate Presence → Configure**
2. Review/adjust polling interval, click **Next**
3. See all currently connected devices
4. **Select** which ones to track
5. (Optional) Add friendly names in the overrides box:

```
AA:BB:CC:DD:EE:FF=Primary phone
11:22:33:44:55:66=Studio laptop
FC:AA:14:55:01:23=Living room TV
```

6. **Save** — device trackers are created

### Device name behavior

**If you assign a custom friendly name:**
- The name persists always, both online and offline
- Router hostname changes are ignored
- The name never changes (unless you edit it)

**If you select a device from the list without a custom name:**
- When **online:** Home Assistant displays the current router hostname
- When **offline:** Home Assistant displays the last hostname seen from the router
- When **reconnecting:** The name updates to the current router hostname

**If a device never went online:**
- Home Assistant falls back to displaying the MAC address

**If you want to add a device manually:**
- Add a line like `AA:BB:CC:DD:EE:FF=` in the overrides box
- Add `AA:BB:CC:DD:EE:FF=My name` if you also want a fixed friendly name
- Any MAC written in the overrides box is monitored, even if it is not currently online

> **Offline devices:** Add any MAC via the overrides box even if not currently connected. The tracker starts in `not_home` and switches to `home` when detected.
>
> MAC addresses are case-insensitive: `aa:bb:cc:dd:ee:ff=Phone` works the same as `AA:BB:CC:DD:EE:FF=Phone`.

---

## Device Tracker Entities

For each monitored device, a `device_tracker.<name>` entity is created.

### States

| State | Condition |
|---|---|
| `home` | Device MAC detected in router's client list |
| `not_home` | Device MAC no longer connected |

### Attributes

| Attribute | Content |
|---|---|
| `mac_address` | Uppercase MAC address |
| `hostname` | Name from router |
| `ip_address` | DHCP-assigned IP |
| `network_type` | `WiFi`, `LAN`, or `Unknown` |

### Example

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

Each tracker registers a Home Assistant Device:

| Field | Value |
|---|---|
| Manufacturer | Huawei |
| Model | Router Client |
| Connections | MAC Address |
| Name | Custom friendly name or router hostname |
| Via device | The router (DN8245F2) |

---

## Managing Devices

### Add or remove devices

**Settings → Devices & Services → FASTGate Presence → Configure** → follow step 2 above

### Update polling interval

Same configure screen as above.

### Remove a device

Deselect it in the configure screen. On save, the tracker and registry entry are automatically deleted.

---

## Diagnostics

**Settings → Devices & Services → FASTGate Presence → ⋮ → Diagnostics**

Shows:
- Router connection status
- Connected device count
- Monitored devices and states
- Last update timestamp
- Network type debugging info

**Safe to share:** Never includes passwords, tokens, or sensitive data.

---

## Security

- **Password storage:** Encrypted in Home Assistant's secure config storage (`config/.storage/core.config_entries`), never in plain text
- **Network:** Local HTTP only (LAN only)—no internet traffic
- **Sessions:** RouterScraper creates a fresh login per poll cycle—no long-lived tokens to protect
- **Logging:** Credentials never logged; DEBUG logs only MAC and hostname
- **Diagnostics:** Safe to share publicly

---

## Troubleshooting

### Router not reachable (`cannot_connect`)

- Verify the IP address
- Try opening `http://192.168.1.254` or `http://myfastgate` from your network
- Ensure Home Assistant is on the same LAN (not VPN'd or on a different subnet)

### Login failed (`invalid_auth`)

- Verify credentials match the router web interface
- Default username is usually `admin`
- Default password is on the router label

### Login locked (`login_locked`)

The router temporarily blocks logins after multiple failed attempts. Wait 5–10 minutes.

### Device shows `not_home` while still connected

1. Verify the device appears in the router web UI (`http://192.168.1.254`)
2. Check Home Assistant logs: **Settings → System → Logs** → filter `fastgate_presence`
3. Try lowering polling interval to 30 s
4. Confirm the MAC address matches (some devices randomize MACs on reconnect)

### Randomized MAC addresses (Android 10+, iOS 14+)

Android and iOS use randomized MACs per network. They may change on every reconnection.

**Fix:**
- **Android:** Wi-Fi → network → Advanced → Privacy → **Use device MAC**
- **iOS:** Settings → Wi-Fi → network → **Private Wi-Fi Address** → **off**

---

## Known Limitations

| Limitation | Reason |
|---|---|
| RouterScraper is synchronous | Polling runs in a thread pool to avoid blocking Home Assistant |
| Login on every poll | DN8245F2 doesn't support persistent sessions |
| Variable network labels | Router firmware formats the `Network` field differently; we normalize to `WiFi`/`LAN` |

---

## Legal

This is an **unofficial** community project—not endorsed by Huawei, Fastweb, or any router vendor.

Provided "as-is" without warranties. Users are responsible for network, legal, and compliance requirements.

RouterScraper is a third-party dependency; firmware and library changes may affect compatibility.

Product names and trademarks (Huawei, Fastweb, FASTGate) are used for identification only.

---

## Contributing

Pull requests and issues welcome.

Before opening a PR:
1. Ensure **HACS** and **hassfest** checks pass (GitHub Actions)
2. Validate Python: `python -m py_compile` on modified files
3. Update `CHANGELOG.md`

---

## License

[MIT](LICENSE) (c) 2026 Rodolfo Candido
