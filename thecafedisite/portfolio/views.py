from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CareerEntry, Skill, ProfileImage, MusicTrack, Video, Comment


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
    tracks = MusicTrack.objects.filter(is_published=True).prefetch_related('comments')
    # Add approved comments to each track
    for track in tracks:
        track.approved_comments = track.comments.filter(is_approved=True)
    context = {
        'tracks': tracks,
    }
    return render(request, "music.html", context)


def videos(request):
    """Videos page with all published videos"""
    videos_list = Video.objects.filter(is_published=True).prefetch_related('comments')
    # Add approved comments to each video
    for video in videos_list:
        video.approved_comments = video.comments.filter(is_approved=True)
    context = {
        'videos': videos_list,
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
        'pending_comment_count': Comment.objects.filter(is_approved=False).count(),
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


# =============================================================================
# CAREER ENTRY MANAGEMENT
# =============================================================================

@login_required
def career_list(request):
    """List all career entries for management"""
    entries = CareerEntry.objects.all().order_by('-start_date')
    return render(request, "dashboard/career_list.html", {'entries': entries})


@login_required
def career_add(request):
    """Add a new career entry"""
    if request.method == 'POST':
        title = request.POST.get('title')
        company = request.POST.get('company')
        location = request.POST.get('location', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        bullet_1 = request.POST.get('bullet_1')
        bullet_2 = request.POST.get('bullet_2')
        bullet_3 = request.POST.get('bullet_3')
        order = request.POST.get('order', 0) or 0
        is_published = request.POST.get('is_published') == 'on'

        if not all([title, company, start_date, bullet_1, bullet_2, bullet_3]):
            messages.error(request, 'Title, company, start date, and all 3 bullets are required.')
            return render(request, "dashboard/career_form.html", {'action': 'add'})

        CareerEntry.objects.create(
            title=title,
            company=company,
            location=location,
            start_date=start_date,
            end_date=end_date,
            bullet_1=bullet_1,
            bullet_2=bullet_2,
            bullet_3=bullet_3,
            order=int(order),
            is_published=is_published,
        )
        messages.success(request, f'Career entry "{title}" created.')
        return redirect('portfolio:career_list')

    return render(request, "dashboard/career_form.html", {'action': 'add'})


@login_required
def career_edit(request, pk):
    """Edit an existing career entry"""
    entry = get_object_or_404(CareerEntry, pk=pk)

    if request.method == 'POST':
        entry.title = request.POST.get('title', entry.title)
        entry.company = request.POST.get('company', entry.company)
        entry.location = request.POST.get('location', '')
        entry.start_date = request.POST.get('start_date', entry.start_date)
        end_date = request.POST.get('end_date')
        entry.end_date = end_date if end_date else None
        entry.bullet_1 = request.POST.get('bullet_1', entry.bullet_1)
        entry.bullet_2 = request.POST.get('bullet_2', entry.bullet_2)
        entry.bullet_3 = request.POST.get('bullet_3', entry.bullet_3)
        entry.order = int(request.POST.get('order', 0) or 0)
        entry.is_published = request.POST.get('is_published') == 'on'

        entry.save()
        messages.success(request, f'Career entry "{entry.title}" updated.')
        return redirect('portfolio:career_list')

    return render(request, "dashboard/career_form.html", {'action': 'edit', 'entry': entry})


@login_required
@require_POST
def career_delete(request, pk):
    """Delete a career entry"""
    entry = get_object_or_404(CareerEntry, pk=pk)
    title = entry.title
    entry.delete()
    messages.success(request, f'Career entry "{title}" deleted.')
    return redirect('portfolio:career_list')


@login_required
@require_POST
def career_toggle(request, pk):
    """Toggle publish status of a career entry"""
    entry = get_object_or_404(CareerEntry, pk=pk)
    entry.is_published = not entry.is_published
    entry.save(update_fields=['is_published'])
    status = 'published' if entry.is_published else 'unpublished'
    messages.success(request, f'Career entry "{entry.title}" {status}.')
    return redirect('portfolio:career_list')


# =============================================================================
# SKILL MANAGEMENT
# =============================================================================

@login_required
def skill_list(request):
    """List all skills for management"""
    skills = Skill.objects.all().order_by('category', 'name')
    return render(request, "dashboard/skill_list.html", {'skills': skills})


@login_required
def skill_add(request):
    """Add a new skill"""
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        proficiency = request.POST.get('proficiency', 3)
        order = request.POST.get('order', 0) or 0
        is_published = request.POST.get('is_published') == 'on'

        if not name or not category:
            messages.error(request, 'Name and category are required.')
            return render(request, "dashboard/skill_form.html", {
                'action': 'add',
                'categories': Skill.CATEGORY_CHOICES,
                'proficiencies': Skill.PROFICIENCY_CHOICES,
            })

        Skill.objects.create(
            name=name,
            category=category,
            proficiency=int(proficiency),
            order=int(order),
            is_published=is_published,
        )
        messages.success(request, f'Skill "{name}" created.')
        return redirect('portfolio:skill_list')

    return render(request, "dashboard/skill_form.html", {
        'action': 'add',
        'categories': Skill.CATEGORY_CHOICES,
        'proficiencies': Skill.PROFICIENCY_CHOICES,
    })


@login_required
def skill_edit(request, pk):
    """Edit an existing skill"""
    skill = get_object_or_404(Skill, pk=pk)

    if request.method == 'POST':
        skill.name = request.POST.get('name', skill.name)
        skill.category = request.POST.get('category', skill.category)
        skill.proficiency = int(request.POST.get('proficiency', skill.proficiency))
        skill.order = int(request.POST.get('order', 0) or 0)
        skill.is_published = request.POST.get('is_published') == 'on'

        skill.save()
        messages.success(request, f'Skill "{skill.name}" updated.')
        return redirect('portfolio:skill_list')

    return render(request, "dashboard/skill_form.html", {
        'action': 'edit',
        'skill': skill,
        'categories': Skill.CATEGORY_CHOICES,
        'proficiencies': Skill.PROFICIENCY_CHOICES,
    })


@login_required
@require_POST
def skill_delete(request, pk):
    """Delete a skill"""
    skill = get_object_or_404(Skill, pk=pk)
    name = skill.name
    skill.delete()
    messages.success(request, f'Skill "{name}" deleted.')
    return redirect('portfolio:skill_list')


@login_required
@require_POST
def skill_toggle(request, pk):
    """Toggle publish status of a skill"""
    skill = get_object_or_404(Skill, pk=pk)
    skill.is_published = not skill.is_published
    skill.save(update_fields=['is_published'])
    status = 'published' if skill.is_published else 'unpublished'
    messages.success(request, f'Skill "{skill.name}" {status}.')
    return redirect('portfolio:skill_list')


# =============================================================================
# PROFILE IMAGE MANAGEMENT
# =============================================================================

@login_required
def profile_list(request):
    """List all profile images for management"""
    images = ProfileImage.objects.all().order_by('order')
    return render(request, "dashboard/profile_list.html", {'images': images})


@login_required
def profile_add(request):
    """Add a new profile image"""
    if request.method == 'POST':
        image = request.FILES.get('image')
        alt_text = request.POST.get('alt_text', '')
        order = request.POST.get('order', 0) or 0
        is_active = request.POST.get('is_active') == 'on'

        if not image:
            messages.error(request, 'Image file is required.')
            return render(request, "dashboard/profile_form.html", {'action': 'add'})

        ProfileImage.objects.create(
            image=image,
            alt_text=alt_text,
            order=int(order),
            is_active=is_active,
        )
        messages.success(request, 'Profile image uploaded.')
        return redirect('portfolio:profile_list')

    return render(request, "dashboard/profile_form.html", {'action': 'add'})


@login_required
def profile_edit(request, pk):
    """Edit an existing profile image"""
    profile = get_object_or_404(ProfileImage, pk=pk)

    if request.method == 'POST':
        profile.alt_text = request.POST.get('alt_text', '')
        profile.order = int(request.POST.get('order', 0) or 0)
        profile.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('image'):
            profile.image = request.FILES['image']

        profile.save()
        messages.success(request, 'Profile image updated.')
        return redirect('portfolio:profile_list')

    return render(request, "dashboard/profile_form.html", {'action': 'edit', 'profile': profile})


@login_required
@require_POST
def profile_delete(request, pk):
    """Delete a profile image"""
    profile = get_object_or_404(ProfileImage, pk=pk)
    profile.delete()
    messages.success(request, 'Profile image deleted.')
    return redirect('portfolio:profile_list')


@login_required
@require_POST
def profile_toggle(request, pk):
    """Toggle active status of a profile image"""
    profile = get_object_or_404(ProfileImage, pk=pk)
    profile.is_active = not profile.is_active
    profile.save(update_fields=['is_active'])
    status = 'activated' if profile.is_active else 'deactivated'
    messages.success(request, f'Profile image {status}.')
    return redirect('portfolio:profile_list')


# =============================================================================
# COMMENT SUBMISSION (Public)
# =============================================================================

@require_POST
def submit_track_comment(request, pk):
    """Submit a comment on a music track"""
    track = get_object_or_404(MusicTrack, pk=pk, is_published=True)

    username = request.POST.get('username', '').strip()
    comment_text = request.POST.get('comment_text', '').strip()
    honeypot = request.POST.get('website', '')  # Honeypot field for spam

    # Spam check - honeypot should be empty
    if honeypot:
        return JsonResponse({'status': 'ok'})  # Silently ignore spam

    if not username or not comment_text:
        return JsonResponse({'status': 'error', 'message': 'Name and comment are required.'}, status=400)

    if len(username) > 50:
        return JsonResponse({'status': 'error', 'message': 'Name too long.'}, status=400)

    if len(comment_text) > 1000:
        return JsonResponse({'status': 'error', 'message': 'Comment too long (max 1000 characters).'}, status=400)

    Comment.objects.create(
        track=track,
        username=username,
        comment_text=comment_text,
        is_approved=False,
    )

    return JsonResponse({'status': 'ok', 'message': 'Comment submitted for review.'})


@require_POST
def submit_video_comment(request, pk):
    """Submit a comment on a video"""
    video = get_object_or_404(Video, pk=pk, is_published=True)

    username = request.POST.get('username', '').strip()
    comment_text = request.POST.get('comment_text', '').strip()
    honeypot = request.POST.get('website', '')  # Honeypot field for spam

    # Spam check - honeypot should be empty
    if honeypot:
        return JsonResponse({'status': 'ok'})  # Silently ignore spam

    if not username or not comment_text:
        return JsonResponse({'status': 'error', 'message': 'Name and comment are required.'}, status=400)

    if len(username) > 50:
        return JsonResponse({'status': 'error', 'message': 'Name too long.'}, status=400)

    if len(comment_text) > 1000:
        return JsonResponse({'status': 'error', 'message': 'Comment too long (max 1000 characters).'}, status=400)

    Comment.objects.create(
        video=video,
        username=username,
        comment_text=comment_text,
        is_approved=False,
    )

    return JsonResponse({'status': 'ok', 'message': 'Comment submitted for review.'})


# =============================================================================
# COMMENT MODERATION (Admin)
# =============================================================================

@login_required
def comment_list(request):
    """List all pending comments for moderation"""
    pending_comments = Comment.objects.filter(is_approved=False).order_by('-created_at')
    approved_comments = Comment.objects.filter(is_approved=True).order_by('-created_at')[:20]
    return render(request, "dashboard/comment_list.html", {
        'pending_comments': pending_comments,
        'approved_comments': approved_comments,
    })


@login_required
@require_POST
def comment_approve(request, pk):
    """Approve a comment"""
    comment = get_object_or_404(Comment, pk=pk)
    comment.is_approved = True
    comment.save(update_fields=['is_approved'])
    messages.success(request, f'Comment by "{comment.username}" approved.')
    return redirect('portfolio:comment_list')


@login_required
@require_POST
def comment_reject(request, pk):
    """Reject (delete) a comment"""
    comment = get_object_or_404(Comment, pk=pk)
    username = comment.username
    comment.delete()
    messages.success(request, f'Comment by "{username}" rejected and deleted.')
    return redirect('portfolio:comment_list')
