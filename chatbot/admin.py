

from django.contrib import admin
from .models import KnowledgeBase, KnowledgeBaseFile

class KnowledgeBaseFileInline(admin.TabularInline):
    model = KnowledgeBaseFile
    extra = 1

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_at')
    search_fields = ('name', 'company')
    list_filter = ('company', 'created_at')
    inlines = [KnowledgeBaseFileInline]