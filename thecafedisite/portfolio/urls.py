from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'portfolio'

urlpatterns = [
    # Public pages
    path('', views.homepage, name='home'),
    path('music/', views.music, name='music'),
    path('music/track/<int:pk>/play/', views.track_play, name='track_play'),
    path('videos/', views.videos, name='videos'),
    path('videos/<int:pk>/view/', views.video_view, name='video_view'),
    path('stream/', views.stream, name='stream'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Admin dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Custom admin - Music Tracks
    path('dashboard/music/', views.music_list, name='music_list'),
    path('dashboard/music/add/', views.music_add, name='music_add'),
    path('dashboard/music/<int:pk>/edit/', views.music_edit, name='music_edit'),
    path('dashboard/music/<int:pk>/delete/', views.music_delete, name='music_delete'),
    path('dashboard/music/<int:pk>/toggle/', views.music_toggle, name='music_toggle'),

    # Custom admin - Videos
    path('dashboard/videos/', views.video_list, name='video_list'),
    path('dashboard/videos/add/', views.video_add, name='video_add'),
    path('dashboard/videos/<int:pk>/edit/', views.video_edit, name='video_edit'),
    path('dashboard/videos/<int:pk>/delete/', views.video_delete, name='video_delete'),
    path('dashboard/videos/<int:pk>/toggle/', views.video_toggle, name='video_toggle'),
]
