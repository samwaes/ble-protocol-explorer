# Medisana BS430 BLE protocol notes

## Verified device behaviour

The scale is not continuously connectable. A completed weighing wakes the BLE interface and creates a short synchronization window. A client must scan continuously, detect the advertisement, connect quickly, retrieve the measurement, and tolerate the scale disconnecting when it powers down.

## Advertisement

- Observed address: `DB:BC:F9:44:FC:17`
- Local name: `0203B 17FC44F9BCDB`
- Advertised service: `000078b2-0000-1000-8000-00805f9b34fb`

## Proprietary GATT service

Service: `0x78B2`

| Characteristic | Properties | Current interpretation |
|---|---|---|
| `0x8A20` | Read | Device or session status |
| `0x8A21` | Indicate | Unknown data channel |
| `0x8A22` | Indicate | Unknown data channel |
| `0x8A81` | Write | Likely command channel |
| `0x8A82` | Indicate | Active control or session channel |

## Verified packets

Read from `0x8A20`:

```text
37 FB
```

First indication from `0x8A82`:

```text
84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00
```

The 20-byte length is consistent with a single BLE ATT payload. The meaning is not yet established. It may be a handshake, device state, session announcement, or measurement metadata.

## Working hypotheses

- `0x8A81` is likely used by the official app to request or acknowledge stored measurements.
- `0x8A82` appears to provide an immediate indication after subscriptions are enabled.
- `0x8A21` and `0x8A22` may carry measurement data after a command sequence.
- The scale is designed for wake, connect, synchronize, disconnect rather than a permanent connection.

## Next evidence required

1. Several captures with the actual displayed weight and body metrics recorded beside each session.
2. A capture of the official application writing to `0x8A81`.
3. Repeated sessions to distinguish fixed header bytes from counters, timestamps, identifiers, and measurements.
4. Packet comparison using different known weights or user profiles.

## Evidence rules

Do not assign a field meaning from one packet. A candidate field must vary consistently across multiple labelled captures before it is treated as decoded.
