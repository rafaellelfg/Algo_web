"""The Django admin site (http://127.0.0.1:8000/admin/) — browse every table."""
from django.contrib import admin

from .models import AdminChallenge, ApiToken, Operation, SavedTree


class OperationInline(admin.TabularInline):
    model = Operation
    fields = ("kind", "tree_kind", "target", "found", "outcome", "size_after", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(SavedTree)
class SavedTreeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "initial_values", "size", "created_at")
    list_filter = ("kind", "user")
    inlines = [OperationInline]


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("id", "tree", "kind", "tree_kind", "target", "found", "outcome", "created_at")
    list_filter = ("kind", "found")


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "prefix", "created_at", "expires_at", "last_used_at", "revoked_at")
    list_filter = ("role",)
    readonly_fields = ("key_hash", "prefix", "created_at", "last_used_at")


@admin.register(AdminChallenge)
class AdminChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at", "attempts", "used_at")
    readonly_fields = ("key_hash",)
