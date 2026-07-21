# Home Assistant installation

## Release identification

- Integration version: `0.5.0`
- Multi-profile implementation revision: `940a667548c67d580e1fd4c90499259dc1bf622a`
- Supported scale profiles: `1` through `8`

## Critical BS430 wake behaviour

The BS430 is not continuously discoverable. Bluetooth becomes available only after a fully completed and validated weighing.

1. Select or confirm the intended profile on the scale.
2. Stand still until the measurement is complete.
3. Wait for the Bluetooth symbol.
4. Home Assistant detects the advertisement and synchronizes during the short wake window.

Keep VitaDock and other competing Bluetooth clients disconnected during testing.

## Install or update

1. Install or update **Medisana BS430** through HACS.
2. Confirm that HACS shows version `0.5.0`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Medisana BS430**.
5. Complete one weighing to verify automatic synchronization.

## Link profiles to people

Open the integration and choose **Configure**.

The options form contains profile slots 1 through 8. Enter a person name for every profile that is in use.

- Profile 1 remains available even when no name is entered, preserving the existing entity IDs and Home Assistant history.
- Profiles 2 through 8 receive entities after a person name is configured.
- Saving the profile names reloads the integration automatically.
- Entity names include the configured person name, for example `Lieve Weight` or `Sam Body fat`.
- The numeric profile ID and configured profile name are also included as entity attributes.

Leaving an additional profile name blank avoids creating unused entities.

## Multi-profile behaviour

The scale returns the stored history for the profile currently active during the weighing. Version `0.5.0` routes valid profile IDs 1 through 8 to separate entity sets.

Measurements with a missing or out-of-range profile ID are quarantined and cannot overwrite a person's sensors. Diagnostics list observed profile IDs and configured profile names but omit body-composition values and raw frame contents.

## Normal operation

No fixed polling interval is used. A validated weighing produces a Bluetooth advertisement and starts synchronization automatically. The **Synchronize now** button remains available as a fallback while the Bluetooth symbol is visible.

## Verification

1. Configure a name for profile 2.
2. Complete a profile-2 weighing.
3. Wait approximately 10–20 seconds.
4. Confirm that only the profile-2 entities update.
5. Repeat with profile 1 and confirm that the original entities update.
6. Download diagnostics when profile routing needs to be verified.

## Current limitations

- Scale-side profile names are not changed; the mapping exists only in Home Assistant.
- Target weight and unit settings are not writable.
- Persistent statistics backfill is not implemented.
- Recent scale timestamps can currently decode with an incorrect year offset and remain under investigation.
- Another phone or application can claim the short Bluetooth connection window first.

## Rollback

1. Remove the Medisana BS430 integration in **Settings → Devices & services**.
2. Remove it through HACS or delete `/config/custom_components/medisana_bs430`.
3. Restart Home Assistant.

The integration does not modify ZHA, VirtualBox USB passthrough or the Zigbee adapter.
