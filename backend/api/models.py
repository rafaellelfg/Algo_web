"""Database tables.

SavedTree, Operation   the history of trees and what was done with them
ApiToken               Bearer keys (only their hashes are stored)
AdminChallenge         step 2 of the admin login (the admin phrase)
"""
from django.conf import settings
from django.db import models
from django.utils import timezone



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



class ApiToken(models.Model):
    """
    One Bearer key. The key itself is shown to the client once and never stored:
    only its HMAC-SHA256 hash (`key_hash`) is kept, plus a short `prefix` so a
    person can recognise the key in a list.
    """

    class Role(models.TextChoices):
        USER = "user"
        ADMIN = "admin"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    key_hash = models.CharField(max_length=64, unique=True)
    prefix = models.CharField(max_length=20)
    label = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.prefix}… ({self.role}) of {self.user}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()


class AdminChallenge(models.Model):
    """
    Step 2 of the admin login. After a correct password the server hands out a
    one-time challenge id and asks for the admin phrase. The id is stored hashed,
    expires after a few minutes and allows only a few wrong answers.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_challenges")
    key_hash = models.CharField(max_length=64, unique=True)
    question = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
