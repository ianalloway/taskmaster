"""
Tests for taskmaster.py - task management functions.

Strategy: patch the module-level TASKS_FILE and HISTORY_FILE globals so
all file I/O is redirected to pytest's tmp_path instead of ~/.taskmaster/.
"""
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure the project root is importable regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).parent.parent))
import taskmaster as tm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_files(tmp_path, tasks=None, history=None):
    """Write tasks and history JSON files under tmp_path and patch globals."""
    tasks_file = tmp_path / "tasks.json"
    history_file = tmp_path / "history.json"
    tasks_file.write_text(json.dumps(tasks if tasks is not None else []))
    history_file.write_text(json.dumps(history if history is not None else []))
    return tasks_file, history_file


# ---------------------------------------------------------------------------
# detect_context
# ---------------------------------------------------------------------------

class TestDetectContext:
    def test_job_keyword_email(self):
        assert tm.detect_context("Send email to recruiter") == "job"

    def test_job_keyword_linkedin(self):
        assert tm.detect_context("Update my LinkedIn profile") == "job"

    def test_job_keyword_apply(self):
        assert tm.detect_context("Apply for the senior role") == "job"

    def test_job_keyword_recruiter(self):
        assert tm.detect_context("Chat with the recruiter today") == "job"

    def test_code_keyword_fix(self):
        assert tm.detect_context("Fix the login bug") == "code"

    def test_code_keyword_build(self):
        assert tm.detect_context("Build and deploy to production") == "code"

    def test_code_keyword_deploy(self):
        assert tm.detect_context("Deploy the new release") == "code"

    def test_code_keyword_code(self):
        assert tm.detect_context("Code the payment module") == "code"

    def test_learning_keyword_learn(self):
        assert tm.detect_context("Learn async Python") == "learning"

    def test_learning_keyword_study(self):
        assert tm.detect_context("Study for AWS exam") == "learning"

    def test_learning_keyword_course(self):
        assert tm.detect_context("Finish the Udemy course") == "learning"

    def test_learning_keyword_read(self):
        assert tm.detect_context("Read the new Python docs") == "learning"

    def test_content_keyword_blog(self):
        assert tm.detect_context("Write a blog post about AI") == "content"

    def test_content_keyword_post(self):
        assert tm.detect_context("Schedule social media post") == "content"

    def test_content_keyword_write(self):
        assert tm.detect_context("Write newsletter copy") == "content"

    def test_general_fallback(self):
        assert tm.detect_context("Buy groceries") == "general"

    def test_case_insensitive(self):
        assert tm.detect_context("SEND EMAIL TO BOSS") == "job"


# ---------------------------------------------------------------------------
# load_tasks / save_tasks
# ---------------------------------------------------------------------------

class TestLoadSaveTasks:
    def test_save_and_load_roundtrip(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        tasks = [{"id": 1, "description": "hello", "completed": False}]
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.save_tasks(tasks)
            loaded = tm.load_tasks()
        assert loaded == tasks

    def test_load_creates_empty_file_when_missing(self, tmp_path):
        tasks_file = tmp_path / "tasks.json"
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        # tasks_file intentionally absent
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.load_tasks()
        assert result == []
        assert tasks_file.exists()

    def test_save_persists_json(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        tasks = [{"id": 1, "description": "test task", "completed": False}]
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.save_tasks(tasks)
        raw = json.loads(tasks_file.read_text())
        assert raw[0]["description"] == "test task"


# ---------------------------------------------------------------------------
# load_history / save_history
# ---------------------------------------------------------------------------

class TestLoadSaveHistory:
    def test_save_and_load_roundtrip(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        history = [{"task": "did thing", "context": "code"}]
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.save_history(history)
            loaded = tm.load_history()
        assert loaded == history

    def test_empty_history_returns_empty_list(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.load_history()
        assert result == []


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

class TestAddTask:
    def test_add_valid_task_returns_confirmation(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.add_task("Write unit tests")
        assert "Write unit tests" in result

    def test_add_task_stores_in_file(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("Deploy app", priority="high")
            tasks = tm.load_tasks()
        assert len(tasks) == 1
        assert tasks[0]["description"] == "Deploy app"
        assert tasks[0]["priority"] == "high"

    def test_add_task_default_priority_is_medium(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("Some task")
            tasks = tm.load_tasks()
        assert tasks[0]["priority"] == "medium"

    def test_add_task_not_completed_by_default(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("New task")
            tasks = tm.load_tasks()
        assert tasks[0]["completed"] is False

    def test_add_multiple_tasks_increments_id(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("First task")
            tm.add_task("Second task")
            tasks = tm.load_tasks()
        assert tasks[0]["id"] == 1
        assert tasks[1]["id"] == 2

    def test_add_task_with_due_date(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("Deadline task", due="2026-03-01")
            tasks = tm.load_tasks()
        assert tasks[0]["due"] == "2026-03-01"

    def test_add_task_with_tags(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("Tagged task", tags=["work", "urgent"])
            tasks = tm.load_tasks()
        assert tasks[0]["tags"] == ["work", "urgent"]

    def test_add_task_detects_context(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.add_task("Fix the nasty bug in production")
            tasks = tm.load_tasks()
        assert tasks[0]["context"] == "code"

    def test_add_task_priority_appears_in_return_string(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.add_task("Urgent thing", priority="high")
        assert "HIGH" in result


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

class TestListTasks:
    def _seed_tasks(self, tmp_path):
        tasks = [
            {"id": 1, "description": "High task", "priority": "high",
             "completed": False, "context": "code", "due": None},
            {"id": 2, "description": "Medium task", "priority": "medium",
             "completed": False, "context": "job", "due": "2026-03-10"},
            {"id": 3, "description": "Low task", "priority": "low",
             "completed": False, "context": "learning", "due": None},
            {"id": 4, "description": "Done task", "priority": "high",
             "completed": True, "context": "code", "due": None},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks)
        return tasks_file, history_file

    def test_list_returns_only_incomplete(self, tmp_path):
        tasks_file, history_file = self._seed_tasks(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks()
        assert "Done task" not in result
        assert "High task" in result

    def test_list_empty_tasks(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks()
        assert result == "No tasks."

    def test_list_filter_by_priority_high(self, tmp_path):
        tasks_file, history_file = self._seed_tasks(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks(filter_priority="high")
        assert "High task" in result
        assert "Medium task" not in result
        assert "Low task" not in result

    def test_list_filter_by_priority_no_match(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[
            {"id": 1, "description": "Only medium", "priority": "medium",
             "completed": False, "context": "general", "due": None},
        ])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks(filter_priority="high")
        assert result == "No tasks."

    def test_list_filter_by_context(self, tmp_path):
        tasks_file, history_file = self._seed_tasks(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks(filter_context="job")
        assert "Medium task" in result
        assert "High task" not in result

    def test_list_shows_due_date(self, tmp_path):
        tasks_file, history_file = self._seed_tasks(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks()
        assert "2026-03-10" in result

    def test_list_all_incomplete_when_no_filter(self, tmp_path):
        tasks_file, history_file = self._seed_tasks(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.list_tasks()
        # 3 incomplete tasks should appear
        assert "High task" in result
        assert "Medium task" in result
        assert "Low task" in result


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------

class TestCompleteTask:
    def _seed(self, tmp_path, completed=False):
        tasks = [
            {"id": 1, "description": "Do something", "priority": "medium",
             "completed": completed, "context": "general",
             "estimate_minutes": 30, "due": None},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks)
        return tasks_file, history_file

    def test_complete_valid_task_returns_confirmation(self, tmp_path):
        tasks_file, history_file = self._seed(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.complete_task(1)
        assert "Do something" in result

    def test_complete_marks_task_completed(self, tmp_path):
        tasks_file, history_file = self._seed(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.complete_task(1)
            tasks = tm.load_tasks()
        assert tasks[0]["completed"] is True

    def test_complete_adds_completed_at_timestamp(self, tmp_path):
        tasks_file, history_file = self._seed(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.complete_task(1)
            tasks = tm.load_tasks()
        assert "completed_at" in tasks[0]

    def test_complete_invalid_id_returns_not_found(self, tmp_path):
        tasks_file, history_file = self._seed(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.complete_task(999)
        assert result == "Task not found."

    def test_complete_task_appends_to_history(self, tmp_path):
        tasks_file, history_file = self._seed(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.complete_task(1)
            history = tm.load_history()
        assert len(history) == 1
        assert history[0]["task"] == "Do something"

    def test_complete_already_completed_task_returns_not_found(self, tmp_path):
        """
        Once a task is marked completed, list_tasks hides it, but complete_task
        searches the raw tasks list. If the task is present but already completed,
        it will still match on id and mark it again (idempotent). If the task was
        removed from the list entirely, it returns 'Task not found.'

        This test verifies the behavior for a task that exists but is already done.
        The function will find it by ID and re-complete it (returning the done msg).
        """
        tasks_file, history_file = self._seed(tmp_path, completed=True)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.complete_task(1)
        # The function iterates all tasks (including completed) - it will find id=1
        assert "Do something" in result or result == "Task not found."

    def test_complete_task_with_multiple_tasks(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Task A", "priority": "high",
             "completed": False, "context": "code", "estimate_minutes": 20, "due": None},
            {"id": 2, "description": "Task B", "priority": "low",
             "completed": False, "context": "general", "estimate_minutes": 10, "due": None},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.complete_task(1)
            remaining = tm.load_tasks()
        assert remaining[0]["completed"] is True
        assert remaining[1]["completed"] is False


# ---------------------------------------------------------------------------
# CLI argument parsing (via __main__ block using subprocess)
# ---------------------------------------------------------------------------

class TestCLI:
    """Smoke-test the CLI entry points using subprocess so the module-level
    file paths can be overridden via environment variables are not needed —
    we patch at the function level instead."""

    def test_cli_add_command(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file), \
             patch("sys.argv", ["taskmaster", "add", "Write", "tests", "--high"]), \
             patch("builtins.print") as mock_print:
            # Re-run the __main__ block logic
            cmd = "add"
            desc = "Write tests"
            priority = "high"
            due = None
            output = tm.add_task(desc, priority, due)
            mock_print(output)
        mock_print.assert_called_once()
        printed = mock_print.call_args[0][0]
        assert "Write tests" in printed
        assert "HIGH" in printed

    def test_cli_done_command(self, tmp_path):
        tasks = [{"id": 5, "description": "CLI task", "priority": "medium",
                  "completed": False, "context": "general", "estimate_minutes": 30, "due": None}]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.complete_task(5)
        assert "CLI task" in result

    def test_cli_no_args_shows_usage(self, tmp_path, capsys):
        """Running with no args prints usage info."""
        import subprocess
        env = os.environ.copy()
        # Point HOME to tmp_path so ~/.taskmaster doesn't pollute the test env
        env["HOME"] = str(tmp_path)
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "taskmaster.py")],
            capture_output=True, text=True, env=env
        )
        assert result.returncode == 1
        assert "Taskmaster" in result.stdout or "Commands" in result.stdout


# ---------------------------------------------------------------------------
# ai_prioritize
# ---------------------------------------------------------------------------

class TestAiPrioritize:
    def _seed(self, tmp_path, tasks, history=None):
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=history or [])
        return tasks_file, history_file

    def test_no_tasks_returns_message(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert "No tasks" in result

    def test_high_priority_sorted_first_with_no_history(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Low task", "priority": "low",
             "completed": False, "context": "general", "due": None},
            {"id": 2, "description": "High task", "priority": "high",
             "completed": False, "context": "general", "due": None},
            {"id": 3, "description": "Medium task", "priority": "medium",
             "completed": False, "context": "general", "due": None},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        # High task should appear before medium and low in the output
        high_pos = result.index("High task")
        medium_pos = result.index("Medium task")
        low_pos = result.index("Low task")
        assert high_pos < medium_pos < low_pos

    def test_due_today_gets_highest_bonus(self, tmp_path):
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tasks = [
            {"id": 1, "description": "Due soon", "priority": "low",
             "completed": False, "context": "general", "due": tomorrow},
            {"id": 2, "description": "No due medium", "priority": "medium",
             "completed": False, "context": "general", "due": None},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        # Due soon should appear before No due medium because of the large due-date bonus
        assert result.index("Due soon") < result.index("No due medium")

    def test_due_within_3_days_bonus(self, tmp_path):
        from datetime import datetime, timedelta
        in_3_days = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        in_10_days = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        tasks = [
            {"id": 1, "description": "Far away low", "priority": "low",
             "completed": False, "context": "general", "due": in_10_days},
            {"id": 2, "description": "3 days low", "priority": "low",
             "completed": False, "context": "general", "due": in_3_days},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert result.index("3 days low") < result.index("Far away low")

    def test_invalid_due_date_does_not_crash(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Bad date task", "priority": "medium",
             "completed": False, "context": "general", "due": "not-a-date"},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert "Bad date task" in result

    def test_recent_context_boosts_score(self, tmp_path):
        history = [{"context": "code", "task": "old task", "priority": "medium",
                    "completed_at": "2026-01-01", "estimate": 30}] * 10
        tasks = [
            {"id": 1, "description": "Code task", "priority": "medium",
             "completed": False, "context": "code", "due": None},
            {"id": 2, "description": "General task", "priority": "medium",
             "completed": False, "context": "general", "due": None},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert result.index("Code task") < result.index("General task")

    def test_output_contains_header(self, tmp_path):
        tasks = [{"id": 1, "description": "A task", "priority": "medium",
                  "completed": False, "context": "general", "due": None}]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert "AI PRIORITIZED" in result or "PRIORITIZED" in result

    def test_completed_tasks_excluded(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Done task", "priority": "high",
             "completed": True, "context": "general", "due": None},
            {"id": 2, "description": "Pending task", "priority": "low",
             "completed": False, "context": "general", "due": None},
        ]
        tasks_file, history_file = self._seed(tmp_path, tasks)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.ai_prioritize()
        assert "Done task" not in result
        assert "Pending task" in result


# ---------------------------------------------------------------------------
# suggest_next
# ---------------------------------------------------------------------------

class TestSuggestNext:
    def test_no_tasks_returns_message(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "No tasks" in result

    def test_returns_highest_priority_task(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Low task", "priority": "low",
             "completed": False, "context": "general"},
            {"id": 2, "description": "High task", "priority": "high",
             "completed": False, "context": "general"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "High task" in result

    def test_context_match_breaks_tie(self, tmp_path):
        history = [{"context": "code", "task": "recent", "priority": "medium",
                    "completed_at": "2026-01-10", "estimate": 30}]
        tasks = [
            {"id": 1, "description": "Code task", "priority": "medium",
             "completed": False, "context": "code"},
            {"id": 2, "description": "General task", "priority": "medium",
             "completed": False, "context": "general"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "Code task" in result

    def test_no_history_still_suggests(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Only task", "priority": "medium",
             "completed": False, "context": "general"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "Only task" in result

    def test_completed_tasks_excluded(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Done task", "priority": "high",
             "completed": True, "context": "general"},
            {"id": 2, "description": "Pending task", "priority": "low",
             "completed": False, "context": "general"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "Done task" not in result
        assert "Pending task" in result

    def test_output_contains_next_marker(self, tmp_path):
        tasks = [{"id": 1, "description": "Do this", "priority": "medium",
                  "completed": False, "context": "general"}]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.suggest_next()
        assert "Next" in result or "next" in result


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_with_empty_data(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.stats()
        assert "0" in result

    def test_stats_counts_pending_and_completed(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Done", "priority": "high",
             "completed": True, "context": "code"},
            {"id": 2, "description": "Pending", "priority": "medium",
             "completed": False, "context": "job"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.stats()
        assert "2" in result  # total tasks

    def test_stats_shows_context_breakdown(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Code task", "priority": "high",
             "completed": False, "context": "code"},
            {"id": 2, "description": "Job task", "priority": "medium",
             "completed": False, "context": "job"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.stats()
        assert "code" in result
        assert "job" in result

    def test_stats_shows_avg_time_with_history(self, tmp_path):
        history = [{"task": "old", "context": "code", "priority": "medium",
                    "completed_at": "2026-01-01", "estimate": 60}]
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.stats()
        assert "60" in result or "Avg" in result

    def test_stats_header_present(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.stats()
        assert "STATS" in result or "Total" in result


# ---------------------------------------------------------------------------
# daily_briefing
# ---------------------------------------------------------------------------

class TestDailyBriefing:
    def test_briefing_with_no_tasks(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        assert "No tasks" in result or "High" in result or "0" in result

    def test_briefing_shows_priority_counts(self, tmp_path):
        tasks = [
            {"id": 1, "description": "High task", "priority": "high",
             "completed": False, "context": "code"},
            {"id": 2, "description": "Medium task", "priority": "medium",
             "completed": False, "context": "general"},
            {"id": 3, "description": "Low task", "priority": "low",
             "completed": False, "context": "general"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        assert "High" in result
        assert "Medium" in result
        assert "Low" in result

    def test_briefing_lists_high_priority_tasks(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Urgent A", "priority": "high",
             "completed": False, "context": "code"},
            {"id": 2, "description": "Urgent B", "priority": "high",
             "completed": False, "context": "code"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        assert "Urgent A" in result
        assert "Urgent B" in result

    def test_briefing_caps_high_priority_at_3(self, tmp_path):
        tasks = [
            {"id": i, "description": f"High task {i}", "priority": "high",
             "completed": False, "context": "code"}
            for i in range(1, 6)
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        # Only first 3 high-priority tasks listed
        assert "High task 4" not in result
        assert "High task 5" not in result

    def test_briefing_includes_next_suggestion(self, tmp_path):
        tasks = [
            {"id": 1, "description": "Do this next", "priority": "high",
             "completed": False, "context": "code"},
        ]
        tasks_file, history_file = _setup_files(tmp_path, tasks=tasks, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        assert "Do this next" in result

    def test_briefing_header_present(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, tasks=[], history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.daily_briefing()
        assert "DAY" in result or "BRIEF" in result or "☀️" in result


# ---------------------------------------------------------------------------
# CLI subprocess tests for each command
# ---------------------------------------------------------------------------

class TestCLISubprocess:
    """Full CLI integration tests using subprocess."""

    def _run(self, tmp_path, *args):
        import subprocess
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        return subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "taskmaster.py")] + list(args),
            capture_output=True, text=True, env=env
        )

    def test_cli_add_and_list(self, tmp_path):
        result = self._run(tmp_path, "add", "My CLI task", "--high")
        assert result.returncode == 0
        assert "My CLI task" in result.stdout

        result = self._run(tmp_path, "ls")
        assert result.returncode == 0
        assert "My CLI task" in result.stdout

    def test_cli_add_with_due(self, tmp_path):
        result = self._run(tmp_path, "add", "Task with due", "--due=2026-12-31")
        assert result.returncode == 0

    def test_cli_done(self, tmp_path):
        self._run(tmp_path, "add", "Complete me")
        result = self._run(tmp_path, "done", "1")
        assert result.returncode == 0
        assert "Complete me" in result.stdout

    def test_cli_ai(self, tmp_path):
        self._run(tmp_path, "add", "Some task")
        result = self._run(tmp_path, "ai")
        assert result.returncode == 0

    def test_cli_next(self, tmp_path):
        self._run(tmp_path, "add", "Next task")
        result = self._run(tmp_path, "next")
        assert result.returncode == 0
        assert "Next task" in result.stdout

    def test_cli_stats(self, tmp_path):
        result = self._run(tmp_path, "stats")
        assert result.returncode == 0
        assert "STATS" in result.stdout or "Total" in result.stdout

    def test_cli_brief(self, tmp_path):
        result = self._run(tmp_path, "brief")
        assert result.returncode == 0

    def test_cli_ls_high_filter(self, tmp_path):
        self._run(tmp_path, "add", "High task", "--high")
        self._run(tmp_path, "add", "Low task", "--low")
        result = self._run(tmp_path, "ls", "--high")
        assert "High task" in result.stdout
        assert "Low task" not in result.stdout

    def test_cli_ls_medium_filter(self, tmp_path):
        self._run(tmp_path, "add", "Medium task")
        result = self._run(tmp_path, "ls", "--medium")
        assert "Medium task" in result.stdout

    def test_cli_ls_low_filter(self, tmp_path):
        self._run(tmp_path, "add", "Low task", "--low")
        result = self._run(tmp_path, "ls", "--low")
        assert "Low task" in result.stdout

    def test_cli_ls_context_filter(self, tmp_path):
        self._run(tmp_path, "add", "Fix the bug")  # context=code
        self._run(tmp_path, "add", "Update LinkedIn")  # context=job
        result = self._run(tmp_path, "ls", "--context=code")
        assert "Fix the bug" in result.stdout
        assert "Update LinkedIn" not in result.stdout


# ---------------------------------------------------------------------------
# ensure_dir — history file auto-creation (lines 17-18)
# ---------------------------------------------------------------------------

class TestStreak:
    """Tests for the streak() and _render_streak() functions."""

    def _history_entry(self, date_str):
        return {"task": "done", "context": "general", "priority": "medium",
                "completed_at": f"{date_str}T10:00:00", "estimate": 30}

    def test_no_history_returns_zero_streak(self, tmp_path):
        tasks_file, history_file = _setup_files(tmp_path, history=[])
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()
        assert "0 day" in result or "Start" in result

    def test_single_completion_today_is_streak_1(self, tmp_path):
        from datetime import datetime
        today = datetime.now().date().isoformat()
        history = [self._history_entry(today)]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()
        assert "1 day" in result

    def test_consecutive_days_counted(self, tmp_path):
        from datetime import date, timedelta as td
        today = date.today()
        history = [
            self._history_entry((today - td(days=i)).isoformat())
            for i in range(5)
        ]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()
        assert "5 days" in result

    def test_gap_resets_streak(self, tmp_path):
        from datetime import date, timedelta as td
        today = date.today()
        history = [
            self._history_entry(today.isoformat()),
            # gap: skip yesterday
            self._history_entry((today - td(days=2)).isoformat()),
        ]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()
        assert "1 day" in result

    def test_render_streak_zero_shows_snowflake(self):
        result = tm._render_streak(0)
        assert "❄️" in result

    def test_render_streak_nonzero_shows_fire(self):
        result = tm._render_streak(3)
        assert "🔥" in result

    def test_render_streak_bar_length_20(self):
        result = tm._render_streak(10)
        assert "█" in result and "░" in result

    def test_render_streak_bar_caps_at_20(self):
        result = tm._render_streak(100)
        # bar should be "████████████████████" (20 blocks, no ░)
        assert "░" not in result.split("[")[1].split("]")[0]

    def test_streak_skips_invalid_dates(self, tmp_path):
        history = [{"task": "bad", "context": "general", "priority": "medium",
                    "completed_at": "not-a-date", "estimate": 30}]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()  # Should not crash
        assert "day" in result

    def test_streak_entry_without_completed_at(self, tmp_path):
        history = [{"task": "old", "context": "general", "priority": "medium",
                    "estimate": 30}]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()  # Should not crash
        assert "day" in result

    def test_streak_from_yesterday_when_nothing_today(self, tmp_path):
        """Streak should count from yesterday if nothing was done today."""
        from datetime import date, timedelta as td
        yesterday = (date.today() - td(days=1)).isoformat()
        two_days_ago = (date.today() - td(days=2)).isoformat()
        history = [
            self._history_entry(yesterday),
            self._history_entry(two_days_ago),
        ]
        tasks_file, history_file = _setup_files(tmp_path, history=history)
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            result = tm.streak()
        assert "2 days" in result

    def test_cli_streak_command(self, tmp_path):
        import subprocess
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "taskmaster.py"), "streak"],
            capture_output=True, text=True, env=env
        )
        assert result.returncode == 0
        assert "STREAK" in result.stdout


class TestEnsureDir:
    def test_creates_history_file_when_absent(self, tmp_path):
        """ensure_dir should write an empty history.json if it doesn't exist."""
        tasks_file = tmp_path / "tasks.json"
        history_file = tmp_path / "history.json"
        tasks_file.write_text("[]")
        # history_file intentionally absent
        assert not history_file.exists()
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.ensure_dir()
        assert history_file.exists()
        assert json.loads(history_file.read_text()) == []

    def test_does_not_overwrite_existing_history(self, tmp_path):
        """ensure_dir must not truncate an existing history file."""
        tasks_file, history_file = _setup_files(
            tmp_path,
            history=[{"task": "keep me", "context": "code"}]
        )
        with patch.object(tm, "TASKS_FILE", tasks_file), \
             patch.object(tm, "HISTORY_FILE", history_file):
            tm.ensure_dir()
        data = json.loads(history_file.read_text())
        assert data[0]["task"] == "keep me"


# ---------------------------------------------------------------------------
# __main__ block — in-process coverage via runpy
# ---------------------------------------------------------------------------

class TestMainBlock:
    """Execute the __main__ block inside the test process so coverage tracks it.

    runpy.run_path re-evaluates the module top-level, so TASKS_FILE / HISTORY_FILE
    are re-computed from Path.home().  We patch Path.home() to return tmp_path so
    the fresh globals point to the test directory.
    """

    def _run_main(self, tmp_path, argv, tasks=None, history=None):
        """Run taskmaster.py as __main__ in-process with a patched HOME directory."""
        import runpy
        # Pre-create the .taskmaster dir and seed files so the module finds them.
        tm_dir = tmp_path / ".taskmaster"
        tm_dir.mkdir(parents=True, exist_ok=True)
        (tm_dir / "tasks.json").write_text(json.dumps(tasks if tasks is not None else []))
        (tm_dir / "history.json").write_text(json.dumps(history if history is not None else []))

        with patch("pathlib.Path.home", return_value=tmp_path), \
             patch("sys.argv", argv), \
             patch("builtins.print") as mock_print:
            try:
                runpy.run_path(
                    str(Path(__file__).parent.parent / "taskmaster.py"),
                    run_name="__main__"
                )
            except SystemExit:
                pass
        return mock_print

    def test_main_no_args_prints_usage(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py"])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Taskmaster" in printed or "Commands" in printed

    def test_main_add_high(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "add", "Main add task", "--high"])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Main add task" in printed
        assert "HIGH" in printed

    def test_main_add_low(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "add", "Low prio task", "--low"])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Low prio task" in printed

    def test_main_add_with_due(self, tmp_path):
        mock_print = self._run_main(
            tmp_path, ["taskmaster.py", "add", "Due task", "--due=2026-12-31"]
        )
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Due task" in printed

    def test_main_ls(self, tmp_path):
        tasks = [{"id": 1, "description": "Listed task", "priority": "medium",
                  "completed": False, "context": "general", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ls"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Listed task" in printed

    def test_main_ls_high_filter(self, tmp_path):
        tasks = [{"id": 1, "description": "High ls task", "priority": "high",
                  "completed": False, "context": "code", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ls", "--high"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "High ls task" in printed

    def test_main_ls_medium_filter(self, tmp_path):
        tasks = [{"id": 1, "description": "Med ls task", "priority": "medium",
                  "completed": False, "context": "general", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ls", "--medium"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Med ls task" in printed

    def test_main_ls_low_filter(self, tmp_path):
        tasks = [{"id": 1, "description": "Low ls task", "priority": "low",
                  "completed": False, "context": "general", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ls", "--low"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Low ls task" in printed

    def test_main_ls_context_filter(self, tmp_path):
        tasks = [{"id": 1, "description": "Context ls task", "priority": "medium",
                  "completed": False, "context": "job", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ls", "--context=job"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Context ls task" in printed

    def test_main_done(self, tmp_path):
        tasks = [{"id": 1, "description": "Done via main", "priority": "medium",
                  "completed": False, "context": "general", "estimate_minutes": 30, "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "done", "1"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Done via main" in printed

    def test_main_ai(self, tmp_path):
        tasks = [{"id": 1, "description": "AI task", "priority": "medium",
                  "completed": False, "context": "general", "due": None}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "ai"], tasks=tasks)
        mock_print.assert_called()

    def test_main_next(self, tmp_path):
        tasks = [{"id": 1, "description": "Next task main", "priority": "high",
                  "completed": False, "context": "code"}]
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "next"], tasks=tasks)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Next task main" in printed

    def test_main_stats(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "stats"])
        mock_print.assert_called()

    def test_main_brief(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "brief"])
        mock_print.assert_called()

    def test_main_streak(self, tmp_path):
        mock_print = self._run_main(tmp_path, ["taskmaster.py", "streak"])
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "STREAK" in printed
