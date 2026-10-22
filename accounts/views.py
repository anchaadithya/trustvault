
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from audit.models import AuditAction, AuditEvent, Outcome
from audit.services import record
from documents.models import Document

from .decorators import role_required
from .forms import (
    RoleChangeForm,
    UserCreateForm,
    AdminPasswordResetForm,
)
from .models import Role, User


def home(request):
    """Show login to anonymous visitors; dashboard to authenticated users."""
    if not request.user.is_authenticated:
        return redirect("login")

    since = timezone.now() - timedelta(days=7)

    context = {
        "documents_count": Document.objects.count(),
        "users_count": User.objects.count(),
        "recent_activity": AuditEvent.objects.order_by("-timestamp")[:5],
        "uploads_count": AuditEvent.objects.filter(
            timestamp__gte=since,
            action=AuditAction.UPLOAD,
            outcome=Outcome.SUCCESS,
        ).count(),
        "downloads_count": AuditEvent.objects.filter(
            timestamp__gte=since,
            action=AuditAction.DOWNLOAD,
            outcome=Outcome.SUCCESS,
        ).count(),
    }

    return render(request, "accounts/home.html", context)


@login_required
@role_required(Role.ADMIN)
def user_list(request):
    search_query = request.GET.get("q", "").strip()
    selected_role = request.GET.get("role", "").strip()

    users = User.objects.all().order_by("username")

    if search_query:
        users = users.filter(username__icontains=search_query)

    valid_roles = [value for value, label in Role.choices]

    if selected_role in valid_roles:
        users = users.filter(role=selected_role)
    else:
        selected_role = ""

    context = {
        "users": users,
        "roles": Role.choices,
        "search_query": search_query,
        "selected_role": selected_role,
    }

    return render(request, "accounts/user_list.html", context)


@login_required
@role_required(Role.ADMIN)
@require_POST
def change_role(request, pk):
    target = get_object_or_404(User, pk=pk)

    if target.pk == request.user.pk:
        record(
            request,
            AuditAction.ROLE_CHANGE,
            Outcome.DENIED,
            detail="admin tried to change own role",
        )
        raise PermissionDenied

    form = RoleChangeForm(request.POST)

    if form.is_valid():
        old_role = target.role
        target.role = form.cleaned_data["role"]
        target.save(update_fields=["role"])

        record(
            request,
            AuditAction.ROLE_CHANGE,
            Outcome.SUCCESS,
            detail=f"user ID {target.pk}: {old_role} -> {target.role}",
        )

        messages.success(
            request,
            f"{target.username} is now {target.get_role_display()}.",
        )
    else:
        messages.error(request, "Invalid role.")

    return redirect("user_list")


@login_required
@role_required(Role.ADMIN)
def user_create(request):
    form = UserCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data

        with transaction.atomic():
            new_user = User.objects.create_user(
                data["username"],
                data["email"],
                data["password"],
                role=data["role"],
            )

            record(
                request,
                AuditAction.USER_MANAGE,
                Outcome.SUCCESS,
                detail=f"created user ID {new_user.pk} as {new_user.role}",
            )

        messages.success(
            request,
            f"User {new_user.username} created.",
        )
        return redirect("user_list")

    return render(
        request,
        "accounts/user_create.html",
        {"form": form},
    )


@login_required
@role_required(Role.ADMIN)
@require_POST
def toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)

    if target.pk == request.user.pk:
        record(
            request,
            AuditAction.USER_MANAGE,
            Outcome.DENIED,
            detail="admin tried to deactivate self",
        )
        raise PermissionDenied

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    record(
        request,
        AuditAction.USER_MANAGE,
        Outcome.SUCCESS,
        detail=(
            f"{'activated' if target.is_active else 'deactivated'} "
            f"user ID {target.pk}"
        ),
    )

    messages.success(
        request,
        f"{target.username} is now "
        f"{'active' if target.is_active else 'deactivated'}.",
    )

    return redirect("user_list")


@login_required
@role_required(Role.ADMIN)
@require_POST
def change_username(request, pk):
    target = get_object_or_404(User, pk=pk)
    new_username = request.POST.get("username", "").strip()

    if not new_username:
        messages.error(request, "Username cannot be empty.")
        return redirect("user_list")

    if len(new_username) > 150:
        messages.error(
            request,
            "Username cannot exceed 150 characters.",
        )
        return redirect("user_list")

    if User.objects.exclude(pk=target.pk).filter(
        username__iexact=new_username
    ).exists():
        messages.error(request, "That username is already in use.")
        return redirect("user_list")

    old_username = target.username

    with transaction.atomic():
        target.username = new_username
        target.save(update_fields=["username"])

        record(
            request,
            AuditAction.USER_MANAGE,
            Outcome.SUCCESS,
            detail=(
                f"admin changed username for user ID {target.pk}: "
                f"{old_username} -> {new_username}"
            ),
        )

    messages.success(request, "Username updated successfully.")
    return redirect("user_list")


@login_required
@role_required(Role.ADMIN)
@require_POST
def delete_user(request, pk):
    """Permanently delete a user while retaining independent audit events."""
    with transaction.atomic():
        target = User.objects.select_for_update().filter(pk=pk).first()

        if target is None:
            messages.error(request, "User not found.")
            return redirect("user_list")

        if target.pk == request.user.pk:
            record(
                request,
                AuditAction.USER_MANAGE,
                Outcome.DENIED,
                detail="admin tried to remove own account",
            )
            messages.error(
                request,
                "You cannot remove your own account.",
            )
            return redirect("user_list")

        if target.is_superuser:
            messages.error(
                request,
                "Superuser accounts cannot be removed from this page.",
            )
            return redirect("user_list")

        if target.role == Role.ADMIN:
            another_active_admin_exists = (
                User.objects.select_for_update()
                .filter(role=Role.ADMIN, is_active=True)
                .exclude(pk=target.pk)
                .exists()
            )

            if not another_active_admin_exists:
                messages.error(
                    request,
                    "You cannot remove the last active Admin account.",
                )
                return redirect("user_list")

        old_username = target.username
        user_id = target.pk

        record(
            request,
            AuditAction.USER_MANAGE,
            Outcome.SUCCESS,
            detail=(
                f"admin permanently deleted user ID {user_id}; "
                f"previous username: {old_username}"
            ),
        )

        target.delete()

    messages.success(
        request,
        f"Account {old_username} was permanently deleted.",
    )
    return redirect("user_list")


@login_required
@role_required(Role.ADMIN)
def reset_user_password(request, pk):
    target = get_object_or_404(User, pk=pk)

    form = AdminPasswordResetForm(
        target,
        request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        record(
            request,
            AuditAction.USER_MANAGE,
            Outcome.SUCCESS,
            detail=f"admin reset password for user ID {target.pk}",
        )

        messages.success(
            request,
            f"Password reset successfully for {target.username}.",
        )
        return redirect("user_list")

    return render(
        request,
        "accounts/password_reset.html",
        {
            "form": form,
            "target_user": target,
        },
    )


class ThrottledLoginView(LoginView):
    """Block repeated login failures within a configured time window."""

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")[:150]

        since = timezone.now() - timedelta(
            minutes=settings.LOGIN_FAILURE_WINDOW_MINUTES
        )

        fails = AuditEvent.objects.filter(
            action=AuditAction.LOGIN,
            outcome=Outcome.FAILURE,
            timestamp__gte=since,
        )

        ip = request.META.get("REMOTE_ADDR")

        too_many_username_failures = (
            fails.filter(actor_username=username).count()
            >= settings.LOGIN_MAX_FAILURES
        )

        too_many_ip_failures = (
            bool(ip)
            and fails.filter(ip_address=ip).count()
            >= settings.LOGIN_MAX_FAILURES_PER_IP
        )

        if too_many_username_failures or too_many_ip_failures:
            record(
                request,
                AuditAction.LOGIN,
                Outcome.DENIED,
                actor_username=username,
                detail="throttled",
            )

            form = self.get_form()
            form.add_error(
                None,
                "Too many failed attempts. Please try again later.",
            )
            return self.form_invalid(form)

        return super().post(request, *args, **kwargs)
