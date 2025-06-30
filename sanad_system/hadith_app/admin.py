from django.contrib import admin
from .models import Narrator, Hadith, Sanad, SanadNarrator, HadithCategory, HadithBook

class SanadNarratorInline(admin.TabularInline):
    model = SanadNarrator
    extra = 1

@admin.register(Narrator)
class NarratorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_year', 'death_year', 'reliability')
    search_fields = ('name', 'biography')
    list_filter = ('reliability',)

@admin.register(Hadith)
class HadithAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'source', 'grade', 'created_at')
    search_fields = ('text', 'source')
    list_filter = ('grade', 'categories')
    filter_horizontal = ('categories',)
    
    def short_text(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    short_text.short_description = "نص الحديث"

@admin.register(Sanad)
class SanadAdmin(admin.ModelAdmin):
    list_display = ('hadith', 'is_mutawatir')
    inlines = [SanadNarratorInline]

@admin.register(HadithCategory)
class HadithCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)

@admin.register(HadithBook)
class HadithBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year_written')
    search_fields = ('title', 'author')