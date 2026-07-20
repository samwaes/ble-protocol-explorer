# Medisana BS430 BLE protocol

## Status

The core transport and measurement protocol is now validated against a real BS430 synchronization session. The scale returned several stored measurements in one connection, confirming that synchronization is historical rather than latest-only.

The implementation in this repository is an independent Python implementation informed by public openScale protocol support and our own captures. No openScale source code is copied.

## Verified device behaviour

The scale is not continuously connectable. A completed weighing wakes the BLE interface and creates a short synchronization window. A client must scan, stop scanning once the device is found, connect quickly, enable indications, request synchronization, receive all stored records, and tolerate the scale powering down.

One validated session returned four weight records in newest-first order:

| Local time (Europe/Brussels) | Weight |
|---|---:|
| 2026-07-20 16:49:25 | 81.0 kg |
| 2026-07-20 14:16:16 | 80.4 kg |
| 2026-07-20 14:14:53 | 80.4 kg |
| 2026-07-20 13:14:22 | 80.0 kg |

The newest record matched a manually observed weighing at approximately 16:49 after eating.

## Advertisement

- Observed address: `DB:BC:F9:44:FC:17`
- Local name: `0203B 17FC44F9BCDB`
- Name prefix identifying BS430 variants: `0203B`
- Advertised service: `000078b2-0000-1000-8000-00805f9b34fb`

## Proprietary GATT service

Service: `0x78B2`

| Characteristic | Properties | Established purpose |
|---|---|---|
| `0x8A20` | Read | Device/session value; observed as `37 FB`, not required for measurement retrieval |
| `0x8A21` | Indicate | Weight, measurement timestamp, probable impedance and profile metadata |
| `0x8A22` | Indicate | Matching timestamp and body-composition values |
| `0x8A81` | Write | Synchronization request/time command |
| `0x8A82` | Indicate | Status/session frame |

## Session sequence

1. Detect the scale after a completed weighing or while it is awake.
2. Stop BLE scanning before connecting.
3. Connect to the scale.
4. Enable indications in this order:
   - `0x8A22`
   - `0x8A21`
   - `0x8A82`
5. Write the synchronization command to `0x8A81` with a GATT response:

```text
02 <current Unix timestamp as uint32 little-endian>
```

6. Continue receiving records until the scale disconnects or the stream becomes inactive.

Important distinction:

- the synchronization command uses the current Unix timestamp;
- captured BS430 measurement timestamps use seconds since `2010-01-01T00:00:00Z`.

## Record pairing

Each weight frame and its feature frame contain the same four-byte timestamp key:

- `0x8A21`: bytes `5..8`
- `0x8A22`: bytes `1..4`

Frames must be paired by this key, not merely by arrival order.

Example:

```text
8A21: 1D A4 1F 00 FE 75 FA 20 1F 0D 13 00 FF 01 09 00 00 00 00
8A22: 6F 75 FA 20 1F 01 B9 0A C8 F0 69 F2 79 F1 20 F0 00 00 00
                    └──────────┘ shared timestamp 75 FA 20 1F
```

## Measurement timestamp

```text
measurement_time_utc = 2010-01-01T00:00:00Z + uint32_le(timestamp_bytes) seconds
```

For `75 FA 20 1F`:

```text
UTC:              2026-07-20 14:49:25
Europe/Brussels:  2026-07-20 16:49:25
```

## Weight frame: `0x8A21`

Observed length: 19 bytes.

| Bytes | Encoding | Meaning | Status |
|---|---|---|---|
| `1..2` | unsigned 16-bit little-endian | Weight in kilograms multiplied by 100 | Confirmed |
| `5..8` | unsigned 32-bit little-endian | Seconds since 2010-01-01 | Confirmed |
| `9..10` | unsigned 16-bit little-endian divided by 10 | Probable bioelectrical impedance in ohms | Probable |
| `13` | unsigned byte | Candidate scale profile number | Probable, not independently confirmed |

The tested user is configured in the VitaDock application as profile `1`, and byte `13` was consistently `01` in the captured records. The integration must expose this as a candidate until corroborated by documentation or another profile capture.

## Feature frame: `0x8A22`

Observed length: 19 bytes.

| Bytes | Meaning |
|---|---|
| `1..4` | Measurement timestamp key, seconds since 2010-01-01 |
| `8..9` | Body fat percentage |
| `10..11` | Body water percentage |
| `12..13` | Muscle percentage |
| `14..15` | Bone mass in kilograms |

Each body-composition value is decoded as:

```text
value = (uint16_le(bytes) & 0x0FFF) / 10
```

## Observed status frame: `0x8A82`

```text
84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00
```

This is retained for diagnostics but is not needed to decode measurements.

## Confirmed app configuration surface

The official scale application exposes these scale/user settings:

- body-weight unit:
  - Metric
  - Imperial US
  - Imperial UK
- target weight
- numbered user profile
- tested user: profile `1`

These settings establish a concrete future write-capability backlog. Their GATT commands are not yet known and must not be guessed in production code.

## Integration rules

- Support several historical records per synchronization.
- Pair frames by timestamp key.
- Sort completed records by decoded measurement time.
- Treat equal weight values at different timestamps as separate measurements.
- Deduplicate only exact records, using timestamp plus packet content.
- Preserve unknown bytes for diagnostics.
- Expose profile byte `13` as an unconfirmed candidate.
- Never issue profile, unit, target-weight, delete or reset writes until their commands are independently verified.
