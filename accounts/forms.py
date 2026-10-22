
from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Role, User


class RoleChangeForm(forms.Form):
    role = forms.ChoiceField(choices=Role.choices)


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    role = forms.ChoiceField(choices=Role.choices)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "A user with this username already exists."
            )

        return username


class AdminPasswordResetForm(forms.Form):
    password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    def __init__(self, target_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_user = target_user

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error(
                "confirm_password",
                "Passwords do not match.",
            )

        return cleaned_data

    def save(self):
        password = self.cleaned_data["password"]
        self.target_user.set_password(password)
        self.target_user.save(update_fields=["password"])
        return self.target_user
