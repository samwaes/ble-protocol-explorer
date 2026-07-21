# Medisana BS430 Local Integration

**Status:** Stable for personal use; profile validation active  
**Integration version:** `0.4.2`  
**Protocol version:** `1.0.0`  
**Released:** `2026-07-21`  
**Current milestone:** Validate multiple scale profiles without contaminating existing Home Assistant history

A Hupla Labs project to connect a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy, without VitaDock or a cloud service.

## Release 0.4.2

Version `0.4.2` adds a safe profile-validation mode.

- profile `1` is treated as the currently confirmed primary profile;
- only profile-1 measurements may update the existing Home Assistant sensors;
- measurements with another profile candidate are quarantined in memory;
- measurements without a profile candidate are also quarantined;
- quarantined measurements do not overwrite the current sensors or enter their history;
- downloaded diagnostics show privacy-conscious profile observations, acceptance status and quarantine counters;
- no profile, unit, target-weight, delete or reset commands are written to the scale.

This is an intentionally conservative intermediate release. Separate Home Assistant entities for additional users will only be created after the profile byte has been confirmed through controlled measurements.

## First stable synchronization result

Version `0.4.1` resolved Home Assistant deduplication of identical wake advertisements by clearing advertisement history after each synchronization window.

Confirmed acceptance result:

- three consecutive automatic synchronization tests succeeded;
- the scale fully powered off between every test;
- no use of the manual **Synchronize now** button was required.

Expected normal workflow:

```text
Complete a validated weighing
→ Bluetooth icon starts blinking
→ Home Assistant detects the advertisement
→ Bluetooth icon becomes continuously lit while connected
→ Measurements update
→ Scale powers off
→ Advertisement history is cleared for the next weighing
```

## Profile validation test

After installing `0.4.2`:

1. Restart Home Assistant.
2. Perform one full measurement with scale profile `2` and note the exact time.
3. Let automatic synchronization finish.
4. Confirm that the existing profile-1 sensors did not change to the profile-2 values.
5. Download diagnostics from the integration page.
6. Check `profile_validation.observations` for a record with `profile_id_candidate: 2` and status `quarantined_non_primary_profile`.
7. Repeat once with profile `1` and confirm status `accepted`.

The diagnostics deliberately omit body-composition values and raw frame contents from the profile observation list.

## Current capabilities

- direct local synchronization without VitaDock cloud;
- automatic wake detection after a completed weighing;
- repeated automatic synchronization across complete scale power cycles;
- retry logic throughout most of the scale's short Bluetooth wake window;
- manual **Synchronize now** fallback;
- import of weight, body fat, body water, muscle and bone mass;
- synchronization of several stored historical measurements in one connection;
- pairing of weight and body-composition frames by shared timestamp;
- scale timestamps decoded as seconds since `2010-01-01`;
- last valid sensor values retained while the scale sleeps or is temporarily unreachable;
- HACS installation and updates;
- integration diagnostics with advertisement, trigger, attempt, success, failure and profile-quarantine information.

## Protocol summary

Confirmed service and characteristics:

- service `0x78B2`;
- characteristics `0x8A20`, `0x8A21`, `0x8A22`, `0x8A81`, `0x8A82`.

The synchronization command is:

```text
02 <current Unix timestamp as uint32 little-endian>
```

Captured measurement timestamps use:

```text
2010-01-01T00:00:00Z + encoded seconds
```

The scale can return several stored measurements, newest first. The reader listens until disconnect, timeout or inactivity and pairs `0x8A21` and `0x8A22` frames using their embedded timestamp.

See [docs/protocol-bs430.md](docs/protocol-bs430.md) for the detailed current protocol specification.

## Completed work

- [x] Confirm BLE advertisement and synchronization window
- [x] Map proprietary service and characteristics
- [x] Identify synchronization command
- [x] Decode and validate measurement values
- [x] Confirm multi-record history synchronization
- [x] Correct timestamp epoch and frame pairing
- [x] Preserve profile candidate and unknown fields
- [x] Add native Home Assistant integration, sensors, diagnostics and sync button
- [x] Preserve last sensor values between sync sessions
- [x] Support repeated automatic synchronization
- [x] Validate three consecutive automatic tests after complete scale power-off
- [x] Add primary-profile filtering and quarantine diagnostics

## Non-blocking backlog

- [ ] Confirm profile `1` versus profile `2` through controlled measurements
- [ ] Create separate entities for confirmed profiles
- [ ] Add persistent duplicate handling across Home Assistant restarts
- [ ] Add fixture-based protocol and coordinator tests
- [ ] Confirm impedance decoding
- [ ] Investigate unit, target-weight and profile configuration commands
- [ ] Monitor reliability during normal daily use

## Repository documents

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) — delivery phases
- [docs/protocol-bs430.md](docs/protocol-bs430.md) — protocol details
- [docs/home-assistant-integration-plan.md](docs/home-assistant-integration-plan.md) — integration design
- [docs/install-home-assistant.md](docs/install-home-assistant.md) — Home Assistant installation

## Safety and privacy

The integration does not use a cloud service and does not issue unverified write commands to the scale. Quarantined records remain in integration memory only and are represented in diagnostics without measurement values or raw frame contents.

Body-composition readings are personal health data and should not be used for medical decisions.
