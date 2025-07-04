from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Narrator, Hadith, Sanad, SanadNarrator, HadithCategory, HadithBook
from .forms import HadithForm

class SanadNarratorInline(admin.TabularInline):
    model = SanadNarrator
    extra = 1
    verbose_name = _('راوي السند')
    verbose_name_plural = _('رواة السند')

@admin.register(Narrator)
class NarratorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_year', 'death_year', 'get_reliability_display')
    search_fields = ('name', 'biography')
    list_filter = ('reliability',)
    fieldsets = (
        (None, {
            'fields': ('name', 'birth_year', 'death_year', 'biography')
        }),
        (_('معلومات التوثيق'), {
            'fields': ('reliability',)
        }),
    )

@admin.register(Hadith)
class HadithAdmin(admin.ModelAdmin):
    form = HadithForm
    list_display = ('short_text', 'source', 'get_grade_display', 'created_at')
    search_fields = ('text', 'source', 'source_hadith_number')
    list_filter = ('grade', 'categories', 'created_at')
    filter_horizontal = ('categories',)
    fieldsets = (
        (None, {
            'fields': ('text', 'source', 'grade', 'categories')
        }),
        (_('معلومات المصدر'), {
            'fields': ('source_page', 'source_hadith_number')
        }),
        (_('معلومات إضافية'), {
            'classes': ('collapse',),
            'fields': ('context', 'reference_page', 'reference_edition'),
        }),
    )
    
    def short_text(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    short_text.short_description = _('نص الحديث')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['source'].label = _('المصدر')
        form.base_fields['grade'].label = _('الدرجة')
        form.base_fields['categories'].label = _('التصنيفات')
        return form

@admin.register(Sanad)
class SanadAdmin(admin.ModelAdmin):
    list_display = ('hadith', 'is_mutawatir', 'created_at')
    list_filter = ('is_mutawatir', 'created_at')
    inlines = [SanadNarratorInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hadith')

@admin.register(HadithCategory)
class HadithCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name', 'description')
    list_filter = ('parent',)
    fields = ('name', 'parent', 'description')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].label = _('الاسم')
        form.base_fields['parent'].label = _('التصنيف الأب')
        form.base_fields['description'].label = _('الوصف')
        return form

@admin.register(HadithBook)
class HadithBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year_written')
    search_fields = ('title', 'author', 'description')
    list_filter = ('year_written',)
    fieldsets = (
        (None, {
            'fields': ('title', 'author', 'year_written')
        }),
        (_('وصف الكتاب'), {
            'fields': ('description',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['title'].label = _('العنوان')
        form.base_fields['author'].label = _('المؤلف')
        form.base_fields['year_written'].label = _('سنة التأليف')
        form.base_fields['description'].label = _('الوصف')
        return form