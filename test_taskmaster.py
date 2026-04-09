"""
Automated tests for taskmaster.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import taskmaster


class TestNextId(unittest.TestCase):
    """Tests for the next_id helper."""

    def test_empty_list(self):
        self.assertEqual(taskmaster.next_id([]), 1)

    def test_sequential_ids(self):
        tasks = [{"id": 1}, {"id": 2}, {"id": 3}]
        self.assertEqual(taskmaster.next_id(tasks), 4)

    def test_fills_gap(self):
        tasks = [{"id": 1}, {"id": 3}]
        self.assertEqual(taskmaster.next_id(tasks), 2)

    def test_missing_id_key(self):
        """Tasks without an 'id' key should be ignored gracefully."""
        tasks = [{"description": "no id here"}, {"id": 1}]
        self.assertEqual(taskmaster.next_id(tasks), 2)

    def test_all_missing_id_keys(self):
        """If no task has an 'id', the next ID should be 1."""
        tasks = [{"description": "no id"}, {"description": "also no id"}]
        self.assertEqual(taskmaster.next_id(tasks), 1)


class TestAddTask(unittest.TestCase):
    """Tests for add_task."""

    def setUp(self):
        self._tasks_patcher = patch("taskmaster.TASKS_FILE")
        self._history_patcher = patch("taskmaster.HISTORY_FILE")
        self._tasks_patcher.start()
        self._history_patcher.start()
        # Start with an empty task list
        patch("taskmaster.load_tasks", return_value=[]).start()
        self._save = patch("taskmaster.save_tasks").start()
        self.addCleanup(patch.stopall)

    def test_add_first_task(self):
        with patch("taskmaster.load_tasks", return_value=[]):
            result = taskmaster.add_task("Write tests", priority="high")
        self.assertIn("Write tests", result)
        self.assertIn("#1", result)
        self.assertIn("HIGH", result)

    def test_add_task_increments_id(self):
        existing = [{"id": 1, "description": "existing task", "completed": False,
                     "priority": "medium", "due": None, "tags": [],
                     "estimate_minutes": 30, "created": "2025-01-01T00:00:00",
                     "context": "general"}]
        with patch("taskmaster.load_tasks", return_value=existing):
            result = taskmaster.add_task("Another task")
        self.assertIn("#2", result)

    def test_add_task_fills_id_gap(self):
        existing = [
            {"id": 1, "description": "t1", "completed": False, "priority": "medium",
             "due": None, "tags": [], "estimate_minutes": 30,
             "created": "2025-01-01T00:00:00", "context": "general"},
            {"id": 3, "description": "t3", "completed": False, "priority": "medium",
             "due": None, "tags": [], "estimate_minutes": 30,
             "created": "2025-01-01T00:00:00", "context": "general"},
        ]
        with patch("taskmaster.load_tasks", return_value=existing):
            result = taskmaster.add_task("Fill gap")
        self.assertIn("#2", result)

    def test_add_task_with_missing_id_in_existing(self):
        """add_task should not crash when existing tasks are missing the 'id' key."""
        existing = [{"description": "corrupted task", "completed": False}]
        with patch("taskmaster.load_tasks", return_value=existing):
            result = taskmaster.add_task("New task after corrupted data")
        self.assertIn("#1", result)


class TestDeleteTask(unittest.TestCase):
    """Tests for delete_task."""

    def _make_task(self, task_id, description="task"):
        return {"id": task_id, "description": description, "completed": False,
                "priority": "medium", "due": None, "tags": [],
                "estimate_minutes": 30, "created": "2025-01-01T00:00:00",
                "context": "general"}

    def test_delete_existing_task(self):
        tasks = [self._make_task(1), self._make_task(2)]
        with patch("taskmaster.load_tasks", return_value=tasks), \
             patch("taskmaster.save_tasks") as mock_save:
            result = taskmaster.delete_task(1)
        self.assertIn("Deleted", result)
        saved = mock_save.call_args[0][0]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["id"], 2)

    def test_delete_nonexistent_task(self):
        tasks = [self._make_task(1)]
        with patch("taskmaster.load_tasks", return_value=tasks), \
             patch("taskmaster.save_tasks"):
            result = taskmaster.delete_task(99)
        self.assertIn("not found", result)

    def test_delete_all_tasks(self):
        tasks = [self._make_task(1)]
        with patch("taskmaster.load_tasks", return_value=tasks), \
             patch("taskmaster.save_tasks") as mock_save:
            taskmaster.delete_task(1)
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved, [])

    def test_id_reuse_after_delete(self):
        """After deleting task #1 and adding a new task, the new task should get ID #1."""
        tasks = [self._make_task(2)]
        with patch("taskmaster.load_tasks", return_value=tasks), \
             patch("taskmaster.save_tasks"):
            result = taskmaster.add_task("Reused ID task")
        self.assertIn("#1", result)


class TestMalformedJson(unittest.TestCase):
    """Tests for edge cases with malformed or missing JSON fields."""

    def test_task_missing_id_in_next_id(self):
        tasks = [{"description": "no id"}]
        self.assertEqual(taskmaster.next_id(tasks), 1)

    def test_list_tasks_skips_completed(self):
        tasks = [
            {"id": 1, "description": "pending", "completed": False,
             "priority": "medium", "due": None, "tags": [],
             "estimate_minutes": 30, "created": "2025-01-01T00:00:00",
             "context": "general"},
            {"id": 2, "description": "done", "completed": True,
             "priority": "medium", "due": None, "tags": [],
             "estimate_minutes": 30, "created": "2025-01-01T00:00:00",
             "context": "general"},
        ]
        with patch("taskmaster.load_tasks", return_value=tasks):
            result = taskmaster.list_tasks()
        self.assertIn("pending", result)
        self.assertNotIn("done", result)

    def test_list_tasks_empty(self):
        with patch("taskmaster.load_tasks", return_value=[]):
            result = taskmaster.list_tasks()
        self.assertEqual(result, "No tasks.")


class TestUnknownCommand(unittest.TestCase):
    """Tests for the unknown command feedback."""

    def test_unknown_command_message(self):
        result = subprocess.run(
            [sys.executable, "taskmaster.py", "invalidcmd"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error: Unknown command 'invalidcmd'", result.stdout)
        self.assertIn("--help", result.stdout)

    def test_unknown_command_exit_code(self):
        result = subprocess.run(
            [sys.executable, "taskmaster.py", "notacommand"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
