# Architecture

The implementation is now split into reusable layers:

- `models.py`: protocol-neutral measurement data
- `decoder.py`: pure frame decoding and timestamp conversion
- `protocol.py`: UUIDs, epoch and synchronization command
- `synchronizer.py`: timestamp-based frame pairing and de-duplication
- `bluetooth.py`: standalone Bleak transport

The future Home Assistant custom component will depend on this package rather than duplicate protocol logic.

## Confirmed configuration scope

The official scale app exposes:

- Metric, Imperial US and Imperial UK body-weight units
- target weight
- numbered user profiles

Sam's known scale profile is profile 1. Captured byte 13 currently equals 1 and is exposed only as a probable profile candidate until independently confirmed.

Scale-side writes remain disabled until their commands are known. Home Assistant-side profile mapping can be implemented safely without writing to the scale.
