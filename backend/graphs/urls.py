from django.urls import path

from . import views

urlpatterns = [
    path("analyze/", views.analyze, name="graph-analyze"),
    path("run/", views.run_algorithm, name="graph-run"),
]
