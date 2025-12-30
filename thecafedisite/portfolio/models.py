from django.db import models
from django.core.validators import FileExtensionValidator

# ============ HOME PAGE CONTENT ============

class CareerEntry(models.Model):
    """Career history timeline entries with 3 bullet points"""
    title = models.CharField(max_length=200, help_text="Job title")
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if current")

    # 3 bullet point descriptions (not a paragraph)
    bullet_1 = models.CharField(max_length=500, help_text="First responsibility/achievement")
    bullet_2 = models.CharField(max_length=500, help_text="Second responsibility/achievement")
    bullet_3 = models.CharField(max_length=500, help_text="Third responsibility/achievement")

    order = models.IntegerField(default=0, help_text="Display order (lower = first)")
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = "Career Entries"

    def __str__(self):
        return f"{self.title} at {self.company}"

    @property
    def is_current(self):
        return self.end_date is None


class Skill(models.Model):
    """Skills with categories and proficiency levels"""
    CATEGORY_CHOICES = [
        ('tech_frameworks', 'Technologies and Frameworks'),
        ('programming_languages', 'Programming Languages'),
        ('databases', 'Databases'),
        ('developer_tools', 'Developer Tools'),
    ]

    PROFICIENCY_CHOICES = [
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Proficient'),
        (4, 'Advanced'),
        (5, 'Expert'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=25, choices=CATEGORY_CHOICES)
    proficiency = models.IntegerField(choices=PROFICIENCY_CHOICES, default=3)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', '-proficiency', 'order']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class ProfileImage(models.Model):
    """Rotating profile images for home page"""
    image = models.ImageField(
        upload_to='profile/',
        help_text="Profile image (recommended: square, min 400x400px)"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Alt text for accessibility (e.g., 'Eddie at a music studio')"
    )
    order = models.IntegerField(default=0, help_text="Display order (lower = first)")
    is_active = models.BooleanField(default=True, help_text="Include in rotation")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Profile Images"

    def __str__(self):
        return f"Profile Image {self.order + 1}"


# ============ MUSIC PAGE ============

class MusicTrack(models.Model):
    """Music tracks with audio files and metadata (artist: thecafedisco)"""
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100, blank=True)
    release_date = models.DateField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True, help_text="Auto-calculated from file")

    # File uploads
    audio_file = models.FileField(
        upload_to='music/',
        validators=[FileExtensionValidator(allowed_extensions=['wav', 'mp3'])],
        help_text="Upload .wav or .mp3 file (max 100MB)"
    )
    cover_art = models.ImageField(
        upload_to='music/covers/',
        null=True,
        blank=True,
        help_text="Album artwork (optional)"
    )

    # Metadata
    is_published = models.BooleanField(default=True)
    play_count = models.IntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date', '-created_at']
        verbose_name_plural = "Music Tracks"

    def __str__(self):
        return self.title

    def increment_play_count(self):
        self.play_count += 1
        self.save(update_fields=['play_count'])


# ============ VIDEO PAGE ============

class Video(models.Model):
    """Video files with metadata"""
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, help_text="e.g., 'Tutorial', 'Demo', 'Showcase'")
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")

    # File uploads
    video_file = models.FileField(
        upload_to='videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm'])],
        help_text="Upload .mp4 file (1440p recommended, max 10GB)"
    )
    thumbnail = models.ImageField(
        upload_to='videos/thumbnails/',
        null=True,
        blank=True,
        help_text="Video thumbnail (auto-generated if not provided)"
    )

    # Metadata
    duration = models.DurationField(null=True, blank=True, help_text="Video length")
    resolution = models.CharField(max_length=20, blank=True, help_text="e.g., '1920x1080', '2560x1440'")
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name_plural = "Videos"

    def __str__(self):
        return self.title

    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


# ============ COMMENTS ============

class Comment(models.Model):
    """User comments on music tracks or videos"""
    # Can be associated with either a track or video (one must be set)
    track = models.ForeignKey(
        MusicTrack,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments'
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments'
    )

    # Comment content
    username = models.CharField(max_length=50, help_text="Display name")
    comment_text = models.TextField(max_length=1000)

    # Moderation
    is_approved = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.track.title if self.track else self.video.title if self.video else "Unknown"
        return f"{self.username} on {target}"

    @property
    def content_type(self):
        """Returns 'track' or 'video' based on which FK is set"""
        if self.track:
            return 'track'
        elif self.video:
            return 'video'
        return None
