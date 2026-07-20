# Controlled Home Assistant installation

This integration is still experimental. Install it only for a controlled test and keep the existing Zigbee configuration unchanged.

## Prerequisites

- Home Assistant with a working Bluetooth adapter or Bluetooth proxy
- Medisana BS430 visible to Home Assistant after a weighing
- VitaDock and other phones disconnected while testing
- File access through Studio Code Server, Samba, SSH or another supported method

## Install

1. Copy the complete folder:

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

4. Open **Settings → Devices & services → Add integration**.

5. Search for **Medisana BS430**.

6. Wake the scale by completing a normal weighing. Bluetooth discovery is only available for a short period.

7. Confirm the discovered scale.

## First test

After setup:

1. Wake the scale with a normal weighing.
2. Press **Synchronize now**.
3. Wait for the scale to disconnect naturally.
4. Check the weight and body-composition sensors.
5. Download integration diagnostics if values or timestamps are incorrect.

## Current limitations

- Profile number 1 is still marked as probable rather than formally proven.
- Scale-side target weight and unit settings are not writable yet.
- Historical records are returned by the decoder, but persistent backfill into Home Assistant statistics is not implemented yet.
- The integration does not delete or acknowledge measurements on the scale.
- Automatic scheduled synchronization is not enabled in the first controlled release.

## Rollback

1. Remove the Medisana BS430 integration in **Settings → Devices & services**.
2. Delete `/config/custom_components/medisana_bs430`.
3. Restart Home Assistant.

This integration does not modify ZHA, VirtualBox USB passthrough or the Zigbee adapter.
