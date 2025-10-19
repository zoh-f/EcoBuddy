from django.shortcuts import render, redirect
from django.contrib.auth import logout

# Create your views here.
from django.http import HttpResponse

def home(request):
    return render(request, "index.html")

def logout_view(request):
    logout(request)
    return redirect('/')