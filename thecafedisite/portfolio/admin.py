from django.contrib import admin
from .models import CareerEntry, Skill, ProfileImage, MusicTrack, Video


@admin.register(CareerEntry)
class CareerEntryAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'start_date', 'end_date', 'is_current', 'is_published', 'order']
    list_filter = ['is_published', 'company']
    list_editable = ['order', 'is_published']
    search_fields = ['title', 'company', 'bullet_1', 'bullet_2', 'bullet_3']
    ordering = ['-start_date']
    fieldsets = (
        (None, {
            'fields': ('title', 'company', 'location')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Description (3 Bullet Points)', {
            'fields': ('bullet_1', 'bullet_2', 'bullet_3')
        }),
        ('Settings', {
            'fields': ('order', 'is_published')
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'proficiency', 'order', 'is_published']
    list_filter = ['category', 'proficiency', 'is_published']
    list_editable = ['order', 'proficiency', 'is_published']
    search_fields = ['name']
    ordering = ['category', '-proficiency', 'order']


@admin.register(ProfileImage)
class ProfileImageAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'alt_text', 'order', 'is_active']
    list_filter = ['is_active']
    list_editable = ['order', 'is_active']


@admin.register(MusicTrack)
class MusicTrackAdmin(admin.ModelAdmin):
    list_display = ['title', 'genre', 'release_date', 'duration', 'play_count', 'is_published']
    list_filter = ['is_published', 'genre', 'release_date']
    list_editable = ['is_published']
    search_fields = ['title', 'genre']
    readonly_fields = ['play_count', 'created_at', 'updated_at']
    ordering = ['-release_date', '-created_at']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'duration', 'resolution', 'view_count', 'order', 'is_published']
    list_filter = ['is_published', 'category']
    list_editable = ['order', 'is_published']
    search_fields = ['title', 'category', 'tags']
    readonly_fields = ['view_count', 'created_at', 'updated_at']
    ordering = ['order', '-created_at']
