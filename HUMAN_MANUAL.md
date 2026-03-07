# Human Manual

Procedures that require manual intervention.

---

## Refresh Google OAuth Token

Required when: scopes change, token is revoked, or `token.json` is deleted/corrupted.

1. Delete `token.json` if it exists
2. Run:
   ```
   python -c "from google_auth import get_credentials; get_credentials()"
   ```
3. A browser window will open — log in and grant permissions
4. `token.json` is written automatically — done

**Current scopes granted:**
- `gmail.readonly`
- `calendar` (read/write)
- `cloud-platform.read-only`
- `cloud-billing.readonly`
- `cloud-billing`

To add a new scope: add it to `SCOPES` in `google_auth.py`, delete `token.json`, and repeat above.

---

## Add a New Telegram Bot/Channel

1. Open BotFather in Telegram → `/newbot`
2. Copy the token into `.env` (e.g. `TELEGRAM_TOKEN_XYZ=...`)
3. Add the bot to the target group, disable privacy mode via BotFather → Bot Settings → Group Privacy → Turn off
4. Message the group, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get the `chat_id`
5. Add `TELEGRAM_CHAT_ID_XYZ=<chat_id>` to `.env`

---

## How Telegram Messaging Works

**Inbound:** Each cycle, the agent polls the bot's `getUpdates` API. New messages are stored in the `telegram_messages` table. The last `update_id` is tracked in a memory key (`telegram.last_update_id` / `telegram_coo.last_update_id`) to avoid re-fetching.

**Context:** The last 20 messages are passed to the agent each cycle. New ones are tagged `[NEW]`, old ones `[SEEN]`. If new messages exist, the agent is instructed to reply.

**Outbound:** The agent calls `send_telegram` to reply. If new messages were received but the agent never sends a reply, a fallback error message is sent automatically.

**Two channels:** CoS and COO each have their own bot token, chat ID, and message history (tagged `cos`/`coo` in the DB). They poll and send independently.

**Reserved keys:** `telegram.last_update_id` and `telegram_coo.last_update_id` are system-managed. The agent is blocked from overwriting them via `set_memory`.

**Troubleshooting:**
- Bot not seeing messages → check Group Privacy is **off** in BotFather, and re-add bot to group after changing
- Outbound failing → check bot token and chat ID in `.env`, restart the agent process

---

## Anthropic Admin Key (for cost monitoring)

Required for the COO agent to fetch Claude API usage and costs.

1. Go to [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys
2. Create an Admin Key (`sk-ant-admin...`) — must be org-level, same workspace as `ANTHROPIC_API_KEY`
3. Add to `.env`: `ANTHROPIC_ADMIN_KEY=sk-ant-admin...`
