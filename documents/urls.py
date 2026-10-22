
from django.urls import path
from . import views

urlpatterns = [
    # Documents list
    path("", views.document_list, name="documents"),

    # Upload document
    path("upload/", views.upload, name="document_upload"),

    # Access requests: View and Download
    path(
        "download-requests/",
        views.download_requests,
        name="download_requests",
    ),
    path(
        "download-requests/<int:request_pk>/<str:decision>/",
        views.review_download_request,
        name="review_download_request",
    ),

    # Request download permission
    path(
        "<int:pk>/request-download/",
        views.request_download_access,
        name="request_download_access",
    ),

    # Request temporary view permission (1 hour)
    path(
        "<int:pk>/request-view/",
        views.request_view_access,
        name="request_view_access",
    ),

    # Document actions
    path("<int:pk>/download/", views.download, name="document_download"),
    path("<int:pk>/edit/", views.edit, name="document_edit"),
    path("<int:pk>/delete/", views.delete, name="document_delete"),

    # Document sharing permissions
    path(
        "<int:pk>/permissions/",
        views.permissions,
        name="document_permissions",
    ),
    path(
        "<int:pk>/permissions/<int:perm_pk>/revoke/",
        views.revoke,
        name="document_revoke",
    ),

    # Document details — keep this route last
    path("<int:pk>/", views.detail, name="document_detail"),
]
