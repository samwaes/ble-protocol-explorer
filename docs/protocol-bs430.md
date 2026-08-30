# Medisana BS430 BLE protocol

## Status

The transport and measurement protocol is validated against real BS430 synchronization sessions. The scale can return several stored measurements in one connection, confirming that synchronization is historical rather than latest-only.

The implementation in this repository is an independent Python implementation informed by public protocol references and direct captures from the tested BS430.

## Verified device behaviour

The scale is not continuously connectable. A completed weighing wakes the BLE interface and creates a short synchronization window. A client must connect quickly, enable indications, request synchronization, receive the offered stored records and tolerate the scale powering down.

A July 2026 validation session returned four stored measurements in newest-first order. An August 2026 synchronization after an extended Bluetooth outage returned 29 valid profile-1 records in one session.

## Advertisement

- Local name observed on the tested unit: `0203B 17FC44F9BCDB`
- Name prefix identifying this BS430 variant: `0203B`
- Advertised service: `000078b2-0000-1000-8000-00805f9b34fb`

The Home Assistant configuration stores the discovered Bluetooth address rather than relying only on the name.

## Proprietary GATT service

Service: `0x78B2`

| Characteristic | Properties | Established purpose |
|---|---|---|
| `0x8A20` | Read | Device/session value; not required for measurement retrieval |
| `0x8A21` | Indicate | Weight, measurement timestamp, probable impedance and profile metadata |
| `0x8A22` | Indicate | Matching timestamp and body-composition values |
| `0x8A81` | Write | Synchronization/time command |
| `0x8A82` | Indicate | Status/session frame |

## Session sequence

1. Detect the scale after a completed weighing or while it is awake.
2. Connect during the short Bluetooth window.
3. Enable indications on:
   - `0x8A22`
   - `0x8A21`
   - `0x8A82`
4. Write the synchronization command to `0x8A81` with a GATT response:

```text
02 <current Unix timestamp as uint32 little-endian>
```

5. Continue receiving records until the scale disconnects or the stream becomes inactive.

The current implementation deliberately keeps the synchronization command on Unix time. Current `0203B` hardware accepts that format, and changing a scale write is not necessary to decode the mixed historical timestamp formats described below.

## Record pairing

Each weight frame and feature frame contain the same four-byte timestamp key:

- `0x8A21`: bytes `5..8`
- `0x8A22`: bytes `1..4`

Frames must be paired by this key, not merely by arrival order.

Example from a July capture:

```text
8A21: 1D A4 1F 00 FE 75 FA 20 1F 0D 13 00 FF 01 09 00 00 00 00
8A22: 6F 75 FA 20 1F 01 B9 0A C8 F0 69 F2 79 F1 20 F0 00 00 00
                    └──────────┘ shared timestamp 75 FA 20 1F
```

## Measurement timestamp: two observed encodings

The earlier assumption that every BS430 measurement timestamp uses seconds since 2010 is no longer valid.

The same tested scale has produced both:

1. **Legacy Medisana epoch**

```text
candidate = 2010-01-01T00:00:00Z + raw seconds
```

Example raw value:

```text
522254965 → 2026-07-20T14:49:25Z
```

2. **Unix epoch**

```text
candidate = 1970-01-01T00:00:00Z + raw seconds
```

Example raw value:

```text
1788067144 → 2026-08-30T05:19:04Z
```

Blindly adding the 2010 offset to the latter produces a false timestamp in 2066.

### Decoder rule

For every raw timestamp the decoder calculates both candidates:

```text
unix_candidate   = raw interpreted as Unix seconds
legacy_candidate = raw + 1,262,304,000 seconds
```

It selects the candidate that is plausible and closest to the current/reference time. A broad five-year plausibility window is used because the physical scale retains recent personal measurements, not an archival multi-year dataset. If neither candidate falls inside that window, proximity is used as a diagnostic fallback rather than failing packet decoding.

The chosen mode is retained on each measurement as:

- `unix`; or
- `medisana_2010`.

Home Assistant diagnostics expose that mode without exposing body-composition values or raw packet contents.

## Weight frame: `0x8A21`

Observed length: 19 bytes.

| Bytes | Encoding | Meaning | Status |
|---|---|---|---|
| `1..2` | unsigned 16-bit little-endian | Weight in kilograms multiplied by 100 | Confirmed |
| `5..8` | unsigned 32-bit little-endian | Measurement timestamp key; epoch can be Unix or Medisana 2010 | Confirmed mixed encoding |
| `9..10` | unsigned 16-bit little-endian divided by 10 | Probable bioelectrical impedance in ohms | Probable |
| `13` | unsigned byte | Candidate scale profile number | Operationally validated for profile routing |

## Feature frame: `0x8A22`

Observed length: 19 bytes.

| Bytes | Meaning |
|---|---|
| `1..4` | Matching measurement timestamp key |
| `8..9` | Body fat percentage |
| `10..11` | Body water percentage |
| `12..13` | Muscle percentage |
| `14..15` | Bone mass in kilograms |

Each body-composition value is decoded as:

```text
value = (uint16_le(bytes) & 0x0FFF) / 10
```

## Status frame

An observed `0x8A82` status frame was:

```text
84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00
```

It is retained for diagnostics but is not needed to decode measurements.

## Scale profile behaviour

The stored records include a profile candidate in byte `13` of the weight frame. The Home Assistant integration accepts valid profile IDs `1` through `8` and routes them to separate entity sets. Missing or out-of-range profile IDs are quarantined.

The scale returns stored history associated with the profile active during the weighing/synchronization workflow. Profile-to-person names exist only in Home Assistant and are not written back to the scale.

## Home Assistant historical reconstruction

The BLE layer returns complete stored measurements. Version `0.6.0` can use them to repair Home Assistant long-term statistics after a connectivity gap.

Protocol decoding and Home Assistant history reconstruction remain separate responsibilities:

```text
BLE frames
→ pair by raw timestamp key
→ decode values
→ normalize timestamp epoch
→ validate profile
→ current sensor update
→ hourly recorder statistics reconstruction
```

The recorder import uses Home Assistant's supported hourly statistics API. It does not write directly to the recorder database.

## Integration rules

- Support several historical records per synchronization.
- Pair weight and feature frames by raw timestamp key.
- Treat equal weight values at different timestamps as separate measurements.
- Deduplicate exact records by timestamp plus packet content inside one synchronization result.
- Decode each timestamp independently because a result set may contain mixed epoch formats.
- Reject implausible dates before historical recorder import.
- Preserve unknown bytes for protocol diagnostics, but keep privacy-conscious Home Assistant diagnostics free of measurement values and raw frames.
- Route valid profile IDs `1` through `8` separately.
- Keep the established synchronization command on Unix time unless new captures prove that a different write is required.
- Never issue profile, unit, target-weight, delete or reset writes until those commands are independently verified.
