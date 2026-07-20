# Controlled Home Assistant installation

## Release identification

- Integration version: `0.3.1`
- Automatic-trigger code revision: `adea036481198c128973a7a7773fbdbc0d961f02`
- HACS should show version `0.3.1` before installation.
- Home Assistant device information shows `0.3.1 (adea036)` after restart.

This integration is still experimental. Install it only for a controlled test and keep the existing Zigbee configuration unchanged.

## Critical BS430 wake behaviour

The BS430 is not continuously discoverable. Bluetooth becomes available only after a **fully completed and validated weighing**.

The correct sequence is:

1. Stand on the scale and remain still until the measurement is fully completed.
2. Complete profile confirmation on the scale when requested.
3. Wait until the Bluetooth symbol appears on the scale display.
4. Home Assistant must discover and connect during this short Bluetooth window.

Simply tapping or waking the scale without completing a validated measurement may not expose the synchronization service. VitaDock or another phone may claim the connection window before Home Assistant, so disable or disconnect competing Bluetooth clients during testing.

## Prerequisites

- Home Assistant with a working Bluetooth adapter or Bluetooth proxy
- Medisana BS430 within Bluetooth range
- VitaDock and other phones disconnected while testing
- File access through HACS, Studio Code Server, Samba, SSH or another supported method

## Install

1. Install or update **Medisana BS430** through HACS.
2. Confirm HACS shows version `0.3.1`.
3. Restart Home Assistant.
4. Complete a full validated weighing and wait for the Bluetooth symbol.
5. Immediately open **Settings → Devices & services → Add integration**.
6. Search for **Medisana BS430** and confirm the discovered scale.

If discovery misses the window, close the setup dialog, complete another full weighing, and retry immediately.

## Normal operation

After setup, no fixed polling interval is used. A validated weighing produces a Bluetooth advertisement. The integration listens for that advertisement and immediately starts synchronization.

Version `0.3.1` matches the BS430 by its stable local-name prefix and service UUID rather than relying only on the previously stored Bluetooth address. It retries up to three times within the short wake window.

The **Synchronize now** button remains available for diagnostics, but it can only work while the Bluetooth symbol is visible and the scale remains connectable.

## Verification

After updating and restarting:

1. Open the BS430 device page.
2. Check Device information for software version `0.3.1 (adea036)`.
3. Complete a validated weighing.
4. Do not press the button initially.
5. Wait approximately 10–20 seconds and inspect the entities.
6. If it fails, inspect Home Assistant logs for `BS430 wake advertisement received` and `Automatic BS430 synchronization`.

## Current limitations

- Profile number 1 remains probable rather than formally proven.
- Scale-side target weight and unit settings are not writable yet.
- Historical records are decoded, but persistent statistics backfill is not implemented yet.
- The integration does not delete or acknowledge measurements on the scale.
- Another phone or application can claim the short connection window first.

## Rollback

1. Remove the Medisana BS430 integration in **Settings → Devices & services**.
2. Remove it through HACS or delete `/config/custom_components/medisana_bs430`.
3. Restart Home Assistant.

This integration does not modify ZHA, VirtualBox USB passthrough or the Zigbee adapter.
