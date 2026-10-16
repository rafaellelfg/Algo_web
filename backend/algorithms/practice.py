"""PRACTICE: the data structures you can practise on and their tasks (pure Python, no Django).

    trees    squirrel   find a branch in a binary search tree and delete it
    graphs   skier      the longest route where every next point is higher

Each task is a story plus the exact task, rules, input and output (in English).
The API (api/api.py) serves them at /api/practice/ and /api/practice/<id>/.
"""
from __future__ import annotations

from typing import Optional

STRUCTURES = [
    {"id": "trees", "title": "Trees", "text": "Binary search trees: search, insert and delete."},
    {"id": "graphs", "title": "Graphs", "text": "Points and connections: walks, paths and searches."},
]

TASKS = [
    {
        "id": "squirrel",
        "structure": "trees",
        "title": "The squirrel and the rotten branches",
        "topic": "Binary search tree · search + delete",
        "difficulty": "Easy",
        "teaser": "Climb the oak, find the rotten branches and gnaw them off without dropping anything that grows on them.",
        "story": [
            "You are a squirrel, and your home is a very tidy oak. Every branch has a number, and the oak "
            "grows by one strict rule: at every fork, the branches with smaller numbers grow to the left and "
            "the ones with larger numbers grow to the right. (Computer scientists call such a tree a binary "
            "search tree. Like every tree in computer science, it is drawn upside down: the root is at the top.)",
            "After a stormy night a woodpecker knocks on your door with bad news: some branches have gone "
            "rotten. He gives you a list of their numbers. A rotten branch has to go before it breaks, but "
            "everything that grows on it is healthy and must not fall to the ground.",
        ],
        "task": ["Remove the rotten branches one by one, in the order of the woodpecker's list. For each of them:"],
        "task_steps": [
            "Find it. Start at the root and compare numbers at every branch: smaller → go left, larger → go "
            "right. A clever squirrel never climbs onto a branch she does not need.",
            "Gnaw it off and reattach everything that grew on it, so that the oak still keeps the "
            "smaller-left, larger-right rule.",
        ],
        "rules": [
            "Nothing grows on the rotten branch (it is a leaf) → simply remove it.",
            "Exactly one branch grows on it → that branch moves up into its place, together with everything "
            "that grows on it.",
            "Two branches grow on it → find the smallest number in its right part: go right once, then left "
            "as far as you can. That branch moves into the rotten branch's place, and whatever grew on its "
            "right is attached where it used to be.",
            "A number from the list is not on the oak → you climb until you reach an empty spot, and nothing changes.",
        ],
        "input": [
            "`values`: the numbers of the branches in the order they grew. Build the oak by inserting them "
            "one by one into an empty binary search tree.",
            "`rotten`: the numbers of the rotten branches, in the woodpecker's order.",
        ],
        "output": [
            "For every rotten branch: the numbers you climb over, from the root down to the rotten branch.",
            "The oak at the end, written in pre-order (a branch, then its left part, then its right part).",
        ],
    },
    {
        "id": "skier",
        "structure": "graphs",
        "title": "The skier's longest climb",
        "topic": "Graph · longest ascending path",
        "difficulty": "Medium",
        "teaser": "Climb from your hut through as many rest points as you can, but every next point must be higher than the last.",
        "story": [
            "You are a skier who loves ski touring: before every ride down, you climb up the mountain on your "
            "skis. The mountain has rest points connected by trails, and you know the altitude of every point.",
            "Climbing is hard work, so you have one rule: on the way up you never go down and never walk along "
            "the flat. Every next point must be strictly higher than the one you are standing on. Today you "
            "want the longest climb possible, starting from the hut where you spent the night.",
        ],
        "task": [
            "Find the longest route from the start point in which every next point is strictly higher than "
            "the previous one. Write down the route and how many trails it has.",
        ],
        "task_steps": [],
        "rules": [
            "Trails go both ways, but you may only walk a trail upward: from the lower point to the higher one.",
            "A trail between two points with the same altitude is flat, so you cannot use it.",
            "The length of a route is the number of trails in it. If several routes are equally long, any of them is correct.",
            "The route can end anywhere. It does not have to reach the highest point of the mountain.",
        ],
        "input": [
            "`points`: every rest point with its altitude in metres.",
            "`trails`: pairs of points that are connected by a trail.",
            "`start`: the hut where you start.",
        ],
        "output": [
            "The longest climb as a list of points beginning with `start`, and its length in trails.",
        ],
    },
]

SUMMARY_FIELDS = ("id", "structure", "title", "topic", "difficulty", "teaser")


def overview() -> list[dict]:
    """Every data structure with the short version of its tasks."""
    return [
        {**s, "tasks": [{k: t[k] for k in SUMMARY_FIELDS} for t in TASKS if t["structure"] == s["id"]]}
        for s in STRUCTURES
    ]


def task_detail(task_id: str) -> Optional[dict]:
    return next((t for t in TASKS if t["id"] == task_id), None)
