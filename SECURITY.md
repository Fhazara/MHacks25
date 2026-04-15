# Security Policy

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.  
Email the maintainers directly and allow up to 72 hours for an initial response.

---

## Security Fixes Applied (April 2025)

A full audit was performed after credentials were identified in the repository
history. The following issues were remediated and the Git history was rewritten
to remove all exposed secrets.

---

### CRITICAL — Hardcoded Discord Webhook Token ✅ Fixed

**Was:** The Discord webhook URL, including its secret token, was committed
verbatim in `object_detection/smart_agent.py`.

**Fix:**
- The webhook was **immediately revoked** in Discord (Server Settings →
  Integrations → Webhooks).
- A new webhook must be created and supplied via the `DISCORD_WEBHOOK_URL`
  environment variable.
- Git history was rewritten with `git-filter-repo` to remove the token from
  every commit.

---

### CRITICAL — Hardcoded Agent Seed Phrases ✅ Fixed

**Was:** Three cryptographic seed phrases were committed in plain text across
`smart_agent.py`, `continuous_request.py`, and `agent_connector.py`.

**Fix:**
- All seeds moved to environment variables:
  `COMPLIANCE_AGENT_SEED`, `REQUEST_AGENT_SEED`, `CLIENT_AGENT_SEED`.
- Generate strong seeds with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- Git history was rewritten to remove old seeds from every commit.

---

### HIGH — `ast.literal_eval()` on File Input ✅ Fixed

**Was:** `agent_connector.py` parsed `sample_batches.txt` using
`ast.literal_eval()`, which is exploitable if the file is attacker-controlled
and can also cause DoS via deeply nested input.

**Fix:** Replaced with `json.loads()`. The file is now written as JSON Lines
by `object_detection.py` and read safely as JSON.

---

### HIGH — No `.gitignore` ✅ Fixed

**Was:** No `.gitignore` existed, making accidental secret commits trivially
easy.

**Fix:** Added `.gitignore` that excludes `.env*` (except `.env.example`),
`__pycache__`, build artefacts, and the runtime `sample_batches.txt` file.

---

### HIGH — Relative File Paths ✅ Fixed

**Was:** `open("osha.json")` and `open("sample_batches.txt")` relied on the
process working directory, which breaks when scripts are run from any other
directory.

**Fix:** All file paths now use `Path(__file__).parent.resolve()` as the base,
giving stable absolute paths regardless of where the scripts are invoked from.

---

### MEDIUM — Bare `except Exception` / `print()` for Errors ✅ Fixed

**Was:** All error handling used `except Exception as e: print(...)`, which
silently swallowed programming bugs and gave no structured log output.

**Fix:**
- Replaced all `print()` calls with the `logging` module (structured, with
  timestamps and log levels).
- Exception handlers now catch specific exception types
  (`json.JSONDecodeError`, `OSError`, `httpx.TimeoutException`, etc.) and log
  at the appropriate level.

---

### MEDIUM — No Input Validation on `lookup_rule()` ✅ Fixed

**Was:** `state` and `hazard` arguments were used directly without validating
that `state` is a known value, allowing silent "Unknown" returns for real
violations.

**Fix:** Added an allowlist (`VALID_STATES = frozenset({"Michigan",
"California"})`) and `ValueError` raises for empty/non-string arguments.

---

### MEDIUM — Discord Webhook Rate Limiting ✅ Fixed

**Was:** No rate limiting; rapid violation detections could exceed Discord's
30 req/min limit and silently drop alerts.

**Fix:** Added a minimum-interval guard (`DISCORD_MIN_INTERVAL_SECONDS`,
default 3 s) using `asyncio.sleep()` and a monotonic timestamp. The interval
is configurable via environment variable.

---

### LOW — Hardcoded Camera Index and Model Path ✅ Fixed

**Was:** `cv2.VideoCapture(1)` and the YOLO model path were hardcoded.

**Fix:** Both are now read from environment variables (`CAMERA_INDEX`,
`MODEL_PATH`) with sensible defaults, and documented in `.env.example`.

---

### LOW — Debug `print()` Throughout `object_detection.py` ✅ Fixed

**Was:** All status output used `print()`.

**Fix:** Replaced with `logging.info()` / `logging.debug()` / `logging.error()`.

---

### LOW — `sample_batches.txt` wrote Python repr, not JSON ✅ Fixed

**Was:** `object_detection.py` wrote `str(item)` (Python `repr`) into
`sample_batches.txt`, which `agent_connector.py` then parsed with
`ast.literal_eval`.

**Fix:** Writer now uses `json.dumps(item)` (JSON Lines format); reader uses
`json.loads()`. This closes the `eval`-family parsing risk entirely.

---

## Running the Project Securely

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in all required values (generate new seeds, create a new Discord webhook).
3. Ensure `.env` is **never** committed (`git status` should never show it).
4. Run agents:
   ```bash
   # Terminal 1
   python object_detection/smart_agent.py

   # Terminal 2
   python object_detection/continuous_request.py

   # Terminal 3 (after object_detection.py has written sample_batches.txt)
   python object_detection/agent_connector.py
   ```
