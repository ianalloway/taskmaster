#!/usr/bin/env python3
"""
Taskmaster AI - The intelligent task manager that learns your patterns
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

TASKS_FILE = Path.home() / ".taskmaster" / "tasks.json"
HISTORY_FILE = Path.home() / ".taskmaster" / "history.json"

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

def add_task(description, priority="medium", due=None, tags=None, estimate_minutes=30):
    tasks = load_tasks()
    task = {
        "id": len(tasks) + 1,
        "description": description,
        "priority": priority,
        "due": due,
        "tags": tags or [],
        "estimate_minutes": estimate_minutes,
        "created": datetime.now().isoformat(),
        "completed": False,
        "context": detect_context(description)
    }
    tasks.append(task)
    save_tasks(tasks)
    return f"✓ Added [{priority.upper()}] {description}"

def detect_context(text):
    """Detect task context from description"""
    text = text.lower()
    if any(w in text for w in ["email", "recruiter", "linkedin", "apply"]):
        return "job"
    if any(w in text for w in ["blog", "write", "post", "content"]):
        return "content"
    if any(w in text for w in ["code", "fix", "bug", "build", "deploy"]):
        return "code"
    if any(w in text for w in ["learn", "study", "course", "read"]):
        return "learning"
    return "general"

def list_tasks(filter_priority=None, filter_context=None):
    tasks = [t for t in load_tasks() if not t["completed"]]
    
    if filter_priority:
        tasks = [t for t in tasks if t["priority"] == filter_priority]
    if filter_context:
        tasks = [t for t in tasks if t.get("context") == filter_context]
    
    if not tasks:
        return "No tasks."
    
    lines = ["\n📋 TASKS:"]
    for t in tasks:
        emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "⚪")
        ctx = t.get("context", "•")
        due_str = f" | due {t['due']}" if t.get("due") else ""
        lines.append(f"{emoji} #{t['id']} [{t['priority'][:1].upper()}] {t['description']}{due_str} ({ctx})")
    
    return "\n".join(lines)

def complete_task(task_id):
    tasks = load_tasks()
    history = load_history()
    
    for t in tasks:
        if t["id"] == task_id:
            t["completed"] = True
            t["completed_at"] = datetime.now().isoformat()
            
            # Learn from completion
            history.append({
                "task": t["description"],
                "context": t.get("context", "general"),
                "priority": t["priority"],
                "completed_at": datetime.now().isoformat(),
                "estimate": t.get("estimate_minutes", 30)
            })
            
            save_tasks(tasks)
            save_history(history)
            return f"✓ Done: {t['description']}"
    
    return "Task not found."

def ai_prioritize():
    """Smart prioritization based on context and patterns"""
    tasks = [t for t in load_tasks() if not t["completed"]]
    history = load_history()
    
    if not tasks:
        return "No tasks to prioritize."
    
    # Learn from history
    context_scores = {}
    for h in history[-20:]:
        ctx = h.get("context", "general")
        if ctx not in context_scores:
            context_scores[ctx] = {"total": 0, "count": 0}
        context_scores[ctx]["total"] += 1
        context_scores[ctx]["count"] += 1
    
    priority_weight = {"high": 4, "medium": 2, "low": 1}
    
    def score_task(t):
        score = priority_weight.get(t["priority"], 2) * 10
        
        # Bonus for matching recent context
        ctx = t.get("context", "general")
        if ctx in context_scores:
            score += context_scores[ctx]["count"] * 2
        
        # Due date bonus
        if t.get("due"):
            try:
                due = datetime.fromisoformat(t["due"])
                days_until = (due - datetime.now()).days
                if days_until <= 1: score += 30
                elif days_until <= 3: score += 20
                elif days_until <= 7: score += 10
            except:
                pass
        
        return score
    
    tasks.sort(key=score_task, reverse=True)
    
    lines = ["\n🤖 AI PRIORITIZED:"]
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. {t['description']} [{t['priority']}]")
    
    return "\n".join(lines)

def suggest_next():
    """Suggest the next task based on patterns"""
    tasks = [t for t in load_tasks() if not t["completed"]]
    history = load_history()
    
    if not tasks:
        return "No tasks."
    
    # Simple suggestion: highest priority + matching recent context
    priority_weight = {"high": 4, "medium": 2, "low": 1}
    
    most_recent_ctx = None
    if history:
        most_recent_ctx = history[-1].get("context", "general")
    
    best = max(tasks, key=lambda t: 
        priority_weight.get(t["priority"], 2) * 10 +
        (5 if t.get("context") == most_recent_ctx else 0)
    )
    
    return f"\n👉 Next: {best['description']} [{best['priority']}]"

def stats():
    tasks = load_tasks()
    history = load_history()
    
    completed = [t for t in tasks if t.get("completed")]
    pending = [t for t in tasks if not t.get("completed")]
    
    # Context breakdown
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
╠══════════════════════════════════════╣
║  BY CONTEXT:                      ║"""]
    
    for ctx, count in sorted(contexts.items(), key=lambda x: -x[1]):
        lines.append(f"║    {ctx:12} {count:>3}                 ║")
    
    if history:
        avg_time = sum(h.get("estimate", 30) for h in history[-10:]) / min(10, len(history))
        lines.append(f"╠══════════════════════════════════════╣")
        lines.append(f"║  Avg time: {avg_time:.0f} min                 ║")
    
    lines.append("╚══════════════════════════════════════╝")
    
    return "\n".join(lines)

def daily_briefing():
    """Morning task briefing"""
    tasks = [t for t in load_tasks() if not t.get("completed")]
    
    high = [t for t in tasks if t.get("priority") == "high"]
    medium = [t for t in tasks if t.get("priority") == "medium"]
    low = [t for t in tasks if t.get("priority") == "low"]
    
    lines = ["\n☀️ YOUR DAY:", f"  🔴 High: {len(high)}", f"  🟡 Medium: {len(medium)}", f"  🟢 Low: {len(low)}"]
    
    if high:
        lines.append("\n  HIGH PRIORITY:")
        for t in high[:3]:
            lines.append(f"    • {t['description']}")
    
    lines.append(suggest_next())
    
    return "\n".join(lines)

COMMANDS = {
    "add": ("Add task", "add <task> [--high|--medium|--low] [--due YYYY-MM-DD]"),
    "ls": ("List tasks", "ls [--high|--medium|--low] [--context job|code|content]"),
    "done": ("Complete", "done <id>"),
    "ai": ("AI prioritize", "ai"),
    "next": ("Next task", "next"),
    "stats": ("Statistics", "stats"),
    "brief": ("Daily briefing", "brief"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🤖 Taskmaster - AI Terminal Task Manager\n")
        print("Commands:")
        for cmd, (desc, usage) in COMMANDS.items():
            print(f"  {cmd:8} {usage:40} - {desc}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        desc = " ".join([a for a in sys.argv[2:] if not a.startswith("--")])
        priority = "medium"
        due = None
        
        if "--high" in sys.argv: priority = "high"
        if "--low" in sys.argv: priority = "low"
        
        for a in sys.argv:
            if a.startswith("--due="):
                due = a.split("=")[1]
        
        print(add_task(desc, priority, due))
    
    elif cmd == "ls":
        p = next((a[1:].split("=")[0] for a in sys.argv if a.startswith("--priority=") or a in ["--high", "--medium", "--low"]), None)
        ctx = next((a.split("=")[1] for a in sys.argv if a.startswith("--context=")), None)
        
        if "--high" in sys.argv: p = "high"
        if "--medium" in sys.argv: p = "medium"
        if "--low" in sys.argv: p = "low"
        
        print(list_tasks(p, ctx))
    
    elif cmd == "done":
        print(complete_task(int(sys.argv[2])))
    
    elif cmd == "ai":
        print(ai_prioritize())
    
    elif cmd == "next":
        print(suggest_next())
    
    elif cmd == "stats":
        print(stats())
    
    elif cmd == "brief":
        print(daily_briefing())
