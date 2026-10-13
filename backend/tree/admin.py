from django.contrib import admin

from .models import Operation, SavedTree


class OperationInline(admin.TabularInline):
    model = Operation
    fields = ("kind", "target", "found", "size_after", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(SavedTree)
class SavedTreeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_id", "initial_values", "size", "created_at")
    list_filter = ("user",)
    inlines = [OperationInline]


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("id", "tree", "kind", "target", "found", "size_after", "created_at")
    list_filter = ("kind", "found")
