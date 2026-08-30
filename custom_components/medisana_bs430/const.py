"""Constants for the Medisana BS430 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "medisana_bs430"
PLATFORMS: Final = ["sensor", "button"]

INTEGRATION_VERSION: Final = "0.6.0"
BUILD_COMMIT: Final = "4d2c89bc7cbf3caa6ba5ccb565b2d181b1d69423"

CONF_ADDRESS: Final = "address"
CONF_PROFILE_MAP: Final = "profile_map"
CONF_IMPORT_HISTORY: Final = "import_history"
CONF_RETAIN_DIAGNOSTICS: Final = "retain_diagnostics"

DEFAULT_IMPORT_HISTORY: Final = True
DEFAULT_RETAIN_DIAGNOSTICS: Final = True

PRIMARY_PROFILE_ID: Final = 1
MIN_PROFILE_ID: Final = 1
MAX_PROFILE_ID: Final = 8
PROFILE_NAME_KEY_PREFIX: Final = "profile_name_"

MANUFACTURER: Final = "Medisana"
MODEL: Final = "BS430"
