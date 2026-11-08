"""Run the real agent on the golden dataset and save what it produced.

Generating is the slow, expensive part, so it is done once and saved. The
judging step (pytest -m eval) then reads the saved file, and you can re-run
the judges as often as you like without paying to regenerate.

    python scripts/generate_eval_outputs.py                 # all itinerary cases
    python scripts/generate_eval_outputs.py rome            # only ids containing "rome"
    python scripts/generate_eval_outputs.py --pause 0       # no waiting between cases

By default it waits between cases. Voyage's free tier allows 3 searches a
minute, and each itinerary makes about 2, so going faster just hits the limit.
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from src.database import engine
from src.models.trip import Trip, TripCreate
from src.observability.usage import track_usage
from src.services.itinerary_service import ItineraryService
from tests.evals.dataset import load_golden_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("generate_eval_outputs")

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "tests" / "evals" / "results" / "outputs.json"


def generate_one(service: ItineraryService, case, session: Session) -> dict:
    trip_data = TripCreate(**case.trip)
    # Not saved to the database: the trip only carries the values to the agent.
    trip = Trip(**trip_data.model_dump(), user_id=0)
    request = service._build_user_request(trip, case.preferences)

    started = time.time()
    with track_usage() as usage:
        try:
            itinerary = service._run_validated_agent(request, trip, session)
            result = {"ok": True, "error": None, "itinerary": itinerary.model_dump()}
        except Exception as e:  # a failed generation is itself a result worth recording
            logger.exception(f"Generation failed for {case.id}")
            result = {"ok": False, "error": f"{type(e).__name__}: {e}", "itinerary": None}
    return {"id": case.id, **result, "seconds": round(time.time() - started, 1), "usage": usage.as_dict()}


def log_usage_summary(results: list[dict]) -> None:
    tokens = sum(r["usage"]["total_tokens"] for r in results)
    costs = [r["usage"]["estimated_cost_usd"] for r in results if r["usage"]["estimated_cost_usd"] is not None]
    generated = [r for r in results if r["ok"]]
    logger.info(f"Total tokens: {tokens:,} across {len(results)} case(s)")
    if costs and generated:
        logger.info(f"Estimated cost: ${sum(costs):.4f} in total, ${sum(costs) / len(generated):.4f} per generated itinerary")
    else:
        logger.info("Estimated cost: n/a (model not in the price table, or nothing generated)")


def main(name_filter: str | None, pause: float) -> None:
    cases = [c for c in load_golden_dataset() if c.expected.outcome == "itinerary"]
    if name_filter:
        cases = [c for c in cases if name_filter in c.id]
    if not cases:
        sys.exit("No matching cases.")

    service = ItineraryService()
    results = []
    with Session(engine) as session:
        for i, case in enumerate(cases, 1):
            if i > 1 and pause:
                logger.info(f"Waiting {pause:g}s to stay under the search rate limit")
                time.sleep(pause)
            logger.info(f"[{i}/{len(cases)}] {case.id}")
            results.append(generate_one(service, case, session))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = sum(r["ok"] for r in results)
    logger.info(f"Saved {len(results)} result(s) to {OUTPUT_PATH} ({ok} generated, {len(results) - ok} failed)")
    log_usage_summary(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name_filter", nargs="?", help="only run cases whose id contains this text")
    parser.add_argument("--pause", type=float, default=45, help="seconds to wait between cases (default 45)")
    args = parser.parse_args()
    main(args.name_filter, args.pause)
