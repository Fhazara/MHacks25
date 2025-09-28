import json
import httpx
from typing import Dict
from uagents import Agent, Context
from models import EnrichedMessage   # RequestAgent now sends EnrichedMessage

# ------------------------
# Initialize Compliance Agent
# ------------------------
compliance_agent = Agent(
    name="Compliance",
    seed="REDACTED_COMPLIANCE_SEED",
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"],
)

# ------------------------
# Load OSHA rules
# ------------------------
RULES_FILE = "osha.json"

def load_rules() -> Dict:
    try:
        with open(RULES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {RULES_FILE}: {e}")
        return {}

rules_data = load_rules()

def lookup_rule(state: str, hazard: str) -> Dict[str, str]:
    """
    Find the OSHA rule and consequence for a given state and hazard.
    Case-insensitive lookup; returns 'Unknown' if not found.
    """
    hazard_key = (hazard or "").strip().lower()
    state_rules = rules_data.get(state, {})
    mapping = {k.lower(): v for k, v in state_rules.items()}
    info = mapping.get(hazard_key, {})
    return {
        "rule": info.get("rule", "Unknown"),
        "consequence": info.get("consequence", "Unknown"),
    }

# ------------------------
# Discord Webhook
# ------------------------
DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/REDACTED_WEBHOOK_ID/"
    "REDACTED_WEBHOOK_TOKEN"
)  # replace for production

async def send_discord_alert(message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10.0)
        except Exception as e:
            print(f"Error sending Discord alert: {e}")

# ------------------------
# Build and Send Alert
# ------------------------
def build_alert(msg: EnrichedMessage) -> str:
    """
    Take the EnrichedMessage, look up rule/consequence for each missing item,
    and build a nicely formatted alert string.
    """
    header = (
        f"⚠️ Compliance Alert\n"
        f"Frames {msg.frame_start} → {msg.frame_end}\n"
        f"{msg.persons} persons detected with violations in {msg.state}\n\n"
    )

    body_lines = []
    for v in msg.violations:
        for m in v.missing:
            # m is MissingItem; fetch OSHA info
            hazard = m.item
            rule_info = lookup_rule(msg.state, hazard)
            body_lines.append(
                f"👤 Person {v.person_id}: Missing {hazard}\n"
                f"   Rule: {rule_info['rule']}\n"
                f"   Consequence: {rule_info['consequence']}\n"
            )

    return header + "\n".join(body_lines)

# ------------------------
# Message Handler
# ------------------------
@compliance_agent.on_message(model=EnrichedMessage)
async def handle_enriched(ctx: Context, sender: str, msg: EnrichedMessage):
    ctx.logger.info(f"[Compliance]: Received EnrichedMessage from {sender}")
    alert = build_alert(msg)
    await send_discord_alert(alert)

# ------------------------
# Startup
# ------------------------
@compliance_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[Compliance]: Running at {compliance_agent.address}")

# ------------------------
# Run
# ------------------------
if __name__ == "__main__":
    compliance_agent.run()
