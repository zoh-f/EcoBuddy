from django.shortcuts import render

# Create your views here.
def home(request):
    context = {'title': 'User Dashboard'}
    return render(request, 'templates/home.html', context)