"""Constants for the Medisana BS430 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "medisana_bs430"
PLATFORMS: Final = ["sensor", "button"]

INTEGRATION_VERSION: Final = "0.4.2"
BUILD_COMMIT: Final = "bc74a3066d701d0cf1d5cc92016b57c814e99716"

CONF_ADDRESS: Final = "address"
CONF_PROFILE_MAP: Final = "profile_map"
CONF_IMPORT_HISTORY: Final = "import_history"
CONF_RETAIN_DIAGNOSTICS: Final = "retain_diagnostics"

DEFAULT_IMPORT_HISTORY: Final = True
DEFAULT_RETAIN_DIAGNOSTICS: Final = True

# Profile decoding is still being validated. Profile 1 is the currently
# confirmed primary user and is the only profile allowed to update sensors.
PRIMARY_PROFILE_ID: Final = 1

MANUFACTURER: Final = "Medisana"
MODEL: Final = "BS430"
