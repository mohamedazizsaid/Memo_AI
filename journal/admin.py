from django.contrib import admin
from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'entry_date', 'mood', 'ai_status', 'word_count', 'created_at']
    list_filter = ['mood', 'ai_status', 'entry_date']
    search_fields = ['title', 'content', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at', 'word_count']
    date_hierarchy = 'entry_date'
