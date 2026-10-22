
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("documents/", include("documents.urls")),
    path("audit/", include("audit.urls")),
]
