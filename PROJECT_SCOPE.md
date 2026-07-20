# Project scope

## Primary objective

Connect a Medisana BS430 smart scale directly to Home Assistant without relying on the proprietary Medisana application or cloud.

The first usable release must:

1. Detect the BS430 when it wakes after a completed weighing.
2. Connect during the short Bluetooth Low Energy availability window.
3. Retrieve and decode the latest measurement.
4. Publish the decoded measurement locally for Home Assistant.
5. Avoid destabilising the existing Home Assistant and Zigbee setup during development.

## Current verified facts

- Device: Medisana BS430
- BLE address observed during testing: `DB:BC:F9:44:FC:17`
- Advertised local name: `0203B 17FC44F9BCDB`
- Proprietary service: `0x78B2`
- Characteristics:
  - `0x8A20`: read
  - `0x8A21`: indicate
  - `0x8A22`: indicate
  - `0x8A81`: write
  - `0x8A82`: indicate
- Confirmed read from `0x8A20`: `37 FB`
- Confirmed indication from `0x8A82`:
  - `84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00`

## Delivery order

### Phase 1: BS430 protocol discovery

- Reliable wake, scan, connect and capture loop
- Record all GATT indications
- Identify required writes to `0x8A81`
- Document packet structure
- Decode weight and available body-composition metrics

### Phase 2: Home Assistant bridge

- Publish measurements over MQTT first
- Add Home Assistant MQTT discovery
- Validate reliability across repeated weighings
- Keep the bridge separate from Home Assistant OS during initial testing

### Phase 3: Productisation

- Configurable device profiles
- Windows and Linux support
- Structured packet recordings
- Automated tests using captured sessions
- Installation and troubleshooting documentation

### Phase 4: Broader BLE explorer

Only after the BS430 path works end to end:

- Generic GATT explorer
- Reusable command console
- Packet comparison and diff tooling
- Pluggable decoders for other BLE devices
- Optional native Home Assistant integration

## Non-goals for the first release

- A generic BLE reverse-engineering platform before BS430 decoding works
- Installing experimental Python packages inside Home Assistant OS
- Sharing the Zigbee USB adapter
- Permanent BLE connections to the scale
- Cloud dependency
