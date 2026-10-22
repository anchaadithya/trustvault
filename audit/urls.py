
from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    path("", views.dashboard, name="audit_dashboard"),
]
