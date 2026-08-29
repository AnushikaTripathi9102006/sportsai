from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout

from accounts.models import Profile

from .forms import SignupForm, LoginForm


def signup(request):

    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()

            role = form.cleaned_data['role']

            profile, created = Profile.objects.get_or_create(user=user)
            profile.role = role

            if role == 'FARMER':
                profile.is_approved = True
            elif role == 'OFFICER':
                profile.is_approved = False

            profile.save()

            login(request, user)

            if role == 'OFFICER':
                return redirect('pending_approval')

            return redirect('dashboard')

    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {
        'form': form
    })

def pending_approval(request):
    return render(request, 'accounts/pending_approval.html')

def user_login(request):

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            profile = user.profile

            if profile.role == 'OFFICER' and not profile.is_approved:
                return redirect('pending_approval')

            login(request, user)

            return redirect('dashboard')

    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {
        'form': form
    })

def user_logout(request):
    logout(request)
    return redirect('home')