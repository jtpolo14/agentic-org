# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is Jordan's personal Chief of Staff agent workspace — a memory and context system, not a software project. There is no build system, test suite, or package manager.

## Key Files

- `START_HERE.md` — Read this first. Defines your role as Chief of Staff and how to operate.
- `job.md` — Agent skill definitions and operational responsibilities. Keep this up to date.
- `agent.db` — SQLite database. Persistent memory, tasks, sessions, and notes all live here.

## Coding Standards

- Keep code short and clean. Prefer simple, direct implementations.
- Avoid verbose try/catch blocks — only catch errors you can meaningfully handle.
- No boilerplate test cases or test scaffolding unless explicitly requested.
- No unnecessary abstractions, helpers, or wrappers for one-off tasks.
