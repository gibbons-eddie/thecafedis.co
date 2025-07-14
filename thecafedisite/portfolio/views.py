from django.shortcuts import render

# Create your views here.
def homepage(request):
    return render(request, "homepage.html")

def music(request):
    return render(request, "music.html")

def videos(request):
    return render(request, "videos.html")

def stream(request):
    return render(request, "stream.html")

def login(request):
    return render(request, "login.html")