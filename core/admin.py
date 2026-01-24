from django.contrib import admin
from .models import Post, Comment, Reaction, Tag, Report

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'like_count', 'comment_count', 'is_flagged')
    list_filter = ('created_at', 'is_flagged')
    search_fields = ('content', 'id')
    readonly_fields = ('id', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'created_at', 'content_snippet')
    search_fields = ('content',)

    def content_snippet(self, obj):
        return obj.content[:50]

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('post', 'reason', 'created_at', 'session_id')
    list_filter = ('reason', 'created_at')
    search_fields = ('post__content', 'reason')
