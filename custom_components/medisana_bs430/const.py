"""Constants for the Medisana BS430 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "medisana_bs430"
PLATFORMS: Final = ["sensor", "button"]

INTEGRATION_VERSION: Final = "0.3.1"
BUILD_COMMIT: Final = "pending"

CONF_ADDRESS: Final = "address"
CONF_PROFILE_MAP: Final = "profile_map"
CONF_IMPORT_HISTORY: Final = "import_history"
CONF_RETAIN_DIAGNOSTICS: Final = "retain_diagnostics"

DEFAULT_IMPORT_HISTORY: Final = True
DEFAULT_RETAIN_DIAGNOSTICS: Final = True

MANUFACTURER: Final = "Medisana"
MODEL: Final = "BS430"
