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
    path('stream/', views.stream, name='stream'),
    path('stream/past/', views.stream_past, name='stream_past'),
    path('stream/past/<int:pk>/', views.stream_replay, name='stream_replay'),

    # Stream API
    path('api/stream/status/', views.stream_status, name='stream_status'),
    path('api/stream/chat-token/', views.stream_chat_token, name='stream_chat_token'),
    path('api/stream/vod/<int:pk>/view/', views.stream_vod_view, name='stream_vod_view'),

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

    # Custom admin - Career Entries
    path('dashboard/career/', views.career_list, name='career_list'),
    path('dashboard/career/add/', views.career_add, name='career_add'),
    path('dashboard/career/<int:pk>/edit/', views.career_edit, name='career_edit'),
    path('dashboard/career/<int:pk>/delete/', views.career_delete, name='career_delete'),
    path('dashboard/career/<int:pk>/toggle/', views.career_toggle, name='career_toggle'),

    # Custom admin - Skills
    path('dashboard/skills/', views.skill_list, name='skill_list'),
    path('dashboard/skills/add/', views.skill_add, name='skill_add'),
    path('dashboard/skills/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('dashboard/skills/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    path('dashboard/skills/<int:pk>/toggle/', views.skill_toggle, name='skill_toggle'),

    # Custom admin - Profile Images
    path('dashboard/profiles/', views.profile_list, name='profile_list'),
    path('dashboard/profiles/add/', views.profile_add, name='profile_add'),
    path('dashboard/profiles/<int:pk>/edit/', views.profile_edit, name='profile_edit'),
    path('dashboard/profiles/<int:pk>/delete/', views.profile_delete, name='profile_delete'),
    path('dashboard/profiles/<int:pk>/toggle/', views.profile_toggle, name='profile_toggle'),

    # Public comment submission
    path('music/track/<int:pk>/comment/', views.submit_track_comment, name='submit_track_comment'),

    # Custom admin - Stream Sessions
    path('dashboard/streams/', views.stream_list, name='stream_list'),
    path('dashboard/streams/add/', views.stream_add, name='stream_add'),
    path('dashboard/streams/<int:pk>/edit/', views.stream_edit, name='stream_edit'),
    path('dashboard/streams/<int:pk>/delete/', views.stream_delete, name='stream_delete'),
    path('dashboard/streams/<int:pk>/toggle/', views.stream_toggle, name='stream_toggle'),
    path('dashboard/streams/config/', views.stream_config_view, name='stream_config'),

    # Custom admin - Comment Moderation
    path('dashboard/comments/', views.comment_list, name='comment_list'),
    path('dashboard/comments/<int:pk>/approve/', views.comment_approve, name='comment_approve'),
    path('dashboard/comments/<int:pk>/reject/', views.comment_reject, name='comment_reject'),
]
