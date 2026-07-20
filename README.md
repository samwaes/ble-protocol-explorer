# Medisana BS430 Local Integration

A Hupla Labs project focused first on connecting a **Medisana BS430 smart scale** locally to Home Assistant over Bluetooth Low Energy.

The broader BLE exploration toolkit remains a secondary goal. The project will only generalise after the BS430 works end to end.

## Major finding

The BS430 protocol does not need to be reverse engineered from scratch. The open-source **openScale** project has supported the BS430 since 2018 and contains an established implementation matching our observed service, characteristics and device-name prefix.

The local Python reader in this repository independently reimplements those protocol facts. No openScale source code is copied; openScale is GPLv3 and is credited as the upstream protocol reference.

## Current status

- automatic discovery of the scale after weighing
- successful Windows BLE connection
- service `0x78B2` confirmed
- characteristics `0x8A20`, `0x8A21`, `0x8A22`, `0x8A81`, `0x8A82` confirmed
- fixed status frame on `0x8A82` confirmed
- BS430 request command identified
- weight and body-composition packet layouts identified
- source-backed Python reader added
- direct measurement validation still required

## Primary target

```text
Medisana BS430
      ↓ Bluetooth Low Energy
Local BS430 reader and decoder
      ↓ MQTT
Home Assistant
```

Development remains isolated from Home Assistant OS and the existing Zigbee configuration until the standalone reader is stable.

## Work sequence

- [x] Confirm BLE advertisement and synchronization window
- [x] Map proprietary service and characteristics
- [x] Build isolated Windows scanner and logger
- [x] Find an established open-source BS430 implementation
- [x] Identify the `0x8A81` time/request command
- [x] Identify the `0x8A21` weight frame layout
- [x] Identify the `0x8A22` body-composition frame layout
- [ ] Validate decoded values against a real weighing
- [ ] Handle multiple users and duplicate measurements
- [ ] Publish measurements over MQTT
- [ ] Add Home Assistant MQTT discovery
- [ ] Validate unattended operation
- [ ] Generalise the explorer for additional BLE devices

See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for the delivery order and [docs/protocol-bs430.md](docs/protocol-bs430.md) for the protocol.

## Next test on Windows

Requirements:

- Python 3.11 or 3.12
- Windows Bluetooth enabled
- VitaDock and nRF Connect disconnected
- Bluetooth temporarily disabled on phones that may claim the scale

Create the environment once:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run:

```powershell
windows\RUN_BS430_READER.bat
```

Wait for the scanner and complete a normal body-analysis weighing. The reader will:

1. connect to the BS430;
2. enable the three indication channels;
3. send `0x02 + current Unix timestamp little-endian` to `0x8A81`;
4. decode weight from `0x8A21`;
5. decode fat, water, muscle and bone values from `0x8A22`;
6. save raw packets as CSV and the decoded measurement as JSON under `captures/private`.

## Safety and stability

The current development phase does not:

- install code in Home Assistant OS
- modify VirtualBox USB passthrough
- use the Zigbee adapter
- change ZHA
- require a cloud service

## Repository structure

```text
medisana_logger.py                 Original passive BS430 capture tool
tools/medisana_protocol_explorer.py  Manual diagnostic explorer
tools/medisana_bs430_reader.py       Source-backed BS430 reader and decoder
windows/RUN_BS430_READER.bat         Windows validation runner
docs/protocol-bs430.md               Established protocol and evidence
PROJECT_SCOPE.md                      Medisana-first scope and phases
captures/                             Sanitised examples only
requirements.txt                      Python dependencies
```

## Project status

Experimental local integration. Body-composition readings are personal health data and should not be used for medical decisions.
