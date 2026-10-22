
from django import forms

from accounts.models import Role, User

from .models import Document
from .validators import category_validator, validate_upload


class UploadForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField(max_length=120, required=False)
    category = forms.CharField(
        max_length=50,
        required=False,
        validators=[category_validator],
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        self.meta = dict(
            zip(
                ("display", "ext", "content_type"),
                validate_upload(uploaded_file),
            )
        )
        return uploaded_file


class EditForm(forms.ModelForm):
    new_file = forms.FileField(
        required=False,
        label="Replace file (optional)",
    )

    def clean_new_file(self):
        uploaded_file = self.cleaned_data.get("new_file")
        if uploaded_file:
            self.meta = dict(
                zip(
                    ("display", "ext", "content_type"),
                    validate_upload(uploaded_file),
                )
            )
        return uploaded_file

    class Meta:
        model = Document
        fields = ["name", "category"]


class GrantForm(forms.Form):
    username = forms.CharField(max_length=150)
    level = forms.ChoiceField(
        choices=[
            ("read", "Read"),
            ("edit", "Read + Edit"),
        ]
    )

    def __init__(self, document, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        target_user = (
            User.objects.filter(
                username__iexact=username,
                is_active=True,
            )
            .exclude(role=Role.ADMIN)
            .exclude(pk=self.document.owner_id)
            .first()
        )

        if target_user is None:
            raise forms.ValidationError(
                "No eligible user with that username."
            )

        self.target = target_user
        return target_user.username


class FilterForm(forms.Form):
    q = forms.CharField(required=False)
    owner = forms.CharField(required=False)
    category = forms.CharField(required=False)
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
