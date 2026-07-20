# Medisana BS430 Local Integration

**Status:** Stable for personal use  
**Integration version:** `0.4.1`  
**Protocol version:** `1.0.0`  
**Released:** `2026-07-20`  
**Current milestone:** First stable local Home Assistant version complete

A Hupla Labs project to connect a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy, without VitaDock or a cloud service.

## Release 0.4.1

Version `0.4.1` completes the first stable personal-use implementation.

The final reliability issue was caused by Home Assistant deduplicating identical wake advertisements after the first successful session. The integration now clears Home Assistant's advertisement history after every synchronization window, allowing the same scale advertisement to trigger future connections again.

Confirmed acceptance result:

- one initial successful automatic synchronization;
- diagnostics used to identify the repeated-wake problem;
- fix released in `0.4.1`;
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
- Home Assistant history graphs no longer receive new `unavailable` gaps from expected sleep behaviour;
- HACS installation and updates;
- integration diagnostics with advertisement, trigger, attempt, success and failure information;
- visible integration version and build revision.

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

## Installation and normal use

Install the repository through HACS, restart Home Assistant and configure the discovered scale.

For normal operation:

1. Complete a full body-analysis weighing.
2. Wait for the Bluetooth icon to start blinking.
3. Home Assistant should connect automatically and the icon should become continuously lit.
4. The measurements should update without opening VitaDock or pressing a button.

Use **Download diagnostics** from the integration page if a future synchronization fails. The manual **Synchronize now** button remains available as a fallback.

## Completed work

- [x] Confirm BLE advertisement and synchronization window
- [x] Map proprietary service and characteristics
- [x] Identify synchronization command
- [x] Decode and validate measurement values
- [x] Confirm multi-record history synchronization
- [x] Correct timestamp epoch and frame pairing
- [x] Preserve profile candidate and unknown fields
- [x] Refactor protocol into reusable Python modules
- [x] Scaffold native Home Assistant custom component
- [x] Add Bluetooth config flow
- [x] Add sensors, diagnostics and synchronize button
- [x] Preserve last sensor values between sync sessions
- [x] Support repeated automatic synchronization
- [x] Clear Home Assistant advertisement history after each session
- [x] Package as a custom HACS repository
- [x] Validate three consecutive automatic tests after complete scale power-off

## Non-blocking backlog

- [ ] Add fixture-based protocol and coordinator tests
- [ ] Add options flow where it creates real user value
- [ ] Validate persistent duplicate handling across longer-term use
- [ ] Restore the last measurement immediately after Home Assistant restart if needed
- [ ] Validate multiple user profiles
- [ ] Confirm impedance decoding
- [ ] Investigate unit, target-weight and profile configuration commands
- [ ] Monitor reliability during normal daily use and future Home Assistant Bluetooth changes

## Confirmed official-app configuration surface

The official app exposes:

- body-weight unit: Metric, Imperial US and Imperial UK;
- target weight;
- numbered user profile;
- tested user: profile `1`.

These functions remain backlog items. They will not become writable controls until their GATT commands and read-back behaviour are verified.

## Repository documents

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) — delivery phases
- [docs/protocol-bs430.md](docs/protocol-bs430.md) — protocol details
- [docs/home-assistant-integration-plan.md](docs/home-assistant-integration-plan.md) — integration design
- [docs/install-home-assistant.md](docs/install-home-assistant.md) — Home Assistant installation

## Safety and privacy

The integration does not:

- use or require a cloud service;
- modify VirtualBox USB passthrough;
- use or change Zigbee/ZHA;
- issue unverified profile, unit, target-weight, delete or reset commands.

Body-composition readings are personal health data and should not be used for medical decisions.
