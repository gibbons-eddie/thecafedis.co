import re
import io
import base64
import logging
import secrets
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from .models import CareerEntry, Skill, ProfileImage, MusicTrack, Video, Comment, StreamConfig, StreamSession

logger = logging.getLogger(__name__)


def homepage(request):
    context = {
        'career_entries': CareerEntry.objects.filter(is_published=True),
        'skills': Skill.objects.filter(is_published=True),
        'profile_images': ProfileImage.objects.filter(is_active=True),
    }
    return render(request, "homepage.html", context)


def music(request):
    tracks = MusicTrack.objects.filter(is_published=True).prefetch_related('comments')
    for track in tracks:
        track.approved_comments = track.comments.filter(is_approved=True)
    context = {
        'tracks': tracks,
    }
    return render(request, "music.html", context)


def videos(request):
    videos_list = Video.objects.filter(is_published=True)
    context = {
        'videos': videos_list,
    }
    return render(request, "videos.html", context)


@require_POST
def track_play(request, pk):
    track = get_object_or_404(MusicTrack, pk=pk, is_published=True)
    track.increment_play_count()
    return JsonResponse({'status': 'ok', 'play_count': track.play_count})


def _extract_youtube_id(url_or_id):
    url_or_id = url_or_id.strip()
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    parsed = urlparse(url_or_id)
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [''])[0]
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/embed/')[1].split('/')[0]
    if parsed.hostname == 'youtu.be':
        return parsed.path.lstrip('/')
    return url_or_id


_ivs_cache = {'result': (False, None, 0), 'ts': 0}

def _check_ivs_live():
    import time
    now = time.time()
    if now - _ivs_cache['ts'] < 5:
        return _ivs_cache['result']

    channel_arn = settings.AWS_IVS_CHANNEL_ARN
    if not channel_arn:
        return False, None, 0

    try:
        import boto3
        from botocore.config import Config
        client = boto3.client(
            'ivs',
            region_name=settings.AWS_IVS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(connect_timeout=3, read_timeout=3),
        )
        response = client.get_stream(channelArn=channel_arn)
        stream_data = response.get('stream', {})
        is_live = stream_data.get('state') == 'LIVE'
        recording_url = stream_data.get('playbackUrl', '')
        viewer_count = int(stream_data.get('viewerCount', 0) or 0)
        result = (is_live, recording_url, viewer_count)
    except Exception:
        result = (False, None, 0)

    _ivs_cache['result'] = result
    _ivs_cache['ts'] = now
    return result


def stream(request):
    is_live, recording_url, viewer_count = _check_ivs_live()
    stream_config = StreamConfig.load()
    context = {
        'is_live': is_live,
        'playback_url': settings.AWS_IVS_PLAYBACK_URL,
        'recording_url': recording_url or '',
        'viewer_count': viewer_count,
        'chat_room_id': settings.AWS_IVS_CHAT_ROOM_ARN.split('/')[-1] if settings.AWS_IVS_CHAT_ROOM_ARN else '',
        'stream_config': stream_config,
        'past_streams': StreamSession.objects.filter(is_published=True)[:3],
    }
    return render(request, "stream.html", context)


def stream_past(request):
    sessions = StreamSession.objects.filter(is_published=True)
    return render(request, "stream_past.html", {'sessions': sessions})


def stream_replay(request, pk):
    session = get_object_or_404(StreamSession, pk=pk, is_published=True)
    session.increment_view_count()
    return render(request, "stream_replay.html", {'session': session})


@require_GET
def stream_status(request):
    is_live, recording_url, viewer_count = _check_ivs_live()
    return JsonResponse({
        'is_live': is_live,
        'recording_url': recording_url or '',
        'playback_url': settings.AWS_IVS_PLAYBACK_URL if is_live else '',
        'viewer_count': viewer_count,
    })


@require_GET
def stream_chat_token(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'error': 'Username required'}, status=400)
    if len(username) > 50:
        return JsonResponse({'error': 'Username too long'}, status=400)

    chat_room_arn = settings.AWS_IVS_CHAT_ROOM_ARN
    if not chat_room_arn:
        return JsonResponse({'error': 'Chat not configured'}, status=503)

    try:
        import boto3
        client = boto3.client(
            'ivschat',
            region_name=settings.AWS_IVS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        response = client.create_chat_token(
            roomIdentifier=chat_room_arn,
            userId=username,
            attributes={'displayName': username},
            capabilities=['SEND_MESSAGE'],
        )
        return JsonResponse({
            'token': response['token'],
            'sessionExpirationTime': response['sessionExpirationTime'].isoformat(),
            'tokenExpirationTime': response['tokenExpirationTime'].isoformat(),
        })
    except Exception as e:
        logger.exception("Failed to create chat token")
        return JsonResponse({'error': 'Failed to generate chat token'}, status=500)


@require_POST
def stream_vod_view(request, pk):
    session = get_object_or_404(StreamSession, pk=pk, is_published=True)
    session.increment_view_count()
    return JsonResponse({'status': 'ok', 'view_count': session.view_count})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('portfolio:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            has_totp = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
            if has_totp:
                request.session['pre_2fa_user_id'] = user.pk
                request.session['pre_2fa_next'] = request.GET.get('next', '')
                return redirect('portfolio:verify_2fa')
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                parsed = urlparse(next_url)
                if not parsed.netloc and not parsed.scheme:
                    return redirect(next_url)
            return redirect('portfolio:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, "login.html")


def verify_2fa(request):
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('portfolio:login')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('portfolio:login')

    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip()
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        static_device = StaticDevice.objects.filter(user=user, confirmed=True).first()

        verified = False
        if device and device.verify_token(code):
            verified = True
        elif static_device and static_device.verify_token(code):
            verified = True

        if verified:
            login(request, user)
            next_url = request.session.pop('pre_2fa_next', '')
            request.session.pop('pre_2fa_user_id', None)
            if next_url:
                parsed = urlparse(next_url)
                if not parsed.netloc and not parsed.scheme:
                    return redirect(next_url)
            return redirect('portfolio:dashboard')
        else:
            messages.error(request, 'Invalid verification code.')

    return render(request, "verify_2fa.html")


@login_required
def setup_2fa(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if device:
        return redirect('portfolio:dashboard')

    pending_device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    if not pending_device:
        pending_device = TOTPDevice.objects.create(
            user=request.user,
            name='default',
            confirmed=False,
        )

    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip()
        if pending_device.verify_token(code):
            pending_device.confirmed = True
            pending_device.save()

            static_device, _ = StaticDevice.objects.get_or_create(
                user=request.user,
                name='backup',
                defaults={'confirmed': True},
            )
            static_device.token_set.all().delete()
            backup_codes = []
            for _ in range(8):
                token = secrets.token_hex(4)
                StaticToken.objects.create(device=static_device, token=token)
                backup_codes.append(token)

            return render(request, "dashboard/setup_2fa_complete.html", {
                'backup_codes': backup_codes,
            })
        else:
            messages.error(request, 'Invalid code. Try again.')

    import qrcode
    uri = pending_device.config_url
    uri = uri.replace('otpauth://totp/default', 'otpauth://totp/thecafedisco')
    img = qrcode.make(uri, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render(request, "dashboard/setup_2fa.html", {
        'qr_data': qr_b64,
        'secret_key': base64.b32encode(pending_device.bin_key).decode(),
    })


@login_required
@require_POST
def disable_2fa(request):
    TOTPDevice.objects.filter(user=request.user).delete()
    StaticDevice.objects.filter(user=request.user).delete()
    messages.success(request, '2FA has been disabled.')
    return redirect('portfolio:dashboard')


@login_required
def dashboard(request):
    context = {
        'career_count': CareerEntry.objects.count(),
        'skill_count': Skill.objects.count(),
        'profile_image_count': ProfileImage.objects.count(),
        'track_count': MusicTrack.objects.count(),
        'video_count': Video.objects.count(),
        'pending_comment_count': Comment.objects.filter(is_approved=False).count(),
        'stream_count': StreamSession.objects.count(),
        'has_2fa': TOTPDevice.objects.filter(user=request.user, confirmed=True).exists(),
    }
    return render(request, "dashboard.html", context)



@login_required
def music_list(request):
    tracks = MusicTrack.objects.all().order_by('-created_at')
    return render(request, "dashboard/music_list.html", {'tracks': tracks})


@login_required
def music_add(request):
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
    track = get_object_or_404(MusicTrack, pk=pk)
    title = track.title
    track.delete()
    messages.success(request, f'Track "{title}" deleted.')
    return redirect('portfolio:music_list')


@login_required
@require_POST
def music_toggle(request, pk):
    track = get_object_or_404(MusicTrack, pk=pk)
    track.is_published = not track.is_published
    track.save(update_fields=['is_published'])
    status = 'published' if track.is_published else 'unpublished'
    messages.success(request, f'Track "{track.title}" {status}.')
    return redirect('portfolio:music_list')



@login_required
def video_list(request):
    videos = Video.objects.all().order_by('-created_at')
    return render(request, "dashboard/video_list.html", {'videos': videos})


@login_required
def video_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category', '')
        youtube_url = request.POST.get('youtube_video_id', '')
        thumbnail = request.FILES.get('thumbnail')
        is_published = request.POST.get('is_published') == 'on'

        youtube_video_id = _extract_youtube_id(youtube_url) if youtube_url else ''

        if not title or not youtube_video_id:
            messages.error(request, 'Title and YouTube video ID are required.')
            return render(request, "dashboard/video_form.html", {'action': 'add'})

        Video.objects.create(
            title=title,
            category=category,
            youtube_video_id=youtube_video_id,
            thumbnail=thumbnail,
            is_published=is_published,
        )
        messages.success(request, f'Video "{title}" added successfully.')
        return redirect('portfolio:video_list')

    return render(request, "dashboard/video_form.html", {'action': 'add'})


@login_required
def video_edit(request, pk):
    video = get_object_or_404(Video, pk=pk)

    if request.method == 'POST':
        video.title = request.POST.get('title', video.title)
        video.category = request.POST.get('category', '')
        video.is_published = request.POST.get('is_published') == 'on'

        youtube_url = request.POST.get('youtube_video_id', '')
        if youtube_url:
            video.youtube_video_id = _extract_youtube_id(youtube_url)

        if request.FILES.get('thumbnail'):
            video.thumbnail = request.FILES['thumbnail']

        video.save()
        messages.success(request, f'Video "{video.title}" updated.')
        return redirect('portfolio:video_list')

    return render(request, "dashboard/video_form.html", {'action': 'edit', 'video': video})


@login_required
@require_POST
def video_delete(request, pk):
    video = get_object_or_404(Video, pk=pk)
    title = video.title
    video.delete()
    messages.success(request, f'Video "{title}" deleted.')
    return redirect('portfolio:video_list')


@login_required
@require_POST
def video_toggle(request, pk):
    video = get_object_or_404(Video, pk=pk)
    video.is_published = not video.is_published
    video.save(update_fields=['is_published'])
    status = 'published' if video.is_published else 'unpublished'
    messages.success(request, f'Video "{video.title}" {status}.')
    return redirect('portfolio:video_list')



@login_required
def career_list(request):
    entries = CareerEntry.objects.all().order_by('-start_date')
    return render(request, "dashboard/career_list.html", {'entries': entries})


@login_required
def career_add(request):
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
    entry = get_object_or_404(CareerEntry, pk=pk)
    title = entry.title
    entry.delete()
    messages.success(request, f'Career entry "{title}" deleted.')
    return redirect('portfolio:career_list')


@login_required
@require_POST
def career_toggle(request, pk):
    entry = get_object_or_404(CareerEntry, pk=pk)
    entry.is_published = not entry.is_published
    entry.save(update_fields=['is_published'])
    status = 'published' if entry.is_published else 'unpublished'
    messages.success(request, f'Career entry "{entry.title}" {status}.')
    return redirect('portfolio:career_list')



@login_required
def skill_list(request):
    skills = Skill.objects.all().order_by('category', 'name')
    return render(request, "dashboard/skill_list.html", {'skills': skills})


@login_required
def skill_add(request):
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
    skill = get_object_or_404(Skill, pk=pk)
    name = skill.name
    skill.delete()
    messages.success(request, f'Skill "{name}" deleted.')
    return redirect('portfolio:skill_list')


@login_required
@require_POST
def skill_toggle(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    skill.is_published = not skill.is_published
    skill.save(update_fields=['is_published'])
    status = 'published' if skill.is_published else 'unpublished'
    messages.success(request, f'Skill "{skill.name}" {status}.')
    return redirect('portfolio:skill_list')



@login_required
def profile_list(request):
    images = ProfileImage.objects.all().order_by('order')
    return render(request, "dashboard/profile_list.html", {'images': images})


@login_required
def profile_add(request):
    if request.method == 'POST':
        image = request.FILES.get('image')
        original = request.FILES.get('original_image')
        alt_text = request.POST.get('alt_text', '')
        order = request.POST.get('order', 0) or 0
        is_active = request.POST.get('is_active') == 'on'

        if not image:
            messages.error(request, 'Image file is required.')
            return render(request, "dashboard/profile_form.html", {'action': 'add'})

        ProfileImage.objects.create(
            image=image,
            original_image=original or image,
            alt_text=alt_text,
            order=int(order),
            is_active=is_active,
        )
        messages.success(request, 'Profile image uploaded.')
        return redirect('portfolio:profile_list')

    return render(request, "dashboard/profile_form.html", {'action': 'add'})


@login_required
def profile_edit(request, pk):
    profile = get_object_or_404(ProfileImage, pk=pk)

    if request.method == 'POST':
        profile.alt_text = request.POST.get('alt_text', '')
        profile.order = int(request.POST.get('order', 0) or 0)
        profile.is_active = request.POST.get('is_active') == 'on'

        original = request.FILES.get('original_image')
        if original:
            profile.original_image = original

        if request.FILES.get('image'):
            profile.image = request.FILES['image']

        profile.save()
        messages.success(request, 'Profile image updated.')
        return redirect('portfolio:profile_list')

    return render(request, "dashboard/profile_form.html", {'action': 'edit', 'profile': profile})


@login_required
@require_POST
def profile_delete(request, pk):
    profile = get_object_or_404(ProfileImage, pk=pk)
    profile.delete()
    messages.success(request, 'Profile image deleted.')
    return redirect('portfolio:profile_list')


@login_required
@require_POST
def profile_toggle(request, pk):
    profile = get_object_or_404(ProfileImage, pk=pk)
    profile.is_active = not profile.is_active
    profile.save(update_fields=['is_active'])
    status = 'activated' if profile.is_active else 'deactivated'
    messages.success(request, f'Profile image {status}.')
    return redirect('portfolio:profile_list')


@login_required
def profile_image_proxy(request, pk):
    profile = get_object_or_404(ProfileImage, pk=pk)
    source = profile.original_image if profile.original_image else profile.image
    return FileResponse(source.open('rb'), content_type='image/jpeg')


@require_POST
def submit_track_comment(request, pk):
    track = get_object_or_404(MusicTrack, pk=pk, is_published=True)

    username = request.POST.get('username', '').strip()
    comment_text = request.POST.get('comment_text', '').strip()
    honeypot = request.POST.get('website', '')  # Honeypot field for spam

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





@login_required
def comment_list(request):
    pending_comments = Comment.objects.filter(is_approved=False, track__isnull=False).order_by('-created_at')
    approved_comments = Comment.objects.filter(is_approved=True, track__isnull=False).order_by('-created_at')[:20]
    return render(request, "dashboard/comment_list.html", {
        'pending_comments': pending_comments,
        'approved_comments': approved_comments,
    })


@login_required
@require_POST
def comment_approve(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.is_approved = True
    comment.save(update_fields=['is_approved'])
    messages.success(request, f'Comment by "{comment.username}" approved.')
    return redirect('portfolio:comment_list')


@login_required
@require_POST
def comment_reject(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    username = comment.username
    comment.delete()
    messages.success(request, f'Comment by "{username}" rejected and deleted.')
    return redirect('portfolio:comment_list')


# =============================================================================
# Dashboard - Stream Sessions
# =============================================================================

@login_required
def stream_list(request):
    sessions = StreamSession.objects.all().order_by('-streamed_at')
    return render(request, "dashboard/stream_list.html", {'sessions': sessions})


@login_required
def stream_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        streamed_at = request.POST.get('streamed_at')
        ended_at = request.POST.get('ended_at') or None
        s3_recording_prefix = request.POST.get('s3_recording_prefix', '')
        vod_playlist_url = request.POST.get('vod_playlist_url', '')
        thumbnail_url = request.POST.get('thumbnail_url', '')
        is_published = request.POST.get('is_published') == 'on'

        if not title or not streamed_at:
            messages.error(request, 'Title and stream date are required.')
            return render(request, "dashboard/stream_form.html", {'action': 'add'})

        StreamSession.objects.create(
            title=title,
            description=description,
            streamed_at=streamed_at,
            ended_at=ended_at,
            s3_recording_prefix=s3_recording_prefix,
            vod_playlist_url=vod_playlist_url,
            thumbnail_url=thumbnail_url,
            is_published=is_published,
        )
        messages.success(request, f'Stream session "{title}" created.')
        return redirect('portfolio:stream_list')

    return render(request, "dashboard/stream_form.html", {'action': 'add'})


@login_required
def stream_edit(request, pk):
    session = get_object_or_404(StreamSession, pk=pk)

    if request.method == 'POST':
        session.title = request.POST.get('title', session.title)
        session.description = request.POST.get('description', '')
        streamed_at = request.POST.get('streamed_at')
        if streamed_at:
            session.streamed_at = streamed_at
        ended_at = request.POST.get('ended_at')
        session.ended_at = ended_at if ended_at else None
        session.s3_recording_prefix = request.POST.get('s3_recording_prefix', '')
        session.vod_playlist_url = request.POST.get('vod_playlist_url', '')
        session.thumbnail_url = request.POST.get('thumbnail_url', '')
        session.is_published = request.POST.get('is_published') == 'on'

        session.save()
        messages.success(request, f'Stream session "{session.title}" updated.')
        return redirect('portfolio:stream_list')

    return render(request, "dashboard/stream_form.html", {'action': 'edit', 'session': session})


@login_required
@require_POST
def stream_delete(request, pk):
    session = get_object_or_404(StreamSession, pk=pk)
    title = session.title
    session.delete()
    messages.success(request, f'Stream session "{title}" deleted.')
    return redirect('portfolio:stream_list')


@login_required
@require_POST
def stream_toggle(request, pk):
    session = get_object_or_404(StreamSession, pk=pk)
    session.is_published = not session.is_published
    session.save(update_fields=['is_published'])
    status = 'published' if session.is_published else 'unpublished'
    messages.success(request, f'Stream session "{session.title}" {status}.')
    return redirect('portfolio:stream_list')


@login_required
def stream_config_view(request):
    config = StreamConfig.load()

    if request.method == 'POST':
        config.placeholder_video_url = request.POST.get('placeholder_video_url', '')
        next_stream_date = request.POST.get('next_stream_date')
        config.next_stream_date = next_stream_date if next_stream_date else None
        config.next_stream_title = request.POST.get('next_stream_title', '')
        config.save()
        messages.success(request, 'Stream configuration updated.')
        return redirect('portfolio:stream_config')

    return render(request, "dashboard/stream_config.html", {'config': config})
