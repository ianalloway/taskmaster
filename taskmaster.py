#!/usr/bin/env python3
"""
Taskmaster AI - The intelligent task manager that learns your patterns
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

TASKS_FILE = Path.home() / ".taskmaster" / "tasks.json"
HISTORY_FILE = Path.home() / ".taskmaster" / "history.json"

PRIORITY_WEIGHT = {"high": 4, "medium": 2, "low": 1}
PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def ensure_dir():
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)


def load_tasks():
    ensure_dir()
    if not TASKS_FILE.exists():
        save_tasks([])
    with open(TASKS_FILE) as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def load_history():
    ensure_dir()
    with open(HISTORY_FILE) as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def next_id(tasks: list) -> int:
    """Return the next available task ID (fills gaps from deleted tasks)."""
    existing = {t["id"] for t in tasks}
    i = 1
    while i in existing:
        i += 1
    return i


def detect_context(text):
    """Detect task context from description."""
    text = text.lower()
    if any(w in text for w in ["email", "recruiter", "linkedin", "apply", "interview", "resume"]):
        return "job"
    if any(w in text for w in ["blog", "write", "post", "content", "article", "newsletter"]):
        return "content"
    if any(w in text for w in ["code", "fix", "bug", "build", "deploy", "pr", "commit", "refactor"]):
        return "code"
    if any(w in text for w in ["learn", "study", "course", "read", "research", "watch"]):
        return "learning"
    if any(w in text for w in ["call", "meeting", "zoom", "schedule", "follow up", "reply"]):
        return "comms"
    return "general"


def is_overdue(task: dict) -> bool:
    """Return True if the task has a due date that has passed."""
    if not task.get("due") or task.get("completed"):
        return False
    try:
        due = datetime.fromisoformat(task["due"])
        return due < datetime.now()
    except (ValueError, TypeError):
        return False


def _fmt_due(task: dict) -> str:
    return f" | due {task['due']}" if task.get("due") else ""


def _fmt_overdue(overdue: bool) -> str:
    return " ⚠️ OVERDUE" if overdue else ""


def add_task(description, priority="medium", due=None, tags=None, estimate_minutes=30):
    tasks = load_tasks()
    task = {
        "id": next_id(tasks),
        "description": description,
        "priority": priority,
        "due": due,
        "tags": tags or [],
        "estimate_minutes": estimate_minutes,
        "created": datetime.now().isoformat(),
        "completed": False,
        "context": detect_context(description),
    }
    tasks.append(task)
    save_tasks(tasks)
    return f"✓ Added [#{task['id']} {priority.upper()}] {description}"


def delete_task(task_id: int) -> str:
    """Permanently remove a task by ID."""
    tasks = load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    if len(tasks) == original_len:
        return f"Task #{task_id} not found."
    save_tasks(tasks)
    return f"✓ Deleted task #{task_id}"


def edit_task(task_id: int, description: str = None, priority: str = None, due: str = None) -> str:
    """Edit a task's description, priority, or due date."""
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            if description:
                t["description"] = description
                t["context"] = detect_context(description)
            if priority:
                if priority not in ("high", "medium", "low"):
                    return "Priority must be high, medium, or low."
                t["priority"] = priority
            if due is not None:
                t["due"] = due if due else None
            save_tasks(tasks)
            return f"✓ Updated task #{task_id}"
    return f"Task #{task_id} not found."


def search_tasks(query: str) -> str:
    """Search tasks by keyword in description or tags."""
    tasks = [t for t in load_tasks() if not t["completed"]]
    q = query.lower()
    matches = [
        t for t in tasks
        if q in t["description"].lower() or any(q in tag.lower() for tag in t.get("tags", []))
    ]
    if not matches:
        return f"No tasks matching '{query}'."
    lines = [f"\n🔍 Results for '{query}':"]
    for t in matches:
        overdue = is_overdue(t)
        emoji = PRIORITY_EMOJI.get(t["priority"], "⚪")
        lines.append(f"{emoji} #{t['id']} [{t['priority'][:1].upper()}] {t['description']}{_fmt_due(t)}{_fmt_overdue(overdue)}")
    return "\n".join(lines)


def list_tasks(filter_priority=None, filter_context=None, filter_tag=None, show_overdue_only=False):
    tasks = [t for t in load_tasks() if not t["completed"]]

    if filter_priority:
        tasks = [t for t in tasks if t["priority"] == filter_priority]
    if filter_context:
        tasks = [t for t in tasks if t.get("context") == filter_context]
    if filter_tag:
        tasks = [t for t in tasks if filter_tag.lower() in [tag.lower() for tag in t.get("tags", [])]]
    if show_overdue_only:
        tasks = [t for t in tasks if is_overdue(t)]

    if not tasks:
        return "No tasks."

    # Precompute overdue once per task to avoid repeated datetime parsing
    for t in tasks:
        t["_overdue"] = is_overdue(t)

    # Sort: overdue first, then by priority weight, then by creation date
    tasks.sort(key=lambda t: (
        not t["_overdue"],
        -PRIORITY_WEIGHT.get(t["priority"], 2),
        t.get("created", ""),
    ))

    lines = ["\n📋 TASKS:"]
    for t in tasks:
        emoji = PRIORITY_EMOJI.get(t["priority"], "⚪")
        ctx = t.get("context", "•")
        tag_str = f" [{', '.join(t['tags'])}]" if t.get("tags") else ""
        lines.append(
            f"{emoji} #{t['id']} [{t['priority'][:1].upper()}] {t['description']}"
            f"{_fmt_due(t)}{_fmt_overdue(t['_overdue'])}{tag_str} ({ctx})"
        )

    overdue_count = sum(1 for t in tasks if t["_overdue"])
    if overdue_count:
        lines.append(f"\n⚠️  {overdue_count} overdue task{'s' if overdue_count != 1 else ''}")

    return "\n".join(lines)


def complete_task(task_id):
    tasks = load_tasks()
    history = load_history()

    for t in tasks:
        if t["id"] == task_id:
            if t.get("completed"):
                return f"Task #{task_id} is already completed."
            t["completed"] = True
            t["completed_at"] = datetime.now().isoformat()

            history.append({
                "task": t["description"],
                "context": t.get("context", "general"),
                "priority": t["priority"],
                "completed_at": datetime.now().isoformat(),
                "estimate": t.get("estimate_minutes", 30),
            })

            save_tasks(tasks)
            save_history(history)
            return f"✓ Done: {t['description']}"

    return f"Task #{task_id} not found."


def ai_prioritize():
    """Smart prioritization based on context and patterns."""
    tasks = [t for t in load_tasks() if not t["completed"]]
    history = load_history()

    if not tasks:
        return "No tasks to prioritize."

    context_scores = {}
    for h in history[-20:]:
        ctx = h.get("context", "general")
        if ctx not in context_scores:
            context_scores[ctx] = 0
        context_scores[ctx] += 1

    def score_task(t):
        score = PRIORITY_WEIGHT.get(t["priority"], 2) * 10

        # Overdue tasks jump to the top
        if is_overdue(t):
            score += 50

        # Bonus for matching recent context
        ctx = t.get("context", "general")
        if ctx in context_scores:
            score += context_scores[ctx] * 2

        # Due date bonus
        if t.get("due"):
            try:
                due = datetime.fromisoformat(t["due"])
                days_until = (due - datetime.now()).days
                if days_until <= 0:
                    score += 40
                elif days_until <= 1:
                    score += 30
                elif days_until <= 3:
                    score += 20
                elif days_until <= 7:
                    score += 10
            except (ValueError, TypeError):
                pass

        return score

    tasks.sort(key=score_task, reverse=True)

    lines = ["\n🤖 AI PRIORITIZED:"]
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. {t['description']} [{t['priority']}]{_fmt_overdue(is_overdue(t))}")

    return "\n".join(lines)


def suggest_next(_tasks=None, _history=None):
    """Suggest the next task based on patterns."""
    tasks = _tasks if _tasks is not None else [t for t in load_tasks() if not t["completed"]]
    history = _history if _history is not None else load_history()

    if not tasks:
        return "No tasks."

    most_recent_ctx = None
    if history:
        most_recent_ctx = history[-1].get("context", "general")

    best = max(
        tasks,
        key=lambda t: (
            50 if is_overdue(t) else 0
        ) + PRIORITY_WEIGHT.get(t["priority"], 2) * 10 + (
            5 if t.get("context") == most_recent_ctx else 0
        ),
    )

    return f"\n👉 Next: {best['description']} [{best['priority']}]{_fmt_overdue(is_overdue(best))}"


def stats():
    tasks = load_tasks()
    history = load_history()

    completed = [t for t in tasks if t.get("completed")]
    pending = [t for t in tasks if not t.get("completed")]
    overdue = [t for t in pending if is_overdue(t)]

    contexts = {}
    for t in completed + pending:
        ctx = t.get("context", "general")
        contexts[ctx] = contexts.get(ctx, 0) + 1

    lines = [f"""
╔══════════════════════════════════════╗
║       📊 TASKMASTER STATS            ║
╠══════════════════════════════════════╣
║  Total:    {len(tasks):>3} tasks               ║
║  Pending:  {len(pending):>3}                     ║
║  Done:     {len(completed):>3}                     ║
║  Overdue:  {len(overdue):>3}                     ║
╠══════════════════════════════════════╣
║  BY CONTEXT:                         ║"""]

    for ctx, count in sorted(contexts.items(), key=lambda x: -x[1]):
        lines.append(f"║    {ctx:12} {count:>3}                 ║")

    if history:
        avg_time = sum(h.get("estimate", 30) for h in history[-10:]) / min(10, len(history))
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║  Avg time: {avg_time:.0f} min                 ║")

    lines.append("╚══════════════════════════════════════╝")

    return "\n".join(lines)


def daily_briefing():
    """Morning task briefing."""
    tasks = [t for t in load_tasks() if not t.get("completed")]
    history = load_history()

    high = [t for t in tasks if t.get("priority") == "high"]
    medium = [t for t in tasks if t.get("priority") == "medium"]
    low = [t for t in tasks if t.get("priority") == "low"]
    overdue = [t for t in tasks if is_overdue(t)]

    lines = [
        "\n☀️  YOUR DAY:",
        f"  🔴 High: {len(high)}",
        f"  🟡 Medium: {len(medium)}",
        f"  🟢 Low: {len(low)}",
    ]

    if overdue:
        lines.append(f"\n  ⚠️  OVERDUE ({len(overdue)}):")
        for t in overdue[:3]:
            lines.append(f"    • #{t['id']} {t['description']} (due {t['due']})")

    if high:
        lines.append("\n  HIGH PRIORITY:")
        for t in high[:3]:
            lines.append(f"    • {t['description']}")

    lines.append(suggest_next(_tasks=tasks, _history=history))

    return "\n".join(lines)


COMMANDS = {
    "add":    ("Add task",         "add <task> [--high|--medium|--low] [--due YYYY-MM-DD] [--tag TAG]"),
    "ls":     ("List tasks",       "ls [--high|--medium|--low] [--context CTX] [--tag TAG] [--overdue]"),
    "done":   ("Complete",         "done <id>"),
    "delete": ("Delete task",      "delete <id>"),
    "edit":   ("Edit task",        "edit <id> [--desc 'new desc'] [--high|--medium|--low] [--due DATE]"),
    "search": ("Search tasks",     "search <keyword>"),
    "ai":     ("AI prioritize",    "ai"),
    "next":   ("Next task",        "next"),
    "stats":  ("Statistics",       "stats"),
    "brief":  ("Daily briefing",   "brief"),
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🤖 Taskmaster - AI Terminal Task Manager\n")
        print("Commands:")
        for cmd, (desc, usage) in COMMANDS.items():
            print(f"  {cmd:8} {usage:50} - {desc}")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        desc = " ".join([a for a in sys.argv[2:] if not a.startswith("--")])
        priority = "medium"
        due = None
        tags = []

        if "--high" in sys.argv:
            priority = "high"
        if "--low" in sys.argv:
            priority = "low"

        for a in sys.argv:
            if a.startswith("--due="):
                due = a.split("=", 1)[1]
            if a.startswith("--tag="):
                tags.append(a.split("=", 1)[1])

        if not desc:
            print("Usage: add <task description> [--high|--medium|--low] [--due=YYYY-MM-DD]")
            sys.exit(1)

        print(add_task(desc, priority, due, tags))

    elif cmd == "ls":
        p = None
        ctx = None
        tag = None
        overdue_only = "--overdue" in sys.argv

        if "--high" in sys.argv:
            p = "high"
        if "--medium" in sys.argv:
            p = "medium"
        if "--low" in sys.argv:
            p = "low"

        for a in sys.argv:
            if a.startswith("--context="):
                ctx = a.split("=", 1)[1]
            if a.startswith("--tag="):
                tag = a.split("=", 1)[1]

        print(list_tasks(p, ctx, tag, overdue_only))

    elif cmd == "done":
        if len(sys.argv) < 3:
            print("Usage: done <id>")
            sys.exit(1)
        print(complete_task(int(sys.argv[2])))

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: delete <id>")
            sys.exit(1)
        print(delete_task(int(sys.argv[2])))

    elif cmd == "edit":
        if len(sys.argv) < 3:
            print("Usage: edit <id> [--desc='new desc'] [--high|--medium|--low] [--due=DATE]")
            sys.exit(1)
        task_id = int(sys.argv[2])
        new_desc = None
        new_priority = None
        new_due = None

        for a in sys.argv[3:]:
            if a.startswith("--desc="):
                new_desc = a.split("=", 1)[1]
            if a in ("--high", "--medium", "--low"):
                new_priority = a[2:]
            if a.startswith("--due="):
                new_due = a.split("=", 1)[1]

        print(edit_task(task_id, new_desc, new_priority, new_due))

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: search <keyword>")
            sys.exit(1)
        print(search_tasks(" ".join(sys.argv[2:])))

    elif cmd == "ai":
        print(ai_prioritize())

    elif cmd == "next":
        print(suggest_next())

    elif cmd == "stats":
        print(stats())

    elif cmd == "brief":
        print(daily_briefing())

    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments to see usage.")
        sys.exit(1)
