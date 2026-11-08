from src.evaluation.render import itinerary_to_text, request_to_text
from src.schemas.itinerary_schema import ItinerarySchema


def test_renderers_produce_readable_text():
    itinerary = ItinerarySchema.model_validate({
        "destination": "Rome", "total_days": 1, "estimated_total_cost": "$100",
        "days": [{"day": 1, "theme": "Ancient", "activities": [
            {"name": "Colosseum", "description": "Tour", "estimated_cost": "$25"}]}],
    })
    text = itinerary_to_text(itinerary)
    assert "Day 1: Ancient" in text and "- Colosseum ($25): Tour" in text
    request = request_to_text("Rome", 2, 800, "cultural", "no museums")
    assert "2-day cultural trip to Rome" in request and "no museums" in request
