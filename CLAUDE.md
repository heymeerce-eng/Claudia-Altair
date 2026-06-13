# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Claudia is a WhatsApp AI agent for ALTAIR Academia (Merce, Anabel, Diana). It runs as a Flask webhook server receiving messages from Twilio, processes them with the Claude API (tool-use loop), and replies via Twilio REST API.

## Commands

```bash
# Run locally
source .venv/bin/activate
python run.py

# Install dependencies
pip install -r requirements.txt

# View live logs (Railway backup via launchd)
tail -f /Users/mercecardenal/claudia/claudia.log
```

No test suite exists. To test a tool manually, activate the venv and import it directly:
```bash
.venv/bin/python -c "from claudia.tools.calendar_tool import get_events; print(get_events('2026-06-13','2026-06-20', email='...', password='...'))"
```

## Architecture

### Message flow
Twilio POST `/webhook` → save to SQLite → **background thread** → `run_agent()` → Twilio REST API reply.

The background thread is critical: Twilio requires a response within 15 seconds but Claude + tools can take longer. The webhook returns empty TwiML immediately; the actual reply is sent via `_send_reply()` when the agent finishes.

### Core files

- **`run.py`** — entry point. Loads `.env`, decodes `GOOGLE_CREDENTIALS_BASE64` to `google_credentials.json` (Railway only, file doesn't exist there), then calls `run_bot()`.
- **`claudia/bot.py`** — Flask app. Endpoints: `/webhook` (WhatsApp), `/calendly` (auto-creates CRM leads on booking), `/zoom-webhook` (updates CRM + pings socia on recording complete), `/health`, `/debug/profiles`.
- **`claudia/agent.py`** — Claude tool-use loop using `claude-haiku-4-5-20251001`. `_build_system_prompt(user)` injects the calling user's profile. `_execute_tool()` dispatches all tool calls with per-user credentials (calendar, zoom).
- **`claudia/users.py`** — Loads `UserProfile` objects from `USER_{i}_*` env vars into `_PROFILES` dict keyed by `whatsapp:+XXXXX`. **Cached at module level** — process restart required for env var changes to take effect.

### User profile loading — known pitfalls

The loader loop (`load_profiles`) iterates i=1,2,3… and **breaks on the first missing `USER_{i}_NAME`**. A user with NAME set but WHATSAPP missing is silently skipped (logs ERROR). This means:
- All USER_N_* vars must be set in Railway manually (`.env` is gitignored).
- If `USER_1_WHATSAPP` is missing in Railway, only USER_2 and USER_3 load.
- `has_calendar()` returns False if `icloud_password` is the placeholder `xxxx-xxxx-xxxx-xxxx`.

Use `/debug/profiles` endpoint to inspect what Railway has loaded and which vars are missing.

### Tools (`claudia/tools/`)

Each tool connects to one external service. Credentials come from env vars.

| Tool | Service | Key env vars |
|------|---------|-------------|
| `calendar_tool.py` | iCloud CalDAV | `USER_{i}_ICLOUD_EMAIL/PASSWORD` per user |
| `crm_tool.py` | Google Sheets (CRM Ventas) | `GOOGLE_SHEETS_CRM_ID` |
| `students_tool.py` | Google Sheets (CRM Alumnos) | `GOOGLE_SHEETS_STUDENTS_ID` |
| `calendly_tool.py` | Calendly REST API | `CALENDLY_API_TOKEN` |
| `zoom_tool.py` | Zoom Server-to-Server OAuth | `ZOOM_ACCOUNT_ID/CLIENT_ID/CLIENT_SECRET` |
| `memory_tool.py` | `memoria.md` flat file | — |
| `pdf_tool.py` | fpdf2, writes to `documentos/` | — |
| `presentation_tool.py` | python-pptx, writes to `documentos/` | — |

**Google Sheets tab matching** uses fuzzy lowercase matching because sheet names contain emojis (e.g. "🔍 CRIBA"). Both `crm_tool` and `students_tool` iterate `ws.title.lower()` looking for keywords.

**Google credentials**: `google_credentials.json` is a service account key. Locally it sits at project root. On Railway it's base64-encoded in `GOOGLE_CREDENTIALS_BASE64` and decoded at startup by `run.py`.

### Persistence

- **Conversation history**: SQLite `claudia.db`, keyed by `hash(whatsapp_number)`. Max 10 messages fetched per request.
- **Persistent memory**: `memoria.md` flat file, organised by `## UserName` sections. Written by `memory_tool.save_memory()`.

Both files are local to the Railway container — they reset on redeploy.

### Deployment

- **Primary**: Railway at `web-production-b87c4.up.railway.app`. Push to `main` on GitHub (`heymeerce-eng/Claudia-Altair`) triggers auto-redeploy.
- **Backup**: macOS launchd service at `~/Library/LaunchAgents/com.altair.claudia.plist`, runs `start_claudia.sh`.
- Twilio sandbox webhook: set to `https://web-production-b87c4.up.railway.app/webhook`.

### Claude API constraint

Tool names must match `^[a-zA-Z0-9_-]{1,128}$`. No Spanish characters (ñ, tildes) in tool names — e.g. `anadir_nota_alumno` not `añadir_nota_alumno`.
