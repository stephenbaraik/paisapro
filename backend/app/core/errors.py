"""Application exception hierarchy."""


class AppError(Exception):
    """Base exception for all application errors."""


class DataNotFoundError(AppError):
    """Requested data does not exist in any data source."""


class ExternalAPIError(AppError):
    """An external API (yfinance, Groq, Supabase) returned an error."""


class ComputationError(AppError):
    """An ML model or financial calculation failed."""
