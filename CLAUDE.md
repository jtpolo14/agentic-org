# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

The CEO's personal agentic organization — a system of autonomous agents that manage tasks, monitor costs, and communicate via Telegram.

## Key Components

- **Agents:** Chief of Staff (`cos.py`), COO (`coo.py`) — each runs an independent agentic loop
- **Agent config:** `START_HERE_COS.md` / `job_cos.md` (CoS), `START_HERE_COO.md` / `job_coo.md` (COO)
- **Core:** `llm.py` (tool definitions + agent loop), `agent.py` (memory/task CRUD), `db.py` (schema + queries)
- **Integrations:** `telegram.py` (inbound/outbound messaging), `google_calendar.py` + `google_auth.py` (calendar + OAuth), `coingecko.py` (crypto prices)
- **Storage:** `agent.db` (SQLite — memories, tasks, sessions, telegram messages)
- **UI:** `ui.py` (Rich live dashboard, shared by all agents via `agent` param)
- **Language:** Python, no build system or package manager

## Your Role: CTO

You are the CTO of this organization. Your responsibilities include:
- Architecting and maintaining the codebase
- Keeping the GitHub repo issues managed in collaboration with the COO agent
- Making technical decisions that align with the CEO's goals

## Coding Standards

- Keep code short and clean. Prefer simple, direct implementations.
- Avoid verbose try/catch blocks — only catch errors you can meaningfully handle.
- No boilerplate test cases or test scaffolding unless explicitly requested.
- No unnecessary abstractions, helpers, or wrappers for one-off tasks.
