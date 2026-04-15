import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context
from models import ViolationMessage, Violation, MissingItem

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.resolve()
SAMPLE_BATCHES_FILE = BASE_DIR / "sample_batches.txt"

# ── Load sample batches using JSON (not ast.literal_eval) ────────────────────
sample_batches = []
if not SAMPLE_BATCHES_FILE.exists():
    logger.warning("Sample batches file not found: %s", SAMPLE_BATCHES_FILE)
else:
    with open(SAMPLE_BATCHES_FILE, "r", encoding="utf-8") as _fh:
        for _lineno, _line in enumerate(_fh, start=1):
            _line = _line.strip()
            if not _line:
                continue
            try:
                sample_batches.append(json.loads(_line))
            except json.JSONDecodeError as _exc:
                logger.warning(
                    "Skipping invalid JSON on line %d of %s: %s",
                    _lineno, SAMPLE_BATCHES_FILE, _exc,
                )

# ── Environment variables ────────────────────────────────────────────────────
REQUEST_AGENT_ADDRESS = os.environ.get(
    "REQUEST_AGENT_ADDRESS",
    "agent1qtzku6e8zjf2a8dtwdc39slkj6gztrx2e2gu0fnf8aqnqaeptqa5vmc60sj",
)

client_agent = Agent(
    name="ClientSimulator",
    seed=os.environ["CLIENT_AGENT_SEED"],
    port=int(os.environ.get("CLIENT_AGENT_PORT", "8003")),
)


async def send_batches(ctx: Context) -> None:
    for batch in sample_batches:
        violations = [
            Violation(
                person_id=batch.get("persons", 0),
                missing=[MissingItem(item=item) for item in v["missing"].keys()]
            )
            for v in batch["violations"]
        ]
        msg = ViolationMessage(
            frame_start=batch["frame_start"],
            frame_end=batch["frame_end"],
            state=batch["state"],
            persons=batch.get("persons", len(violations)),
            violations=violations,
        )
        ctx.logger.info(
            "[ClientSimulator] Sending batch: frames %s-%s",
            msg.frame_start, msg.frame_end,
        )
        await ctx.send(REQUEST_AGENT_ADDRESS, msg)
        await asyncio.sleep(2)


@client_agent.on_event("startup")
async def startup(ctx: Context) -> None:
    ctx.logger.info("[ClientSimulator] Running at %s", client_agent.address)
    asyncio.create_task(send_batches(ctx))


if __name__ == "__main__":
    client_agent.run()
