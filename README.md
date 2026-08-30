# Medisana BS430 Local Integration

**Status:** Stable for personal use; historical recovery enabled  
**Integration version:** `0.6.0`  
**Protocol version:** `1.1.0`  
**Released:** `2026-08-30`  
**Current milestone:** Recover scale memory safely after Bluetooth outages

A Hupla Labs project to connect a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy, without VitaDock or a cloud service.

## Release 0.6.0

Version `0.6.0` fixes two issues found after a multi-week Bluetooth outage.

### Mixed timestamp epochs

The same physical BS430 has now been observed returning stored records in two timestamp formats:

- legacy Medisana seconds since `2010-01-01T00:00:00Z`;
- Unix seconds since `1970-01-01T00:00:00Z`.

The decoder evaluates both interpretations and selects the plausible timestamp closest to the current time. This prevents recent Unix timestamps from being incorrectly shifted into the year 2066 while retaining compatibility with older 2010-epoch records.

The established synchronization command remains:

```text
02 <current Unix timestamp as uint32 little-endian>
```

No speculative scale write has been introduced.

### Historical Home Assistant recovery

A successful synchronization can return the scale's stored records, not only the newest weighing. Version `0.6.0` now uses those recovered records to rebuild Home Assistant long-term statistics for the corresponding profile sensors.

- recovered records are routed by scale profile;
- implausible timestamps are rejected before recorder import;
- weight, body fat, body water, muscle, bone mass and impedance can be reconstructed when present;
- Home Assistant's supported statistics import path is used, with no direct database writes;
- imports are hourly because Home Assistant's supported long-term statistics API is hourly;
- repeated synchronization is safe because an existing entity/hour statistic is updated rather than duplicated;
- gaps between recovered weigh-ins are reconstructed using the last known recovered value, matching the normal state-holding behaviour of a Home Assistant measurement sensor;
- the feature can be disabled under **Configure → Recover stored measurement history**.

This repairs long-term trend views after a Bluetooth outage. It does not manufacture exact historical Home Assistant state-change events at the original minute and second.

## Normal workflow

```text
Complete a validated weighing
→ Bluetooth icon starts blinking
→ Home Assistant detects the advertisement
→ Home Assistant connects and requests stored records
→ mixed timestamp formats are normalized
→ current profile sensors update
→ recovered long-term statistics are queued
→ scale powers off
→ advertisement history is cleared for the next weighing
```

No fixed polling interval is used.

## Current capabilities

- direct local synchronization without VitaDock cloud;
- automatic wake detection after a completed weighing;
- retry logic throughout most of the short Bluetooth wake window;
- manual **Synchronize now** fallback;
- weight, body fat, body water, muscle and bone mass import;
- probable impedance decoding;
- synchronization of multiple stored measurements in one connection;
- pairing of weight and body-composition frames by shared timestamp;
- mixed Unix and Medisana-2010 timestamp decoding;
- profiles `1` through `8`, with separate Home Assistant entity sets for configured profiles;
- last valid sensor values retained while the scale sleeps or is unreachable;
- hourly long-term statistics backfill from stored scale history;
- HACS installation and updates;
- diagnostics for Bluetooth activity, synchronization, profile routing, timestamp mode and history backfill.

## Protocol summary

Confirmed service and characteristics:

- service `0x78B2`;
- `0x8A20`: readable device/session value;
- `0x8A21`: weight, timestamp, probable impedance and profile metadata;
- `0x8A22`: timestamp and body-composition values;
- `0x8A81`: synchronization/time command;
- `0x8A82`: status/session indication.

The scale can return several stored measurements, newest first. The reader listens until disconnect, timeout or inactivity and pairs `0x8A21` and `0x8A22` frames using their embedded timestamp key.

See [docs/protocol-bs430.md](docs/protocol-bs430.md) for the detailed current protocol specification.

## Release history

### 0.5.1

- restored sensor values after integration reloads and Home Assistant restarts;
- retained multi-profile routing introduced in `0.5.0`.

### 0.5.0

- supported profile IDs `1` through `8`;
- allowed profile-to-person naming in Home Assistant;
- routed valid profile records to separate entity sets.

### 0.4.2

- introduced conservative profile validation and quarantine diagnostics.

### 0.4.1

- fixed repeated automatic synchronization by clearing Home Assistant Bluetooth advertisement history after each completed window.

## Completed work

- [x] Confirm BLE advertisement and synchronization window
- [x] Map proprietary service and characteristics
- [x] Identify synchronization command
- [x] Decode and validate measurement values
- [x] Confirm multi-record history synchronization
- [x] Pair weight and feature frames by timestamp
- [x] Support profiles 1 through 8
- [x] Preserve last sensor values between sync sessions
- [x] Support repeated automatic synchronization
- [x] Detect both observed timestamp epochs
- [x] Reject implausible history timestamps
- [x] Rebuild hourly Home Assistant long-term statistics from stored scale records
- [x] Make repeated history imports idempotent at the Home Assistant statistics layer

## Remaining backlog

- [ ] Add broader Home Assistant integration tests around recorder import
- [ ] Confirm impedance decoding independently
- [ ] Investigate unit, target-weight and profile configuration commands before enabling any such writes
- [ ] Monitor mixed-epoch behaviour during normal daily use
- [ ] Quantify the exact scale-side history capacity and overwrite behaviour on this hardware revision

## Repository documents

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md): delivery phases
- [docs/protocol-bs430.md](docs/protocol-bs430.md): protocol details
- [docs/home-assistant-integration-plan.md](docs/home-assistant-integration-plan.md): integration design
- [docs/install-home-assistant.md](docs/install-home-assistant.md): Home Assistant installation and verification

## Safety and privacy

The integration is local and does not use a cloud service. It does not issue unverified profile, unit, target-weight, delete or reset writes to the scale. Historical recovery uses Home Assistant's recorder statistics API instead of editing the recorder database directly.

Body-composition readings are personal health data and should not be used for medical decisions.
