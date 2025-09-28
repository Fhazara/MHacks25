# Initialize sample_batches from sample_batches.txt
import ast
sample_batches = []
with open("sample_batches.txt", "r") as f:
    for line in f:
        try:
            sample_batches.append(ast.literal_eval(line.strip()))
        except Exception as e:
            print(f"Could not parse line: {line.strip()}\nError: {e}")
import asyncio      
from uagents import Agent, Context
from models import ViolationMessage, Violation, MissingItem

REQUEST_AGENT_ADDRESS = "agent1qtzku6e8zjf2a8dtwdc39slkj6gztrx2e2gu0fnf8aqnqaeptqa5vmc60sj"

client_agent = Agent(
    name="ClientSimulator",
    seed="REDACTED_CLIENT_SEED",
    port=8003
)

async def send_batches(ctx: Context):
    while True:
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
                violations=violations
            )
            ctx.logger.info(f"[ClientSimulator] Sending batch: {batch}")
            await ctx.send(REQUEST_AGENT_ADDRESS, msg)
            await asyncio.sleep(2)

@client_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[ClientSimulator] Running at {client_agent.address}")
    asyncio.create_task(send_batches(ctx))

#    from agent_connector import send_report_to_agentverse

if __name__ == "__main__":
    client_agent.run()

