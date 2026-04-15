import asyncio
import logging
import os

from dotenv import load_dotenv
from uagents import Agent, Context
from models import ViolationMessage, EnrichedViolation, EnrichedMessage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Environment variables ────────────────────────────────────────────────────
COMPLIANCE_ADDRESS = os.environ.get(
    "COMPLIANCE_ADDRESS",
    "agent1qgy3ud82pj2sj6dwm8k8eth4pwyzzanc24ske40et2mcd8jyqx3dwkynrnc",
)

request_agent = Agent(
    name="RequestAgent",
    seed=os.environ["REQUEST_AGENT_SEED"],
    port=int(os.environ.get("REQUEST_AGENT_PORT", "8001")),
    endpoint=[os.environ.get("REQUEST_AGENT_ENDPOINT", "http://127.0.0.1:8001/submit")],
)


@request_agent.on_message(model=ViolationMessage)
async def handle_batch(ctx: Context, sender: str, msg: ViolationMessage) -> None:
    ctx.logger.info(
        "[RequestAgent]: Received batch %s-%s from %s",
        msg.frame_start, msg.frame_end, sender,
    )

    enriched_violations = [
        EnrichedViolation(person_id=v.person_id, missing=v.missing)
        for v in msg.violations
    ]
    enriched_msg = EnrichedMessage(
        frame_start=msg.frame_start,
        frame_end=msg.frame_end,
        state=msg.state,
        persons=msg.persons,
        violations=enriched_violations,
    )

    await ctx.send(COMPLIANCE_ADDRESS, enriched_msg)
    ctx.logger.info(
        "[RequestAgent]: Forwarded batch %s-%s to Compliance agent",
        msg.frame_start, msg.frame_end,
    )
    await asyncio.sleep(1)


@request_agent.on_event("startup")
async def startup(ctx: Context) -> None:
    ctx.logger.info("[RequestAgent]: Running at %s", request_agent.address)


if __name__ == "__main__":
    request_agent.run()
