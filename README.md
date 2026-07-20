# BLE Protocol Explorer

A Hupla Labs project focused first on connecting a **Medisana BS430 smart scale** directly to Home Assistant over Bluetooth Low Energy.

The broader BLE exploration toolkit is a secondary goal. The project will only generalise after the BS430 works end to end.

## Current status

The first Windows-based BLE capture succeeded:

- automatic discovery of the scale after weighing
- successful BLE connection
- proprietary service and characteristics discovered
- indications enabled on `0x8A21`, `0x8A22`, and `0x8A82`
- read from `0x8A20`: `37 FB`
- first 20-byte packet received on `0x8A82`

```text
84 53 01 80 01 2D B4 E0 00 00 00 00 00 00 00 00 00 00 00 00
```

## Primary target

```text
Medisana BS430
      ↓ Bluetooth Low Energy
Local capture and decoder
      ↓ MQTT
Home Assistant
```

The development setup remains isolated from Home Assistant OS and the existing Zigbee configuration until the BLE protocol is understood and the bridge is stable.

## Work sequence

- [x] Confirm the scale advertises over BLE
- [x] Identify service `0x78B2`
- [x] Identify characteristics `0x8A20`, `0x8A21`, `0x8A22`, `0x8A81`, `0x8A82`
- [x] Build isolated Windows scanner and logger
- [x] Receive first proprietary indication
- [ ] Capture several labelled weighing sessions
- [ ] Identify the command flow on `0x8A81`
- [ ] Decode weight
- [ ] Decode body-composition metrics where available
- [ ] Publish measurements over MQTT
- [ ] Add Home Assistant MQTT discovery
- [ ] Validate unattended operation
- [ ] Generalise the explorer for additional BLE devices

See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for the delivery order and boundaries.

## Quick start on Windows

Requirements:

- Python 3.11 or 3.12
- Windows Bluetooth enabled
- Medisana and nRF Connect apps disconnected from the scale

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe medisana_logger.py
```

Start the logger before weighing. The scale appears only during its short synchronization window after a completed measurement.

Stop with `Ctrl+C`. A timestamped log file is written in the project folder.

## Safety and stability

The first development phase does not:

- install code in Home Assistant OS
- modify VirtualBox USB passthrough
- use the Zigbee adapter
- change ZHA
- require a cloud service

## Repository structure

```text
medisana_logger.py       Current BS430 capture tool
PROJECT_SCOPE.md         Medisana-first scope and phases
docs/protocol-bs430.md   Verified protocol observations
captures/                Sanitised example captures
requirements.txt         Python dependencies
```

## Project status

Experimental reverse engineering. The packet meanings are not yet fully decoded. Do not use the current output for medical decisions.
