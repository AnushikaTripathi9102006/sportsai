from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.serializers import python


class SignupForm(UserCreationForm):
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Enter your email',
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Enter your username',
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Enter your password',
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Confirm your password',
        })
    )
    


    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('OFFICER', 'Procurement Officer'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        label='Register as',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
        })
    )

    


    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']


class LoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Enter your username',
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-500 '
                     'focus:border-indigo-500',
            'placeholder': 'Enter your password',
        })
    )