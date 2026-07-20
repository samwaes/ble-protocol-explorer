# Medisana BS430 Local Integration

A Hupla Labs project to connect a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy, without VitaDock or a cloud service.

## Current status

The core protocol has now been validated against a real synchronization session.

Confirmed:

- automatic discovery after the scale wakes;
- successful Windows BLE connection;
- service `0x78B2` and characteristics `0x8A20`, `0x8A21`, `0x8A22`, `0x8A81`, `0x8A82`;
- synchronization request through `0x8A81`;
- several historical measurements returned in one connection;
- weight and body-composition frames paired by a shared timestamp key;
- measurement timestamps decoded as seconds since `2010-01-01`;
- weight, fat, water, muscle and bone values validated;
- probable impedance field identified;
- probable profile byte identified: tested user is app profile `1`, and the candidate packet field is also `01`.

The next phase is a reusable protocol package followed by a native Home Assistant integration.

## Architecture target

```text
Medisana BS430
      ↓ Bluetooth Low Energy
Reusable local protocol library
      ↓
History synchronizer and duplicate protection
      ↓
Native Home Assistant integration
```

## Important protocol behaviour

The scale does not return only the latest weighing. A validated session returned several stored measurements, newest first. The reader therefore keeps listening until disconnect, timeout or inactivity and pairs `0x8A21` and `0x8A22` frames using their embedded timestamp.

The synchronization command is:

```text
02 <current Unix timestamp as uint32 little-endian>
```

Captured measurement timestamps use a different epoch:

```text
2010-01-01T00:00:00Z + encoded seconds
```

See [docs/protocol-bs430.md](docs/protocol-bs430.md) for the complete current protocol specification.

## Confirmed official-app configuration surface

The official app exposes:

- body-weight unit:
  - Metric
  - Imperial US
  - Imperial UK
- target weight;
- numbered user profile;
- tested user: profile `1`.

These functions are included in the integration capability backlog. They will not become writable controls until their GATT commands and read-back behaviour are verified.

## Work sequence

- [x] Confirm BLE advertisement and synchronization window
- [x] Map proprietary service and characteristics
- [x] Find an established open-source BS430 implementation
- [x] Identify synchronization command
- [x] Decode and validate measurement values
- [x] Confirm multi-record history synchronization
- [x] Correct timestamp epoch and frame pairing
- [x] Preserve profile candidate and unknown fields
- [ ] Refactor protocol into reusable Python modules
- [ ] Add fixture-based protocol tests
- [ ] Scaffold native Home Assistant custom component
- [ ] Add Bluetooth config flow and options flow
- [ ] Add persistent duplicate prevention
- [ ] Add sensors, history events, diagnostics and synchronize button
- [ ] Investigate unit, target-weight and profile configuration commands
- [ ] Package for HACS

See:

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for delivery phases;
- [docs/protocol-bs430.md](docs/protocol-bs430.md) for protocol details;
- [docs/home-assistant-integration-plan.md](docs/home-assistant-integration-plan.md) for the complete integration design.

## Running the current validation reader

Requirements:

- Python 3.11 or 3.12;
- Windows Bluetooth enabled;
- VitaDock and nRF Connect disconnected;
- Bluetooth temporarily disabled on phones that may claim the scale.

Create the environment once:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run:

```powershell
windows\RUN_BS430_READER.bat
```

Wait for scanning, then complete a body-analysis weighing or wake the scale. Output is written under `captures/private` as CSV, LOG and JSON.

## Safety and privacy

The current development phase does not:

- install experimental code in Home Assistant OS;
- modify VirtualBox USB passthrough;
- use or change Zigbee/ZHA;
- require a cloud service;
- issue unverified profile, unit, target-weight, delete or reset commands.

Body-composition readings are personal health data and should not be used for medical decisions.
