# Medisana BS430 Local Integration

**Status:** Beta  
**Integration version:** `0.4.0`  
**Protocol version:** `1.0.0`  
**Source revision:** `aa6ba4c`  
**Released:** `2026-07-20`  
**Current milestone:** Reliable automatic synchronization

A Hupla Labs project to connect a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy, without VitaDock or a cloud service.

## Release 0.4.0

This release focuses on the approximately 30-second Bluetooth wake window after a validated weighing.

Changes:

- automatic synchronization now matches the stable device-name prefix without requiring the proprietary service UUID in every advertisement;
- a configured-address callback is registered as a fallback;
- automatic connection attempts retry throughout most of the Bluetooth wake window;
- synchronization diagnostics now record advertisements, automatic and manual triggers, attempts, successes, failures and the last error;
- measurement sensors retain their last valid value while the scale is asleep or temporarily unreachable, preventing new `unavailable` gaps in Home Assistant history graphs;
- the manual **Synchronize now** button remains available as a fallback.

Expected normal workflow:

```text
Complete a validated weighing
→ Bluetooth icon starts blinking
→ Home Assistant detects the advertisement
→ Bluetooth icon becomes continuously lit while connected
→ Measurements update
```

## Current status

Confirmed:

- direct local synchronization without VitaDock cloud;
- successful Bluetooth connection and measurement import;
- service `0x78B2` and characteristics `0x8A20`, `0x8A21`, `0x8A22`, `0x8A81`, `0x8A82`;
- synchronization request through `0x8A81`;
- several historical measurements returned in one connection;
- weight and body-composition frames paired by a shared timestamp key;
- measurement timestamps decoded as seconds since `2010-01-01`;
- weight, fat, water, muscle and bone values validated;
- probable impedance field identified;
- probable profile byte identified: tested user is app profile `1`, and the candidate packet field is also `01`.

Still under validation:

- automatic synchronization reliability across repeated weighings;
- profile-byte interpretation;
- persistent duplicate prevention;
- scale configuration commands for units, target weight and profile.

## Architecture

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
- [x] Refactor protocol into reusable Python modules
- [ ] Add fixture-based protocol tests
- [x] Scaffold native Home Assistant custom component
- [x] Add Bluetooth config flow
- [ ] Add options flow
- [ ] Add persistent duplicate prevention
- [x] Add sensors, diagnostics and synchronize button
- [x] Preserve last sensor values between sync sessions
- [ ] Validate repeated automatic synchronization
- [ ] Investigate unit, target-weight and profile configuration commands
- [x] Package as a custom HACS repository

See:

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for delivery phases;
- [docs/protocol-bs430.md](docs/protocol-bs430.md) for protocol details;
- [docs/home-assistant-integration-plan.md](docs/home-assistant-integration-plan.md) for the complete integration design.

## Testing release 0.4.0

1. Update the custom repository in HACS.
2. Confirm that HACS shows version `0.4.0`.
3. Restart Home Assistant.
4. Complete a full body-analysis weighing.
5. Do not press **Synchronize now** during the first test.
6. Verify that the scale Bluetooth icon changes from blinking to continuously lit and that the sensors update.
7. Repeat after the scale has fully switched off.

If automatic synchronization fails, use **Download diagnostics** on the integration device page. The diagnostics include the last advertisement, trigger type, attempt, successful synchronization and error counters.

## Running the validation reader

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

The integration does not:

- use or require a cloud service;
- modify VirtualBox USB passthrough;
- use or change Zigbee/ZHA;
- issue unverified profile, unit, target-weight, delete or reset commands.

Body-composition readings are personal health data and should not be used for medical decisions.
