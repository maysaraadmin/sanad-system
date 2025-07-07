from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Narrator, Hadith, Sanad, SanadNarrator, HadithCategory, HadithBook
from .forms import HadithForm

# Import the custom admin site instance from urls.py
from sanad_system.urls import admin_site

# Get the User model
User = get_user_model()

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('المعلومات الشخصية'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('الصلاحيات'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('مهم'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['username'].label = _('اسم المستخدم')
        form.base_fields['password'].label = _('كلمة المرور')
        form.base_fields['first_name'].label = _('الاسم الأول')
        form.base_fields['last_name'].label = _('اسم العائلة')
        form.base_fields['email'].label = _('البريد الإلكتروني')
        form.base_fields['is_active'].label = _('نشط')
        form.base_fields['is_staff'].label = _('موظف')
        form.base_fields['is_superuser'].label = _('مدير النظام')
        form.base_fields['groups'].label = _('المجموعات')
        form.base_fields['user_permissions'].label = _('الصلاحيات')
        return form
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'groups':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(name__in=['محرر', 'مراجع', 'مدير'])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Register User model with our custom admin site
admin_site.register(User, CustomUserAdmin)

# Hadith Section
class SanadNarratorInline(admin.TabularInline):
    model = SanadNarrator
    extra = 1
    verbose_name = _('راوي السند')
    verbose_name_plural = _('رواة السند')
    autocomplete_fields = ['narrator']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'narrator':
            kwargs['queryset'] = Narrator.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class HadithAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_year', 'death_year', 'get_reliability_display', 'hadith_count')
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
    
    def hadith_count(self, obj):
        count = Hadith.objects.filter(asanid__narrators=obj).distinct().count()
        url = reverse('admin:hadith_app_hadith_changelist') + f'?narrator__id__exact={obj.id}'
        return format_html('<a href="{}">{} أحاديث</a>', url, count)
    hadith_count.short_description = _('عدد الأحاديث')
    hadith_count.admin_order_field = 'hadith_count'

class SanadInline(admin.TabularInline):
    model = Sanad
    extra = 1
    show_change_link = True
    fields = ('is_mutawatir', 'narrators_list', 'created_at')
    readonly_fields = ('narrators_list', 'created_at')
    
    def narrators_list(self, obj):
        return ", ".join([n.name for n in obj.narrators.all()])
    narrators_list.short_description = _('الرواة')

@admin.register(Hadith, site=admin_site)
class HadithAdmin(admin.ModelAdmin):
    form = HadithForm
    list_display = ('short_text', 'source', 'get_grade_display', 'sanad_count', 'created_at')
    search_fields = ('text', 'source', 'source_hadith_number')
    list_filter = ('grade', 'categories', 'created_at')
    filter_horizontal = ('categories',)
    inlines = [SanadInline]
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
    
    def sanad_count(self, obj):
        count = obj.asanid.count()
        url = reverse('admin:hadith_app_sanad_changelist') + f'?hadith__id__exact={obj.id}'
        return format_html('<a href="{}">{} أسانيد</a>', url, count)
    sanad_count.short_description = _('عدد الأسانيد')
    sanad_count.admin_order_field = 'sanad_count'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['source'].label = _('المصدر')
        form.base_fields['grade'].label = _('الدرجة')
        form.base_fields['categories'].label = _('التصنيفات')
        return form

# Sanad and Chain Section
class SanadAdmin(admin.ModelAdmin):
    list_display = ('hadith_link', 'narrators_list', 'is_mutawatir', 'created_at')
    list_filter = ('is_mutawatir', 'created_at')
    search_fields = ('hadith__text', 'narrators__name')
    inlines = [SanadNarratorInline]
    
    def hadith_link(self, obj):
        url = reverse('admin:hadith_app_hadith_change', args=[obj.hadith.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.hadith)[:100] + '...')
    hadith_link.short_description = _('الحديث')
    
    def narrators_list(self, obj):
        narrators = []
        for narrator in obj.narrators.all():
            url = reverse('admin:hadith_app_narrator_change', args=[narrator.id])
            narrators.append(f'<a href="{url}">{narrator.name}</a>')
        return mark_safe(" → ".join(narrators))
    narrators_list.short_description = _('سلسلة الرواة')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hadith')

# Categories and Books
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

# Narrators and Chain Details
class NarratorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_year', 'death_year', 'get_reliability_display', 'hadith_count')
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
    
    def hadith_count(self, obj):
        count = Hadith.objects.filter(asanid__narrators=obj).distinct().count()
        url = reverse('admin:hadith_app_hadith_changelist') + f'?narrator__id__exact={obj.id}'
        return format_html('<a href="{}">{} أحاديث</a>', url, count)
    hadith_count.short_description = _('عدد الأحاديث')
    hadith_count.admin_order_field = 'hadith_count'

class SanadNarratorAdmin(admin.ModelAdmin):
    list_display = ('sanad_link', 'narrator_link', 'order', 'narration_method')
    list_filter = ('narration_method',)
    search_fields = ('narrator__name', 'sanad__hadith__text')
    autocomplete_fields = ['narrator', 'sanad']
    
    def sanad_link(self, obj):
        url = reverse('admin:hadith_app_sanad_change', args=[obj.sanad.id])
        return format_html('<a href="{}">سند #{}</a>', url, obj.sanad.id)
    sanad_link.short_description = _('السند')
    sanad_link.admin_order_field = 'sanad__id'
    
    def narrator_link(self, obj):
        url = reverse('admin:hadith_app_narrator_change', args=[obj.narrator.id])
        return format_html('<a href="{}">{}</a>', url, obj.narrator.name)
    narrator_link.short_description = _('الراوي')
    narrator_link.admin_order_field = 'narrator__name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sanad', 'narrator')

# Register all models with the custom admin site
models_to_register = [
    (Hadith, HadithAdmin),
    (Sanad, SanadAdmin),
    (HadithCategory, HadithCategoryAdmin),
    (HadithBook, HadithBookAdmin),
    (Narrator, NarratorAdmin),
    (SanadNarrator, SanadNarratorAdmin)
]

for model, model_admin in models_to_register:
    if not admin_site.is_registered(model):
        admin_site.register(model, model_admin)