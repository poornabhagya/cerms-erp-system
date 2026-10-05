from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import gettext_lazy as _

from .models import User


class UserLoginForm(AuthenticationForm):
    """Custom Login Form with Bootstrap 5.3 styling."""
    username = forms.CharField(
        label=_("Username or Email"),
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )


class UserPasswordChangeCustomForm(PasswordChangeForm):
    """Custom Password Change Form with Bootstrap 5.3 styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
