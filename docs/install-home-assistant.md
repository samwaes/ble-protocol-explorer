# Home Assistant installation

## Release identification

- Integration version: `0.6.0`
- Supported scale profiles: `1` through `8`
- Historical recovery: enabled by default
- Minimum Home Assistant version in HACS metadata: `2026.6.0`

## Critical BS430 wake behaviour

The BS430 is not continuously discoverable. Bluetooth becomes available only after a fully completed and validated weighing.

1. Select or confirm the intended profile on the scale.
2. Stand still until the measurement is complete.
3. Wait for the Bluetooth symbol.
4. Home Assistant detects the advertisement and synchronizes during the short wake window.

Keep VitaDock and other competing Bluetooth clients disconnected during testing because another client can claim the short connection window first.

## Install or update

1. Open **HACS → Integrations → Medisana BS430**.
2. Update or redownload the integration so the installed version is `0.6.0`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Medisana BS430**.
5. Complete one normal weighing and let the scale finish its Bluetooth cycle.

For an existing installation, the historical recovery option defaults to enabled even when that option did not exist in the previous config entry.

## Profiles and history recovery

Open the integration and choose **Configure**.

The options form contains:

- **Recover stored measurement history**;
- profile slots 1 through 8.

Profile 1 preserves the existing entity IDs. Profiles 2 through 8 receive entities after a person name is configured. Saving the options reloads the integration automatically.

## How historical recovery works

A scale synchronization can return multiple stored measurements. Version `0.6.0` uses those records for two purposes:

1. the latest valid record for each profile updates the normal Home Assistant sensor entities;
2. the recovered records rebuild hourly long-term statistics through Home Assistant's recorder statistics API.

The backfill is duplicate-safe at hourly resolution. If the same recovered hour is imported again, Home Assistant updates the existing statistic instead of creating another row.

No direct SQLite or recorder-database modification is performed.

### Hourly resolution

Home Assistant's supported long-term statistics import interface requires timestamps on the top of the hour. The integration therefore reconstructs hourly mean, minimum and maximum values.

Between recovered weigh-ins, the last recovered value is carried forward. This matches the normal behaviour of a Home Assistant measurement sensor, whose state remains unchanged until the next measurement.

This repairs long-term trends after an outage. It does not create exact historical state-change events at the original minute and second.

## Mixed timestamp handling

Captured BS430 history has now shown two encodings on the same physical device:

- Unix seconds;
- seconds since `2010-01-01T00:00:00Z`.

Version `0.6.0` evaluates both candidates and selects the plausible interpretation nearest the current time. This prevents Unix records from being shifted approximately 40 years into the future while keeping older legacy records valid.

The synchronization command itself remains on Unix time. No new speculative write command is sent to the scale.

## Verification after update

After the first complete weighing following the update:

1. Wait until the scale powers off.
2. Confirm that the current weight sensor updated.
3. Open **History** and inspect a period that includes the Bluetooth outage.
4. Download diagnostics from the Medisana BS430 integration.
5. Check:
   - `release.integration_version` is `0.6.0`;
   - `profiles.observations[*].timestamp_epoch` is `unix` or `medisana_2010`;
   - timestamps are in a plausible current year;
   - `history_backfill.enabled` is `true`;
   - `history_backfill.statistics_imported` is greater than zero when stored history was available;
   - `history_backfill.error` is absent.

## Current limitations

- The amount of recoverable history is limited by the scale's own memory and overwrite behaviour.
- Historical recovery repairs Home Assistant long-term statistics, not raw second-level recorder state history.
- If several weigh-ins occur within one hour, that hour stores their arithmetic mean, minimum and maximum in long-term statistics.
- Scale-side profile names are not changed. The name mapping exists only in Home Assistant.
- Target weight and unit settings are not writable.
- Impedance decoding remains probable rather than independently confirmed.
- Another phone or application can claim the short Bluetooth connection window first.

## Rollback

1. In HACS, reinstall the previous known-good release or remove Medisana BS430.
2. Restart Home Assistant.

Removing the integration does not alter ZHA, the Zigbee adapter or unrelated Home Assistant integrations. Long-term statistics already imported into the recorder are not automatically deleted by removing the integration.
