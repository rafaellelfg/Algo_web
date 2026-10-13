from django.conf import settings
from django.db import models


class SavedTree(models.Model):
    """A tree a logged-in user created. `root` always holds its current state."""

    class TreeKind(models.TextChoices):
        BST = "bst", "Binary search tree"
        RB = "rb", "Red-black tree"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trees")
    kind = models.CharField(max_length=5, choices=TreeKind.choices, default=TreeKind.BST)
    initial_values = models.JSONField()  # the array the user typed in
    root = models.JSONField(null=True)  # current tree (changes after deletes)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Tree #{self.pk} of {self.user}"


class Operation(models.Model):
    """One action on a saved tree."""

    class Kind(models.TextChoices):
        CREATE = "create"
        SEARCH = "search"
        INSERT = "insert"
        DELETE = "delete"
        BLACK_DEPTH = "black_depth"
        PAINT = "paint"

    tree = models.ForeignKey(SavedTree, on_delete=models.CASCADE, related_name="operations")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    tree_kind = models.CharField(max_length=5, default="bst")  # bst / rb at the time of the operation
    target = models.FloatField(null=True, blank=True)
    found = models.BooleanField(null=True)
    outcome = models.CharField(max_length=40, blank=True, default="")  # e.g. "FOUND", "BLACK HEIGHT 3"
    steps = models.JSONField(default=list)  # so the operation can be replayed later
    size_after = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
