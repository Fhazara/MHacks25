import asyncio
from uagents import Agent, Context
from models import ViolationMessage, EnrichedViolation, EnrichedMessage

COMPLIANCE_ADDRESS = "agent1qgy3ud82pj2sj6dwm8k8eth4pwyzzanc24ske40et2mcd8jyqx3dwkynrnc"

request_agent = Agent(
    name="RequestAgent",
    seed="REDACTED_REQUEST_SEED",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"]
)

# Handle a single ViolationMessage at a time
@request_agent.on_message(model=ViolationMessage)
async def handle_batch(ctx: Context, sender: str, msg: ViolationMessage):
    ctx.logger.info(f"[RequestAgent]: Received batch {msg.frame_start}-{msg.frame_end} from {sender}")

    enriched_violations = [
        EnrichedViolation(
            person_id=v.person_id,
            missing=v.missing
        )
        for v in msg.violations
    ]

    enriched_msg = EnrichedMessage(
        frame_start=msg.frame_start,
        frame_end=msg.frame_end,
        state=msg.state,
        persons=msg.persons,
        violations=enriched_violations
    )

    await ctx.send(COMPLIANCE_ADDRESS, enriched_msg)
    ctx.logger.info(f"[RequestAgent]: Forwarded batch {msg.frame_start}-{msg.frame_end} to Compliance agent")
    await asyncio.sleep(1)

@request_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[RequestAgent]: Running at {request_agent.address}")

if __name__ == "__main__":
    request_agent.run()
