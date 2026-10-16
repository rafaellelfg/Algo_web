"""Practice: the data structures with their tasks (algorithms/practice.py, /api/practice/)."""
from django.test import TestCase

from algorithms.practice import STRUCTURES, TASKS


class PracticeApiTests(TestCase):
    def test_structures_with_their_tasks(self):
        r = self.client.get("/api/practice/")  # public, no key needed
        self.assertEqual(r.status_code, 200)
        structures = r.json()["structures"]
        self.assertEqual([s["id"] for s in structures], ["trees", "graphs"])
        tasks = {s["id"]: [t["id"] for t in s["tasks"]] for s in structures}
        self.assertEqual(tasks, {"trees": ["squirrel"], "graphs": ["skier"]})
        self.assertNotIn("story", structures[0]["tasks"][0])  # the list is short; the text comes with the task

    def test_one_task(self):
        task = self.client.get("/api/practice/squirrel/").json()["task"]
        self.assertEqual(task["structure"], "trees")
        self.assertEqual(task["title"], "The squirrel and the rotten branches")
        for field in ("story", "task", "rules", "input", "output"):
            self.assertTrue(task[field], field)
        self.assertEqual(self.client.get("/api/practice/skier/").json()["task"]["structure"], "graphs")

    def test_unknown_task(self):
        r = self.client.get("/api/practice/nope/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["code"], "not_found")

    def test_every_task_belongs_to_a_structure(self):
        ids = {s["id"] for s in STRUCTURES}
        for t in TASKS:
            self.assertIn(t["structure"], ids, t["id"])
        self.assertEqual(len({t["id"] for t in TASKS}), len(TASKS))  # ids are unique
