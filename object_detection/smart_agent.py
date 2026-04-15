import json
import logging
import os
import time
from pathlib import Path
from typing import Dict

import httpx
from dotenv import load_dotenv
from uagents import Agent, Context
from models import EnrichedMessage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Environment variables (all required) ─────────────────────────────────────
_MISSING = object()

def _require_env(name: str) -> str:
    value = os.environ.get(name, _MISSING)
    if value is _MISSING:
        raise RuntimeError(f"Required environment variable '{name}' is not set.")
    return value  # type: ignore[return-value]

DISCORD_WEBHOOK_URL = _require_env("DISCORD_WEBHOOK_URL")
COMPLIANCE_AGENT_SEED = _require_env("COMPLIANCE_AGENT_SEED")
COMPLIANCE_AGENT_PORT = int(os.environ.get("COMPLIANCE_AGENT_PORT", "8000"))
COMPLIANCE_AGENT_ENDPOINT = os.environ.get(
    "COMPLIANCE_AGENT_ENDPOINT", "http://127.0.0.1:8000/submit"
)

# ── Initialize Compliance Agent ───────────────────────────────────────────────
compliance_agent = Agent(
    name="Compliance",
    seed=COMPLIANCE_AGENT_SEED,
    port=COMPLIANCE_AGENT_PORT,
    endpoint=[COMPLIANCE_AGENT_ENDPOINT],
)

# ── OSHA rules ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
RULES_FILE = BASE_DIR / "osha.json"

# Allowlist of states present in osha.json
VALID_STATES: frozenset = frozenset({"Michigan", "California"})


def load_rules() -> Dict:
    if not RULES_FILE.exists():
        logger.error("Rules file not found: %s", RULES_FILE)
        return {}
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in rules file %s: %s", RULES_FILE, exc)
        return {}
    except OSError as exc:
        logger.error("Cannot read rules file %s: %s", RULES_FILE, exc)
        return {}


rules_data = load_rules()


def lookup_rule(state: str, hazard: str) -> Dict[str, str]:
    """Return OSHA rule/consequence for (state, hazard).

    Raises ValueError for invalid inputs; returns 'Unknown' when not found.
    """
    if not state or not isinstance(state, str):
        raise ValueError(f"Invalid state argument: {state!r}")
    if not hazard or not isinstance(hazard, str):
        raise ValueError(f"Invalid hazard argument: {hazard!r}")
    if state not in VALID_STATES:
        logger.warning("Received unknown state %r — returning Unknown rule", state)
        return {"rule": "Unknown", "consequence": "Unknown"}

    hazard_key = hazard.strip().lower()
    state_rules = rules_data.get(state, {})
    mapping = {k.lower(): v for k, v in state_rules.items()}
    info = mapping.get(hazard_key, {})
    return {
        "rule": info.get("rule", "Unknown"),
        "consequence": info.get("consequence", "Unknown"),
    }


# ── Discord webhook with rate-limiting ───────────────────────────────────────
# Discord allows up to 30 requests/minute per webhook; enforce at most 1 per 3 s.
_DISCORD_MIN_INTERVAL = float(os.environ.get("DISCORD_MIN_INTERVAL_SECONDS", "3.0"))
_discord_last_sent: float = 0.0


async def send_discord_alert(message: str) -> None:
    import asyncio
    global _discord_last_sent

    elapsed = time.monotonic() - _discord_last_sent
    if elapsed < _DISCORD_MIN_INTERVAL:
        wait = _DISCORD_MIN_INTERVAL - elapsed
        logger.debug("Discord rate-limit: waiting %.1f s before next alert", wait)
        await asyncio.sleep(wait)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DISCORD_WEBHOOK_URL,
                json={"content": message},
                timeout=10.0,
            )
            response.raise_for_status()
        _discord_last_sent = time.monotonic()
        logger.info("Discord alert sent successfully")
    except httpx.TimeoutException:
        logger.error("Timeout sending Discord alert")
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Discord webhook returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
    except httpx.HTTPError as exc:
        logger.error("HTTP error sending Discord alert: %s", exc)


# ── Alert builder ─────────────────────────────────────────────────────────────
def build_alert(msg: EnrichedMessage) -> str:
    header = (
        f"⚠️ Compliance Alert\n"
        f"Frames {msg.frame_start} → {msg.frame_end}\n"
        f"{msg.persons} persons detected with violations in {msg.state}\n\n"
    )
    body_lines = []
    for v in msg.violations:
        for m in v.missing:
            hazard = m.item
            try:
                rule_info = lookup_rule(msg.state, hazard)
            except ValueError as exc:
                logger.warning("lookup_rule error: %s", exc)
                rule_info = {"rule": "Unknown", "consequence": "Unknown"}
            body_lines.append(
                f"👤 Person {v.person_id}: Missing {hazard}\n"
                f"   Rule: {rule_info['rule']}\n"
                f"   Consequence: {rule_info['consequence']}\n"
            )
    return header + "\n".join(body_lines)


# ── Message handler ───────────────────────────────────────────────────────────
@compliance_agent.on_message(model=EnrichedMessage)
async def handle_enriched(ctx: Context, sender: str, msg: EnrichedMessage) -> None:
    ctx.logger.info("[Compliance]: Received EnrichedMessage from %s", sender)
    alert = build_alert(msg)
    await send_discord_alert(alert)


# ── Startup ───────────────────────────────────────────────────────────────────
@compliance_agent.on_event("startup")
async def startup(ctx: Context) -> None:
    ctx.logger.info("[Compliance]: Running at %s", compliance_agent.address)


if __name__ == "__main__":
    compliance_agent.run()
