from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CareerEntry, Skill, ProfileImage, MusicTrack, Video


def homepage(request):
    """Home page with career entries, skills, and profile images"""
    context = {
        'career_entries': CareerEntry.objects.filter(is_published=True),
        'skills': Skill.objects.filter(is_published=True),
        'profile_images': ProfileImage.objects.filter(is_active=True),
    }
    return render(request, "homepage.html", context)


def music(request):
    """Music page with all published tracks"""
    context = {
        'tracks': MusicTrack.objects.filter(is_published=True),
    }
    return render(request, "music.html", context)


def videos(request):
    """Videos page with all published videos"""
    context = {
        'videos': Video.objects.filter(is_published=True),
    }
    return render(request, "videos.html", context)


@require_POST
def track_play(request, pk):
    """Increment play count for a track"""
    track = get_object_or_404(MusicTrack, pk=pk, is_published=True)
    track.increment_play_count()
    return JsonResponse({'status': 'ok', 'play_count': track.play_count})


@require_POST
def video_view(request, pk):
    """Increment view count for a video"""
    video = get_object_or_404(Video, pk=pk, is_published=True)
    video.increment_view_count()
    return JsonResponse({'status': 'ok', 'view_count': video.view_count})


def stream(request):
    """Stream page"""
    return render(request, "stream.html")


def login_view(request):
    """Custom login view with terminal styling"""
    if request.user.is_authenticated:
        return redirect('portfolio:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'portfolio:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, "login.html")


@login_required
def dashboard(request):
    """Admin dashboard for content management"""
    context = {
        'career_count': CareerEntry.objects.count(),
        'skill_count': Skill.objects.count(),
        'profile_image_count': ProfileImage.objects.count(),
        'track_count': MusicTrack.objects.count(),
        'video_count': Video.objects.count(),
    }
    return render(request, "dashboard.html", context)


# =============================================================================
# MUSIC TRACK MANAGEMENT
# =============================================================================

@login_required
def music_list(request):
    """List all music tracks for management"""
    tracks = MusicTrack.objects.all().order_by('-created_at')
    return render(request, "dashboard/music_list.html", {'tracks': tracks})


@login_required
def music_add(request):
    """Add a new music track"""
    if request.method == 'POST':
        title = request.POST.get('title')
        genre = request.POST.get('genre', '')
        release_date = request.POST.get('release_date') or None
        audio_file = request.FILES.get('audio_file')
        cover_art = request.FILES.get('cover_art')
        is_published = request.POST.get('is_published') == 'on'

        if not title or not audio_file:
            messages.error(request, 'Title and audio file are required.')
            return render(request, "dashboard/music_form.html", {'action': 'add'})

        track = MusicTrack.objects.create(
            title=title,
            genre=genre,
            release_date=release_date,
            audio_file=audio_file,
            cover_art=cover_art,
            is_published=is_published,
        )
        messages.success(request, f'Track "{title}" uploaded successfully.')
        return redirect('portfolio:music_list')

    return render(request, "dashboard/music_form.html", {'action': 'add'})


@login_required
def music_edit(request, pk):
    """Edit an existing music track"""
    track = get_object_or_404(MusicTrack, pk=pk)

    if request.method == 'POST':
        track.title = request.POST.get('title', track.title)
        track.genre = request.POST.get('genre', '')
        release_date = request.POST.get('release_date')
        track.release_date = release_date if release_date else None
        track.is_published = request.POST.get('is_published') == 'on'

        if request.FILES.get('audio_file'):
            track.audio_file = request.FILES['audio_file']
        if request.FILES.get('cover_art'):
            track.cover_art = request.FILES['cover_art']

        track.save()
        messages.success(request, f'Track "{track.title}" updated.')
        return redirect('portfolio:music_list')

    return render(request, "dashboard/music_form.html", {'action': 'edit', 'track': track})


@login_required
@require_POST
def music_delete(request, pk):
    """Delete a music track"""
    track = get_object_or_404(MusicTrack, pk=pk)
    title = track.title
    track.delete()
    messages.success(request, f'Track "{title}" deleted.')
    return redirect('portfolio:music_list')


@login_required
@require_POST
def music_toggle(request, pk):
    """Toggle publish status of a music track"""
    track = get_object_or_404(MusicTrack, pk=pk)
    track.is_published = not track.is_published
    track.save(update_fields=['is_published'])
    status = 'published' if track.is_published else 'unpublished'
    messages.success(request, f'Track "{track.title}" {status}.')
    return redirect('portfolio:music_list')


# =============================================================================
# VIDEO MANAGEMENT
# =============================================================================

@login_required
def video_list(request):
    """List all videos for management"""
    videos = Video.objects.all().order_by('-created_at')
    return render(request, "dashboard/video_list.html", {'videos': videos})


@login_required
def video_add(request):
    """Add a new video"""
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category', '')
        tags = request.POST.get('tags', '')
        video_file = request.FILES.get('video_file')
        thumbnail = request.FILES.get('thumbnail')
        resolution = request.POST.get('resolution', '')
        is_published = request.POST.get('is_published') == 'on'

        if not title or not video_file:
            messages.error(request, 'Title and video file are required.')
            return render(request, "dashboard/video_form.html", {'action': 'add'})

        video = Video.objects.create(
            title=title,
            category=category,
            tags=tags,
            video_file=video_file,
            thumbnail=thumbnail,
            resolution=resolution,
            is_published=is_published,
        )
        messages.success(request, f'Video "{title}" uploaded successfully.')
        return redirect('portfolio:video_list')

    return render(request, "dashboard/video_form.html", {'action': 'add'})


@login_required
def video_edit(request, pk):
    """Edit an existing video"""
    video = get_object_or_404(Video, pk=pk)

    if request.method == 'POST':
        video.title = request.POST.get('title', video.title)
        video.category = request.POST.get('category', '')
        video.tags = request.POST.get('tags', '')
        video.resolution = request.POST.get('resolution', '')
        video.is_published = request.POST.get('is_published') == 'on'

        if request.FILES.get('video_file'):
            video.video_file = request.FILES['video_file']
        if request.FILES.get('thumbnail'):
            video.thumbnail = request.FILES['thumbnail']

        video.save()
        messages.success(request, f'Video "{video.title}" updated.')
        return redirect('portfolio:video_list')

    return render(request, "dashboard/video_form.html", {'action': 'edit', 'video': video})


@login_required
@require_POST
def video_delete(request, pk):
    """Delete a video"""
    video = get_object_or_404(Video, pk=pk)
    title = video.title
    video.delete()
    messages.success(request, f'Video "{title}" deleted.')
    return redirect('portfolio:video_list')


@login_required
@require_POST
def video_toggle(request, pk):
    """Toggle publish status of a video"""
    video = get_object_or_404(Video, pk=pk)
    video.is_published = not video.is_published
    video.save(update_fields=['is_published'])
    status = 'published' if video.is_published else 'unpublished'
    messages.success(request, f'Video "{video.title}" {status}.')
    return redirect('portfolio:video_list')
