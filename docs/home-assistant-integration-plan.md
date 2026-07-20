# Home Assistant integration plan

## Goal

Build a native, local-only Home Assistant integration for the Medisana BS430 that synchronizes historical measurements and is architected for future scale-side configuration without enabling unverified writes.

## Runtime architecture

```text
Bluetooth discovery
      ↓
Connection/session transport
      ↓
BS430 protocol synchronizer
      ↓
Timestamp-key packet assembler
      ↓
Measurement decoder
      ↓
Duplicate/history store
      ↓
Home Assistant entities and events
```

The protocol layer must remain reusable outside Home Assistant for command-line validation and tests.

## Initial configuration flow

1. Discover devices whose name starts with `0203B` or that advertise service `0x78B2`.
2. Display the detected scale name and Bluetooth identity.
3. Prevent duplicate config entries using a stable unique identifier.
4. Perform a non-destructive connection and synchronization test when the scale is awake.
5. Create the Home Assistant device and default entities.

No VitaDock account, cloud token or BLE PIN is required.

## Options flow

Editable after installation:

- automatic synchronization enabled/disabled;
- historical import enabled/disabled;
- maximum imported record age;
- diagnostics enabled/disabled;
- candidate profile mapping, initially `profile 1 → Sam` when explicitly configured;
- expose probable impedance entity;
- connection timeout and retry policy.

Scale-side unit and target-weight settings must not be presented as writable controls until their GATT commands are confirmed.

## Entities for version 1

Enabled by default:

- weight;
- body fat percentage;
- body water percentage;
- muscle percentage;
- bone mass;
- measurement timestamp;
- last successful synchronization;
- synchronization status;
- synchronize-now button.

Disabled by default or diagnostic:

- probable impedance;
- candidate profile number;
- imported record count;
- pending/incomplete record count;
- raw protocol metadata;
- last status frame.

Derived values such as BMI, BMR or difference to target must be clearly marked as Home Assistant calculations and may only be enabled when the required user data is configured.

## Historical records

The BS430 can return several stored measurements in one session. A normal sensor state is insufficient to represent this history safely.

The integration must:

1. assemble each record by shared timestamp key;
2. sort records chronologically;
3. calculate a stable fingerprint from timestamp and raw packet content;
4. persist seen fingerprints;
5. import only unseen records;
6. fire a Home Assistant event for every newly imported historical record;
7. update current sensor states to the newest complete record.

Equal weights measured at different timestamps are separate records and must never be deduplicated by value alone.

## Profile handling

Known facts:

- the official app uses numbered user profiles;
- the tested user is profile `1`;
- weight-frame byte `13` was consistently `01` in the test capture.

Version 1 behaviour:

- expose byte `13` as `profile_id_candidate` with status `unconfirmed`;
- allow an explicit Home Assistant-side mapping from candidate profile `1` to a person/name;
- leave unknown or unmapped measurements unassigned;
- never assign a person based only on similar weight.

## Confirmed application configuration surface

The official application exposes:

- weight unit: Metric, Imperial US, Imperial UK;
- target weight;
- numbered user profile.

These become a capability backlog:

| Capability | Read | Write | Initial status |
|---|---:|---:|---|
| Measurement history | Yes | N/A | Confirmed |
| Candidate profile number | Probable | No | Diagnostic only |
| Weight unit | Unknown | Unknown | Investigate |
| Target weight | Unknown | Unknown | Investigate |
| Profile configuration | Unknown | Unknown | Investigate |

## Safety rules for scale writes

- Never guess commands in the production integration.
- Verify commands from documentation, an established implementation, or controlled official-app captures.
- Keep target-weight, unit and profile writes disabled until read-back or another confirmation mechanism exists.
- Do not implement erase-history or factory-reset functions without strong evidence, explicit confirmation and safeguards.

## Proposed repository structure

```text
medisana_bs430/
  const.py
  models.py
  decoder.py
  protocol.py
  synchronizer.py
  bluetooth.py

custom_components/medisana_bs430/
  __init__.py
  manifest.json
  config_flow.py
  coordinator.py
  sensor.py
  button.py
  diagnostics.py
  strings.json
  translations/
```

## Immediate implementation step

Refactor the validated standalone reader into the reusable `medisana_bs430` package, add fixture-based tests for the captured four-record session, then scaffold the Home Assistant custom component around that tested package.
