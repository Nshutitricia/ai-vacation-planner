class InputRejectedError(ValueError):
    """User-supplied text was rejected before it could reach an LLM prompt.

    A ValueError on purpose: pydantic turns it into a 422 on the REST routes,
    and the voice route already maps ValueError to a 400.
    """


class OutputGuardError(Exception):
    """The model's output failed validation against the trip it was made for.

    Deliberately not a ValueError: the user did nothing wrong, so routes
    report it as a server-side failure rather than a 400.
    """
