DESCRIPTIONS = {
    400: "Rejected request: unsafe or unsupported input, or the itinerary already exists",
    401: "Missing or invalid token",
    403: "The trip belongs to another user",
    404: "Not found",
    500: "Generation failed; details are logged, never returned",
}


def error_responses(*codes: int) -> dict[int, dict]:
    """The error responses a route can return, for the Swagger page."""
    return {code: {"description": DESCRIPTIONS[code]} for code in codes}
