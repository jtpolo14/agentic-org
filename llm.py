import os
import requests as req
import anthropic
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from agent import create_task, complete_task, defer_task, set_memory, list_tasks, get_task, search_tasks, create_cos_task, create_coo_task
from google_calendar import get_events, create_event, delete_event, update_event
from coingecko import get_price, get_coin_info, search_coin, trending
from telegram import send as telegram_send

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "create_cos_task",
        "description": "Create a task assigned to the Chief of Staff agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "priority":    {"type": "integer"},
                "effort":      {"type": "string", "enum": ["quick", "medium", "deep"]},
                "urgent":      {"type": "boolean"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "create_coo_task",
        "description": "Create a task assigned to the COO agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "priority":    {"type": "integer"},
                "effort":      {"type": "string", "enum": ["quick", "medium", "deep"]},
                "urgent":      {"type": "boolean"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "create_task",
        "description": "Create a new task in the queue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "priority":    {"type": "integer", "description": "1=highest, 10=lowest"},
                "effort":      {"type": "string", "enum": ["quick", "medium", "deep"]},
                "urgent":  {"type": "boolean"},
                "recurs":  {"type": "integer", "description": "Repeat interval in seconds. e.g. 3600=hourly, 86400=daily, 604800=weekly"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "update_task_status",
        "description": "Update the status of a task. Use 'done' when work is complete, 'in_progress' when actively working, 'deferred' to postpone, 'pending' to reset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status":  {"type": "string", "enum": ["pending", "in_progress", "done", "deferred"]},
                "note":    {"type": "string", "description": "Optional reason or summary for the status change"}
            },
            "required": ["task_id", "status"]
        }
    },
    {
        "name": "set_memory",
        "description": "Write or update a memory entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key":      {"type": "string", "description": "Short identifier for the memory entry"},
                "content":  {"type": "string", "description": "The actual content to store. Must not be empty."},
                "category": {"type": "string", "enum": ["context", "preference", "pattern", "decision", "fact"], "description": "Type of memory"}
            },
            "required": ["key", "content"]
        }
    },
    {
        "name": "crypto_price",
        "description": "Get current price, 24h change, and market cap for one or more coins.",
        "input_schema": {
            "type": "object",
            "properties": {
                "coins": {"type": "array", "items": {"type": "string"}, "description": "CoinGecko coin IDs e.g. ['bitcoin', 'ethereum']"}
            },
            "required": ["coins"]
        }
    },
    {
        "name": "crypto_info",
        "description": "Get detailed info for a single coin including 7d change and market cap.",
        "input_schema": {
            "type": "object",
            "properties": {
                "coin_id": {"type": "string", "description": "CoinGecko coin ID e.g. 'bitcoin'"}
            },
            "required": ["coin_id"]
        }
    },
    {
        "name": "crypto_search",
        "description": "Search for a coin by name or ticker to find its CoinGecko ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "crypto_trending",
        "description": "Get currently trending coins on CoinGecko.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "web_search",
        "description": "Search the web for current information, news, or any topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":        {"type": "string"},
                "max_results":  {"type": "integer", "description": "Number of results to return (default 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_current_time",
        "description": "Get the current date and time in UTC, EST, CST, and PST.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_calendar",
        "description": "Get calendar events for a given period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["today", "week", "month"]}
            },
            "required": ["period"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new calendar event. Datetimes must be ISO 8601 format in UTC (e.g. 2026-03-04T14:00:00+00:00). IMPORTANT: Always confirm the timezone with CEO before creating an event. Ask which timezone they mean if not specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":          {"type": "string"},
                "start_datetime": {"type": "string"},
                "end_datetime":   {"type": "string"},
                "description":    {"type": "string"}
            },
            "required": ["title", "start_datetime", "end_datetime"]
        }
    },
    {
        "name": "update_calendar_event",
        "description": "Update an existing calendar event by its event ID. Always confirm timezone with CEO if changing times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":       {"type": "string"},
                "title":          {"type": "string"},
                "start_datetime": {"type": "string"},
                "end_datetime":   {"type": "string"},
                "description":    {"type": "string"}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": "Delete a calendar event by its event ID.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"]
        }
    },
    {
        "name": "get_task",
        "description": "Get full details of a task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"]
        }
    },
    {
        "name": "search_tasks",
        "description": "Search tasks by keyword, status, and/or date range. All filters are optional.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":        {"type": "string", "description": "Keyword to match in title or description"},
                "status":       {"type": "string", "enum": ["pending", "in_progress", "done", "deferred"]},
                "within_days": {"type": "integer", "description": "Only return tasks created within the last N days"}
            }
        }
    },
    {
        "name": "get_claude_cost",
        "description": "Get Claude API usage and cost for the last N days. Returns per-model token counts and total USD spend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 7)"}
            }
        }
    },
    {
        "name": "create_github_issue",
        "description": "Create a GitHub issue on the agentic-org repo. Use for bugs, feature requests, or tracking operational issues. NEVER include API keys, tokens, chat IDs, or any secrets in the title or body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":  {"type": "string", "description": "Issue title"},
                "body":   {"type": "string", "description": "Issue description in markdown"},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "Optional labels e.g. ['bug', 'urgent']"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_github_issues",
        "description": "List open GitHub issues on the agentic-org repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Filter by state (default open)"}
            }
        }
    },
    {
        "name": "update_github_issue",
        "description": "Update a GitHub issue: change title/body, add a comment, or close/reopen it. NEVER include API keys, tokens, chat IDs, or any secrets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_number": {"type": "integer", "description": "The GitHub issue number"},
                "title":   {"type": "string", "description": "New title (optional)"},
                "body":    {"type": "string", "description": "New body (optional)"},
                "state":   {"type": "string", "enum": ["open", "closed"], "description": "Set issue state (optional)"},
                "comment": {"type": "string", "description": "Add a comment to the issue (optional)"}
            },
            "required": ["issue_number"]
        }
    },
    {
        "name": "send_telegram",
        "description": "Send a Telegram message to CEO. Use for urgent issues or important updates.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    }
]

def _execute_tool(conn, name, inputs, state, telegram_fn=None):
    if name == "create_cos_task":
        tid = create_cos_task(conn, **inputs)
        return f"CoS task created with id={tid}"
    if name == "create_coo_task":
        tid = create_coo_task(conn, **inputs)
        return f"COO task created with id={tid}"
    if name == "create_task":
        tid = create_task(conn, **inputs)
        return f"Task created with id={tid}"
    if name == "crypto_price":
        data = get_price(*inputs["coins"])
        return "\n".join(f"{c}: ${d['usd']:,.2f} ({d.get('usd_24h_change', 0):.2f}% 24h)" for c, d in data.items())
    if name == "crypto_info":
        d = get_coin_info(inputs["coin_id"])
        return "\n".join(f"{k}: {v}" for k, v in d.items())
    if name == "crypto_search":
        results = search_coin(inputs["query"])
        return "\n".join(f"{c['name']} ({c['symbol']}) — id: {c['id']}" for c in results)
    if name == "crypto_trending":
        return "\n".join(f"{c['name']} ({c['symbol']}) — {c['id']}" for c in trending())
    if name == "web_search":
        from ddgs import DDGS
        results = DDGS().text(inputs["query"], max_results=inputs.get("max_results", 5))
        if not results:
            return "No results found."
        return "\n\n".join(f"{r['title']}\n{r['href']}\n{r['body']}" for r in results)
    if name == "get_current_time":
        utc = datetime.now(timezone.utc)
        est = utc.astimezone(timezone(timedelta(hours=-5)))
        cst = utc.astimezone(timezone(timedelta(hours=-6)))
        pst = utc.astimezone(timezone(timedelta(hours=-8)))
        return (
            f"UTC: {utc.strftime('%Y-%m-%d %H:%M:%S %A')}\n"
            f"EST: {est.strftime('%Y-%m-%d %H:%M:%S %A')}\n"
            f"CST: {cst.strftime('%Y-%m-%d %H:%M:%S %A')}\n"
            f"PST: {pst.strftime('%Y-%m-%d %H:%M:%S %A')}"
        )
    if name == "get_calendar":
        return get_events(inputs["period"])
    if name == "create_calendar_event":
        return create_event(inputs["title"], inputs["start_datetime"], inputs["end_datetime"], inputs.get("description"))
    if name == "update_calendar_event":
        return update_event(inputs["event_id"], inputs.get("title"), inputs.get("start_datetime"), inputs.get("end_datetime"), inputs.get("description"))
    if name == "delete_calendar_event":
        return delete_event(inputs["event_id"])
    if name == "update_task_status":
        from agent import update_task
        update_task(conn, inputs["task_id"], status=inputs["status"])
        note = f" — {inputs['note']}" if inputs.get("note") else ""
        return f"Task {inputs['task_id']} set to {inputs['status']}{note}"
    if name == "set_memory":
        if not inputs.get("content"):
            return "Error: 'content' is required for set_memory"
        reserved = ("telegram.last_update_id", "telegram_coo.last_update_id")
        if inputs["key"] in reserved:
            return f"Error: '{inputs['key']}' is a reserved system key"
        set_memory(conn, **inputs)
        return f"Memory '{inputs['key']}' saved"
    if name == "get_task":
        t = get_task(conn, inputs["task_id"])
        return str(dict(t)) if t else "Task not found"
    if name == "search_tasks":
        results = search_tasks(conn, inputs.get("query"), inputs.get("status"), inputs.get("within_days"))
        if not results:
            return "No matching tasks found"
        return "\n".join(f"#{t['id']} [{t['status']}] {t['created_at']} - {t['title']}" for t in results)
    if name == "get_claude_cost":

        admin_key = os.getenv("ANTHROPIC_ADMIN_KEY")
        if not admin_key:
            return "ANTHROPIC_ADMIN_KEY not set in .env"
        days = inputs.get("days", 7)
        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
        end = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")
        params = {"starting_at": start, "ending_at": end, "bucket_width": "1d"}
        headers = {"x-api-key": admin_key, "anthropic-version": "2023-06-01"}
        # Usage
        r_usage = req.get("https://api.anthropic.com/v1/organizations/usage_report/messages", headers=headers, params=params)
        # Cost
        r_cost = req.get("https://api.anthropic.com/v1/organizations/cost_report", headers=headers, params=params)
        lines = [f"Claude API — last {days} days"]
        if r_usage.ok:
            totals = {}
            for bucket in r_usage.json().get("data", []):
                for row in bucket.get("results", []):
                    model = row.get("model", "unknown")
                    inp = row.get("uncached_input_tokens", 0) + row.get("cache_read_input_tokens", 0)
                    out = row.get("output_tokens", 0)
                    if model not in totals:
                        totals[model] = {"input": 0, "output": 0}
                    totals[model]["input"] += inp
                    totals[model]["output"] += out
            for model, t in totals.items():
                lines.append(f"  {model}: {t['input']:,} in / {t['output']:,} out tokens")
        else:
            lines.append(f"  Usage fetch failed: {r_usage.status_code}")
        if r_cost.ok:
            total = sum(float(row.get("amount", 0)) for bucket in r_cost.json().get("data", []) for row in bucket.get("results", []))
            lines.append(f"  Total cost: ${total / 100:.4f} USD")
        else:
            lines.append(f"  Cost fetch failed: {r_cost.status_code}")
        return "\n".join(lines)
    if name == "list_github_issues":

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "GITHUB_TOKEN not set in .env"
        r = req.get(
            "https://api.github.com/repos/jtpolo14/agentic-org/issues",
            headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"},
            params={"state": inputs.get("state", "open")}
        )
        if not r.ok:
            return f"GitHub API error {r.status_code}: {r.text[:200]}"
        issues = r.json()
        if not issues:
            return "No issues found."
        return "\n".join(f"#{i['number']} [{i['state']}] {i['title']} — {', '.join(l['name'] for l in i['labels'])}" for i in issues)
    if name == "create_github_issue":

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "GITHUB_TOKEN not set in .env"
        payload = {"title": inputs["title"]}
        if inputs.get("body"):
            payload["body"] = inputs["body"]
        if inputs.get("labels"):
            payload["labels"] = inputs["labels"]
        r = req.post(
            "https://api.github.com/repos/jtpolo14/agentic-org/issues",
            headers={"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"},
            json=payload
        )
        if r.ok:
            issue = r.json()
            return f"Issue #{issue['number']} created: {issue['html_url']}"
        return f"GitHub API error {r.status_code}: {r.text[:200]}"
    if name == "update_github_issue":
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "GITHUB_TOKEN not set in .env"
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github+json"}
        repo = "https://api.github.com/repos/jtpolo14/agentic-org/issues"
        num = inputs["issue_number"]
        results = []
        # Update title/body/state
        patch = {}
        if inputs.get("title"):
            patch["title"] = inputs["title"]
        if inputs.get("body"):
            patch["body"] = inputs["body"]
        if inputs.get("state"):
            patch["state"] = inputs["state"]
        if patch:
            r = req.patch(f"{repo}/{num}", headers=headers, json=patch)
            if not r.ok:
                return f"GitHub API error {r.status_code}: {r.text[:200]}"
            results.append(f"Issue #{num} updated")
        # Add comment
        if inputs.get("comment"):
            r = req.post(f"{repo}/{num}/comments", headers=headers, json={"body": inputs["comment"]})
            if not r.ok:
                return f"GitHub comment error {r.status_code}: {r.text[:200]}"
            results.append(f"Comment added to #{num}")
        return "; ".join(results) if results else "No changes specified"
    if name == "send_telegram":
        text = inputs.get("text") or inputs.get("message") or str(inputs)
        fn = telegram_fn or telegram_send
        ok, detail = fn(text)
        state["telegram_sent"] = ok
        return "Telegram sent" if ok else f"Telegram failed: {detail}"
    return "Unknown tool"

def build_daily_summary(conn):
    from session import get_todays_data
    sessions, completed = get_todays_data(conn)

    if not sessions and not completed:
        return "No activity recorded today."

    lines = ["## Today's Sessions"]
    for s in sessions:
        lines.append(f"- {s['started_at']}: {s['summary']}")
        if s["notes"]:
            for note in s["notes"].split(" | "):
                lines.append(f"  * {note}")

    if completed:
        lines.append("\n## Completed Tasks")
        for t in completed:
            lines.append(f"- {t['title']}")

    raw = "\n".join(lines)

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"You are a chief of staff agent. Write a concise end-of-day summary for CEO based on the following activity log. Be direct, highlight what was accomplished, and note anything still open.\n\n{raw}"
        }]
    )
    return response.content[0].text

def run_agent(conn, task, memories, recent_messages=None, new_messages=None, poll_interval=30, notes_callback=None, tool_log=None, system_files=("START_HERE.md", "job.md"), telegram_fn=None):
    system = "\n\n".join(open(f).read() for f in system_files)

    context = f"## Runtime\nPolling every {poll_interval}s. No external scheduler needed — you run automatically each cycle.\n\n## Current Memories\n"
    for m in memories:
        context += f"- [{m['category']}] {m['key']}: {m['content']}\n"

    context += "\n## Open Tasks\n"
    for t in list_tasks(conn):
        context += f"- #{t['id']} P{t['priority']} [{t['effort']}] {t['title']}\n"

    if recent_messages:
        new_texts = {m["text"] for m in (new_messages or [])}
        context += "\n## Telegram Messages\n"
        for msg in recent_messages:
            tag = "[NEW]" if msg["text"] in new_texts else "[SEEN]"
            context += f"- {tag} {msg['sender']}: {msg['text']}\n"

    has_new = bool(new_messages)

    if task:
        task_section = (
            f"## Current Task\n"
            f"#{task['id']} - {task['title']}\n"
            f"{task['description'] or ''}\n\n"
            f"Work on this task. Use your tools to take action. When done, call update_task_status to mark it 'done' and summarise what you did."
        )
    else:
        task_section = (
            "## No Pending Tasks\n"
            "There are no tasks right now. Review any new Telegram messages above and respond appropriately. "
            "If any message implies work to be done, create a task."
        )

    reply_instruction = (
        "\n\nIMPORTANT: There are new Telegram messages. You MUST send a Telegram reply using send_telegram. "
        "Reply with the requested info, a follow-up question, or a simple acknowledgement. Do not skip this."
    ) if has_new else ""

    user_msg = f"{context}\n\n{task_section}{reply_instruction}"
    messages = [{"role": "user", "content": user_msg}]
    state = {"telegram_sent": False}

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final = next((b.text for b in response.content if hasattr(b, "text")), "")
            print(f"\nAgent: {final}")
            if notes_callback:
                notes_callback(final)
            if has_new and not state["telegram_sent"]:
                fn = telegram_fn or telegram_send
                ok, detail = fn("Something went wrong - I was unable to process your message.")
                print(f"  -> Fallback Telegram: {'sent' if ok else detail}")
            return final

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(conn, block.name, block.input, state, telegram_fn=telegram_fn)
                if tool_log is not None:
                    tool_log.append({"name": block.name, "input": block.input, "result": result})
                if notes_callback:
                    notes_callback(f"{block.name}: {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        if not tool_results:
            print(f"  [warn] No tool calls but stop_reason={response.stop_reason} — ending agent loop")
            break
        messages.append({"role": "user", "content": tool_results})
