#!/usr/bin/env python3
"""Seed the database with demo data.

Usage:
    uv run python scripts/seed.py         # dry run (prints what would be created)
    uv run python scripts/seed.py --apply  # actually write to DB
    uv run python scripts/seed.py --clear  # clear all tables first
"""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from superposition.db import AsyncSessionLocal, engine, Base
from superposition.models import (
    Project, Task, Artifact, Agent, Process, Run, Lane,
    Chatbook, Message, Cell, _utcnow
)


SEED_PROJECTS = [
    {
        "title": "Superposition UI",
        "description": "Godot frontend for the Superposition agent interface.",
        "status": "active",
        "priority": 1,
        "tasks": [
            {"title": "Wire projects view to lane navigation", "status": "todo", "priority": 2},
            {"title": "Add terminal resize on window drag", "status": "todo", "priority": 3},
            {"title": "Dashboard shows run history", "status": "todo", "priority": 2},
        ],
    },
    {
        "title": "Backend Cleanup",
        "description": "Fix tech debt: async subprocess, datetime deprecations, missing endpoints.",
        "status": "archived",
        "priority": 1,
        "tasks": [
            {"title": "Async subprocess for cell execution", "status": "done", "priority": 1},
            {"title": "datetime.utcnow() deprecation", "status": "done", "priority": 2},
            {"title": "Missing CRUD endpoints", "status": "done", "priority": 1},
        ],
    },
    {
        "title": "Auth & Rate Limiting",
        "description": "Add authentication tokens and per-client rate limiting to the API.",
        "status": "active",
        "priority": 1,
        "tasks": [
            {"title": "Pick auth strategy (session tokens vs JWT)", "status": "todo", "priority": 1},
            {"title": "Add CORS middleware", "status": "todo", "priority": 2},
            {"title": "Implement per-IP rate limiting", "status": "todo", "priority": 2},
        ],
    },
]

SEED_CHATBOOKS = [
    {
        "title": "Shell snippets",
        "cells": [
            {"language": "shell", "source": "echo 'hello world'", "status": "success", "output": "hello world"},
            {"language": "shell", "source": "ls -la", "status": "success"},
        ],
    },
    {
        "title": "Python experiments",
        "cells": [
            {"language": "python", "source": "print('hello from python')", "status": "success", "output": "hello from python"},
            {"language": "python", "source": "import this", "status": "success"},
        ],
    },
]

SEED_ARTIFACTS = [
    {
        "kind": "text",
        "title": "API contract notes",
        "content_text": "GET /health, POST /chatbooks, POST /cells/{id}/execute ...",
    },
]


async def clear_all(session):
    """Delete all rows from all tables in reverse FK order."""
    tables = [Run, Message, Cell, Chatbook, Artifact, Task, Lane, Process, Agent, Project]
    for model in tables:
        await session.execute(model.__table__.delete())
    await session.commit()


async def seed(session, apply: bool):
    created = []

    # Projects + tasks
    for proj_data in SEED_PROJECTS:
        tasks_data = proj_data.pop("tasks", [])
        proj = Project(**proj_data)
        session.add(proj)
        created.append(f"Project: {proj.title}")
        for t_data in tasks_data:
            task = Task(project_id=proj.id, **t_data)
            session.add(task)
            created.append(f"  Task: {task.title}")

    # Chatbooks + cells
    for cb_data in SEED_CHATBOOKS:
        cells_data = cb_data.pop("cells", [])
        proj = (await session.execute(text("SELECT id FROM projects LIMIT 1"))).scalar_one_or_none()
        if proj:
            cb = Chatbook(project_id=proj, **cb_data)
        else:
            cb = Chatbook(project_id=str(uuid.uuid4()), **cb_data)
        session.add(cb)
        created.append(f"Chatbook: {cb.title}")
        for i, c_data in enumerate(cells_data):
            c_data["index"] = i
            cell = Cell(chatbook_id=cb.id, **c_data)
            session.add(cell)
            created.append(f"  Cell: [{cell.language}] {cell.source[:30]}")

    # Agents
    for name, mode in [("claude", "agent"), ("o3", "agent"), ("opus", "agent")]:
        agent = Agent(name=name, mode=mode, status="idle")
        session.add(agent)
        created.append(f"Agent: {name} ({mode})")

    if not apply:
        print("Dry run — would create:")
        for line in created:
            print(" ", line)
        return

    await session.commit()
    print(f"Seeded {len(created)} rows:")
    for line in created:
        print(" ", line)


async def main():
    parser = argparse.ArgumentParser(description="Seed Superposition database")
    parser.add_argument("--apply", action="store_true", help="Write to DB (without this flag, dry run)")
    parser.add_argument("--clear", action="store_true", help="Clear all tables before seeding")
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if args.clear:
            print("Clearing all tables...")
            await clear_all(session)
            print("Done.")

        await seed(session, apply=args.apply)


if __name__ == "__main__":
    asyncio.run(main())