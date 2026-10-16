"""Every URL of the API in one place (all under /api/)."""
from django.urls import path

from . import api, login

urlpatterns = [
    # ---- login (login.py)
    path("auth/me/", login.me),
    path("auth/register/", login.register),
    path("auth/login/", login.login_view),
    path("auth/logout/", login.logout_view),
    path("auth/admin/login/", login.admin_login),
    path("auth/admin/verify/", login.admin_verify),
    path("auth/token/refresh/", login.refresh),
    path("auth/tokens/", login.my_tokens),
    path("auth/tokens/<int:token_id>/", login.revoke_my_token),
    # ---- trees + history (api.py)
    path("tree/", api.create_tree),
    path("tree/op/", api.tree_op),
    path("tree/search/", api.search_node),
    path("tree/delete/", api.delete_node),
    path("history/", api.history),
    path("history/<int:tree_id>/", api.history_tree),
    path("history/<int:tree_id>/operations/<int:op_id>/", api.history_operation),
    # ---- graphs (api.py)
    path("graph/analyze/", api.analyze),
    path("graph/run/", api.run_algorithm),
    # ---- practice tasks (api.py)
    path("practice/", api.practice_tasks),
    path("practice/<slug:task_id>/", api.practice_task),
    # ---- admin (api.py)
    path("admin/users/", api.admin_users),
    path("admin/users/<int:user_id>/tokens/", api.admin_revoke_user_tokens),
    path("admin/tokens/", api.admin_tokens),
    path("admin/tokens/<int:token_id>/", api.admin_revoke_token),
]
