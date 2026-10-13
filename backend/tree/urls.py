from django.urls import path

from . import views

urlpatterns = [
    path("tree/", views.create_tree, name="create-tree"),
    path("tree/op/", views.tree_op, name="tree-op"),
    path("tree/search/", views.search_node, name="search-node"),
    path("tree/delete/", views.delete_node, name="delete-node"),
    path("history/", views.history, name="history"),
    path("history/<int:tree_id>/", views.history_tree, name="history-tree"),
    path("history/<int:tree_id>/operations/<int:op_id>/", views.history_operation, name="history-operation"),
]
