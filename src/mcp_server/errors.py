class ProviderUnavailableError(Exception):
    """An upstream provider (weather, maps) failed or returned unusable data.

    Raised instead of returning a friendly string so the MCP layer reports a
    real tool error, and the agent can tell "no match" apart from "service down".
    """
