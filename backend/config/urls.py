from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # Django's own admin site (browse the database)
    path("api/", include("api.urls")),  # our JSON API — see api/urls.py
]
