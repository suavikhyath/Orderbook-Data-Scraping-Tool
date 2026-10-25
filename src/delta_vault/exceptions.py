class DeltaVaultError(Exception):
    """Base exception for delta_vault."""


class DeltaAPIError(DeltaVaultError):
    """Raised when the Delta Exchange API request fails."""


class DataValidationError(DeltaVaultError):
    """Raised when the returned data is invalid."""