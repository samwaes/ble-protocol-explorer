# Controlled Home Assistant installation

This integration is still experimental. Install it only for a controlled test and keep the existing Zigbee configuration unchanged.

## Important BS430 behaviour

The BS430 is normally asleep and is not continuously discoverable. Its Bluetooth connection window opens only after a **completed, validated weighing**. Wait until the scale has finished calculating the measurement and the Bluetooth symbol appears. Home Assistant then has only a short period to discover and connect to the scale.

Simply tapping the scale or standing on it briefly may not open a usable synchronization window. Complete the full weighing sequence.

After the integration has been configured, no periodic polling is required. Home Assistant listens for the scale's Bluetooth advertisement and starts synchronization immediately whenever a completed weighing wakes the scale.

## Prerequisites

- Home Assistant with a working connectable Bluetooth adapter or Bluetooth proxy
- Medisana BS430 within Bluetooth range
- VitaDock and other phones disconnected while testing, so they do not claim the short connection window
- File access through HACS, Studio Code Server, Samba, SSH or another supported method

## Install

1. Install or copy the complete folder:

   ```text
   custom_components/medisana_bs430
   ```

   into:

   ```text
   /config/custom_components/medisana_bs430
   ```

2. Confirm that this file exists:

   ```text
   /config/custom_components/medisana_bs430/manifest.json
   ```

3. Restart Home Assistant.

4. Complete a full weighing. Wait until the final values and Bluetooth symbol are shown.

5. Immediately open **Settings → Devices & services → Add integration**.

6. Search for **Medisana BS430** and confirm the discovered scale while it is still awake.

If discovery misses the window, close the setup dialog, complete another full weighing, and try again immediately.

## Normal operation after setup

For each new measurement:

1. Complete a normal validated weighing.
2. Wait for the Bluetooth symbol.
3. Home Assistant detects the advertisement and connects automatically.
4. The integration requests all stored records, updates its entities and disconnects naturally.

You should not need to open the integration or press a button for each weighing. The **Synchronize now** button remains available for diagnostics, but it can only work while the scale is awake.

## First automatic-sync test

1. Confirm that VitaDock is closed and phone Bluetooth is temporarily disabled.
2. Complete a new weighing.
3. Do not open the Medisana integration or press **Synchronize now**.
4. Wait approximately 10 to 20 seconds.
5. Check the weight and body-composition entities in Home Assistant.
6. Check Home Assistant logs or download integration diagnostics if the values do not update.

## Current limitations

- Profile number 1 is still marked as probable rather than formally proven.
- Scale-side target weight and unit settings are not writable yet.
- Historical records are decoded, but persistent backfill into Home Assistant long-term statistics is not implemented yet.
- The integration does not delete or acknowledge measurements on the scale.
- If another phone or application connects first, Home Assistant may miss that synchronization window.

## Rollback

1. Remove the Medisana BS430 integration in **Settings → Devices & services**.
2. Delete `/config/custom_components/medisana_bs430`.
3. Restart Home Assistant.

This integration does not modify ZHA, VirtualBox USB passthrough or the Zigbee adapter.
