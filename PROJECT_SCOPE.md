# Project scope

## Primary objective

Connect a Medisana BS430 smart scale directly to Home Assistant over Bluetooth Low Energy without relying on VitaDock or a cloud service.

The first complete release must:

1. Discover the BS430 when it wakes.
2. Connect during the short BLE availability window.
3. Synchronize all available stored measurements.
4. Pair and decode weight and body-composition frames reliably.
5. prevent duplicate imports across repeated synchronizations.
6. expose measurements, synchronization state and diagnostics in Home Assistant.
7. provide a UI configuration and options flow.
8. preserve a safe path for future scale-side configuration commands.

## Current verified facts

- Device: Medisana BS430
- BLE address observed during testing: `DB:BC:F9:44:FC:17`
- Advertised local name: `0203B 17FC44F9BCDB`
- Proprietary service: `0x78B2`
- Characteristics:
  - `0x8A20`: read
  - `0x8A21`: weight/history indication
  - `0x8A22`: body-composition indication
  - `0x8A81`: synchronization write
  - `0x8A82`: session/status indication
- The scale streams several historical records in one synchronization.
- Weight and feature frames share a timestamp key and must be paired by that key.
- Captured measurement timestamps use a 2010 epoch.
- The tested user is scale profile `1`.
- Weight-frame byte `13` is a probable, but not yet independently confirmed, profile number.
- The official application configures weight units, target weight and numbered profiles.

## Delivery order

### Phase 1: Protocol validation — complete

- [x] Reliable wake, scan and connect loop
- [x] Identify required write to `0x8A81`
- [x] Decode weight and body-composition values
- [x] Validate decoded measurements against real weighings
- [x] Confirm multi-record historical synchronization
- [x] Correct the measurement epoch
- [x] Pair frames by shared timestamp
- [x] Preserve unknown and profile-candidate fields

### Phase 2: Reusable protocol library — current

- [x] Update standalone reader for multi-record synchronization
- [ ] Split transport, protocol, decoder and models into importable modules
- [ ] Add captured-session fixtures with personal values sanitised
- [ ] Add unit tests for timestamps, pairing, metrics and duplicates
- [ ] Define a stable measurement fingerprint
- [ ] Define supported model/capability registry

### Phase 3: Native Home Assistant integration

- [ ] Bluetooth discovery config flow
- [ ] Connection validation and unique device identity
- [ ] Data update coordinator or event-driven synchronizer
- [ ] Persistent seen-record fingerprint store
- [ ] Sensor entities for confirmed measurements
- [ ] Manual `Synchronize now` button
- [ ] Options flow for history, diagnostics and profile mapping
- [ ] Reconfigure and repair flows
- [ ] Device and entity diagnostics
- [ ] Home Assistant events for imported historical records
- [ ] Tests using mocked BLE sessions

### Phase 4: Scale-side configuration investigation

Confirmed application functions to investigate:

- body-weight unit: Metric, Imperial US, Imperial UK
- target weight
- numbered user profile

Rules:

- expose no unverified production writes;
- first capture or source each command;
- classify every capability as confirmed, probable or unknown;
- keep destructive functions such as delete/reset out of scope unless clearly documented and protected.

### Phase 5: Packaging and productisation

- HACS-compatible repository structure
- installation and troubleshooting documentation
- Windows and Linux validation
- unattended synchronization validation
- support matrix for related Medisana models

## Non-goals for the first release

- guessing undocumented scale writes
- automatic person assignment by weight alone
- cloud dependency
- permanent BLE connection
- modifying Zigbee or ZHA
- treating body-composition values as medical measurements
