from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import os

def user_avatar_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/avatars/user_<id>/<filename>
    ext = filename.split('.')[-1]
    filename = f'avatar.{ext}'
    return os.path.join('avatars', f'user_{instance.user.id}', filename)

class Narrator(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الراوي")
    birth_year = models.IntegerField(null=True, blank=True, verbose_name="سنة الميلاد")
    death_year = models.IntegerField(null=True, blank=True, verbose_name="سنة الوفاة")
    biography = models.TextField(null=True, blank=True, verbose_name="السيرة الذاتية")
    reliability = models.CharField(
        max_length=20,
        choices=[
            ('thiqa', 'ثقة'),
            ('saduq', 'صدوق'),
            ('weak', 'ضعيف'),
            ('unknown', 'مجهول')
        ],
        verbose_name="درجة التوثيق"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "راوي"
        verbose_name_plural = "الرواة"
        ordering = ['name']

    def __str__(self):
        return self.name


class Hadith(models.Model):
    text = models.TextField(verbose_name="نص الحديث")
    source = models.CharField(max_length=200, verbose_name="المصدر")
    source_page = models.CharField(max_length=50, null=True, blank=True, verbose_name="الصفحة")
    source_hadith_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="رقم الحديث في المصدر")
    grade = models.CharField(
        max_length=20,
        choices=[
            ('sahih', 'صحيح'),
            ('hasan', 'حسن'),
            ('daif', 'ضعيف'),
            ('mawdu', 'موضوع')
        ],
        null=True,
        blank=True,
        verbose_name="درجة الحديث"
    )
    categories = models.ManyToManyField('HadithCategory', blank=True, verbose_name="التصنيفات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "حديث"
        verbose_name_plural = "الأحاديث"
        ordering = ['-created_at']

    def __str__(self):
        return self.text[:50] + "..." if len(self.text) > 50 else self.text


class Sanad(models.Model):
    hadith = models.ForeignKey(Hadith, on_delete=models.CASCADE, related_name='asanid', verbose_name="الحديث")
    narrators = models.ManyToManyField(Narrator, through='SanadNarrator', verbose_name="الرواة")
    is_mutawatir = models.BooleanField(default=False, verbose_name="متواتر")
    notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "الأسانيد"
        ordering = ['hadith']

    def __str__(self):
        return f"سند الحديث: {self.hadith.id}"


class SanadNarrator(models.Model):
    sanad = models.ForeignKey(Sanad, on_delete=models.CASCADE, verbose_name="السند")
    narrator = models.ForeignKey(Narrator, on_delete=models.CASCADE, verbose_name="الراوي")
    order = models.IntegerField(verbose_name="ترتيب الراوي في السند")
    narration_method = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="طريقة الرواية",
        help_text="مثل: حدثنا، أخبرنا، عن، أنبأنا"
    )

    class Meta:
        verbose_name = "راوي السند"
        verbose_name_plural = "رواة الأسانيد"
        ordering = ['sanad', 'order']
        unique_together = ('sanad', 'order')

    def __str__(self):
        return f"{self.narrator.name} (ترتيب: {self.order})"


class HadithCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")
    description = models.TextField(null=True, blank=True, verbose_name="الوصف")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="التصنيف الأب")

    class Meta:
        verbose_name = "تصنيف الحديث"
        verbose_name_plural = "تصنيفات الأحاديث"

    def __str__(self):
        return self.name


class HadithBook(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان الكتاب")
    author = models.CharField(max_length=100, verbose_name="المؤلف")
    year_written = models.IntegerField(null=True, blank=True, verbose_name="سنة التأليف")
    description = models.TextField(null=True, blank=True, verbose_name="الوصف")

    class Meta:
        verbose_name = "كتاب الحديث"
        verbose_name_plural = "كتب الحديث"

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('المستخدم')
    )
    
    # Personal Information
    bio = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('نبذة شخصية')
    )
    
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('تاريخ الميلاد')
    )
    
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('رقم الهاتف')
    )
    
    location = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('الموقع')
    )
    
    avatar = models.ImageField(
        upload_to=user_avatar_path,
        null=True,
        blank=True,
        verbose_name=_('الصورة الشخصية'),
        help_text=_('صورة الملف الشخصي')
    )
    
    # Preferences
    theme = models.CharField(
        max_length=10,
        choices=[
            ('light', _('فاتح')),
            ('dark', _('داكن')),
            ('system', _('تلقائي (حسب النظام)'))
        ],
        default='system',
        verbose_name=_('السمة')
    )
    
    # Social Links
    website = models.URLField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('الموقع الإلكتروني')
    )
    
    twitter = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('حساب تويتر')
    )
    
    facebook = models.URLField(
        null=True,
        blank=True,
        verbose_name=_('حساب فيسبوك')
    )
    
    # Activity tracking
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name=_('آخر نشاط')
    )
    
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('تم التحقق من البريد الإلكتروني')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    
    class Meta:
        verbose_name = _('ملف شخصي')
        verbose_name_plural = _('الملفات الشخصية')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username}\'s Profile'
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('profile')
    
    def get_initials(self):
        """Get user initials for avatar"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name[0]}{self.user.last_name[0]}".upper()
        elif self.user.first_name:
            return self.user.first_name[0].upper()
        elif self.user.username:
            return self.user.username[0].upper()
        return 'U'
    
    def get_avatar_url(self):
        """Return the avatar URL or a default"""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.png'


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when User is saved"""
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()