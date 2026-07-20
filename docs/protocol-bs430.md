# Medisana BS430 BLE protocol

## Status

The core BS430 protocol is already implemented in the open-source **openScale** project. Our own captures match that implementation exactly, so blind protocol reverse engineering is no longer required.

This repository independently reimplements the protocol behaviour in Python. No openScale source code is copied. openScale is licensed under GPLv3 and remains the primary upstream reference.

## Verified device behaviour

The scale is not continuously connectable. A completed weighing wakes the BLE interface and creates a short synchronization window. A client must scan, stop scanning once the device is found, connect quickly, enable indications, request the stored measurement, and tolerate the scale powering down.

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
| `0x8A21` | Indicate | Weight and measurement timestamp |
| `0x8A22` | Indicate | Body-composition values |
| `0x8A81` | Write | Time/request command |
| `0x8A82` | Indicate | Optional status/session frame; ignored by openScale |

## Session sequence

1. Detect the scale after a completed weighing.
2. Stop BLE scanning before connecting.
3. Connect to the scale.
4. Enable indications in this order:
   - `0x8A22`
   - `0x8A21`
   - `0x8A82`
5. Write the request command to `0x8A81` with a GATT response:

```text
02 <current Unix timestamp as uint32 little-endian>
```

The BS430 uses the normal Unix epoch. Older BS440/BS444 variants use seconds since `2010-01-01` instead.

## Weight frame: `0x8A21`

Minimum length: 9 bytes.

| Bytes | Encoding | Meaning |
|---|---|---|
| `1..2` | unsigned 16-bit little-endian | Weight in kilograms multiplied by 100 |
| `5..8` | unsigned 32-bit little-endian | Unix timestamp in seconds for BS430 |

Example decoding:

```text
weight_kg = uint16_le(frame[1:3]) / 100
measurement_time = uint32_le(frame[5:9])
```

## Feature frame: `0x8A22`

Minimum length: 16 bytes.

| Bytes | Meaning |
|---|---|
| `8..9` | Body fat percentage |
| `10..11` | Body water percentage |
| `12..13` | Muscle percentage |
| `14..15` | Bone mass in kilograms |

Each value is decoded as:

```text
value = (uint16_le(bytes) & 0x0FFF) / 10
```

The raw frame may contain other fields, but they are not yet treated as confirmed in this project.

## Observed status frame: `0x8A82`

Our two initial captures produced the same 20-byte frame:

```text
84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00
```

This frame did not vary with weight and is not used by the established openScale driver. It is therefore treated as session/status data rather than a measurement.

## Upstream evidence

- openScale added explicit BS430 support in December 2018.
- Device names beginning with `0203B` select the BS430 variant.
- The openScale driver uses the same service and four measurement/command characteristics observed in our captures.
- The current openScale handler still implements the same time command and packet layout.

## Next validation

The next test is no longer exploratory. It is a direct protocol validation:

1. Run `tools/medisana_bs430_reader.py`.
2. Complete a body-analysis weighing.
3. Verify that `0x8A21` and `0x8A22` arrive after the time/request command.
4. Compare decoded weight, fat, water, muscle and bone values with the scale display or VitaDock result.
5. Only investigate remaining fields if the confirmed values do not match.
