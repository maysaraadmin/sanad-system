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
    birth_place = models.CharField(max_length=100, null=True, blank=True, verbose_name="مكان الميلاد")
    death_place = models.CharField(max_length=100, null=True, blank=True, verbose_name="مكان الوفاة")
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
    madhhab = models.CharField(
        max_length=50,
        choices=[
            ('hanafi', 'حنفي'),
            ('maliki', 'مالكي'),
            ('shafi', 'شافعي'),
            ('hanbali', 'حنبلي'),
            ('other', 'أخرى'),
            ('unknown', 'غير معروف')
        ],
        null=True,
        blank=True,
        verbose_name="المذهب"
    )
    teachers = models.ManyToManyField(
        'self',
        blank=True,
        related_name='students',
        verbose_name="الشيوخ",
        symmetrical=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "راوي"
        verbose_name_plural = "الرواة"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_reliability_display(self):
        reliability_choices = {
            'thiqa': 'ثقة',
            'saduq': 'صدوق',
            'weak': 'ضعيف',
            'unknown': 'مجهول'
        }
        return reliability_choices.get(self.reliability, self.reliability)
    
    def get_madhhab_display(self):
        madhhab_choices = {
            'hanafi': 'حنفي',
            'maliki': 'مالكي',
            'shafi': 'شافعي',
            'hanbali': 'حنبلي',
            'other': 'أخرى',
            'unknown': 'غير معروف'
        }
        return madhhab_choices.get(self.madhhab, self.madhhab)
    
    def get_age(self):
        """Calculate narrator's age"""
        if self.birth_year and self.death_year:
            return self.death_year - self.birth_year
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        if (
            self.birth_year is not None
            and self.death_year is not None
            and self.death_year < self.birth_year
        ):
            raise ValidationError(
                {'death_year': _('سنة الوفاة يجب أن تكون أكبر من أو تساوي سنة الميلاد.')}
            )
    
    def get_contemporaries(self):
        """Get narrators who lived during the same time period"""
        if not self.birth_year:
            return Narrator.objects.none()
        
        start_year = self.birth_year - 50
        end_year = self.death_year + 50 if self.death_year else self.birth_year + 120
        
        return Narrator.objects.filter(
            birth_year__gte=start_year,
            birth_year__lte=end_year
        ).exclude(id=self.id)
    
    def get_narration_locations(self):
        """Get unique locations where this narrator narrated hadiths"""
        from django.db.models import Count
        from .models import SanadNarrator, Sanad
        
        # This would need to be enhanced with actual location data
        # For now, return birth and death places
        locations = []
        if self.birth_place:
            locations.append(self.birth_place)
        if self.death_place and self.death_place != self.birth_place:
            locations.append(self.death_place)
        return locations
    
    def get_teacher_student_stats(self):
        """Get statistics about teachers and students"""
        teachers = self.teachers.all()
        students = self.students.all()
        
        return {
            'teachers_count': teachers.count(),
            'students_count': students.count(),
            'teachers': teachers,
            'students': students
        }

class Hadith(models.Model):
    # Keep the main text for backward compatibility and as primary text
    text = models.TextField(verbose_name="النص الأساسي للحديث")
    system_hadith_number = models.PositiveIntegerField(
        unique=True, 
        null=True,
        blank=True,
        verbose_name="الرقم التسلسلي للحديث",
        help_text="رقم فريد لكل حديث في النظام"
    )
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
    context = models.TextField(null=True, blank=True, verbose_name="سياق الحديث")
    reference_page = models.CharField(max_length=50, null=True, blank=True, verbose_name="صفحة المرجع")
    reference_edition = models.CharField(max_length=100, null=True, blank=True, verbose_name="طبعة المرجع")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="أضيف بواسطة",
        related_name='created_hadiths',
        editable=False
    )

    class Meta:
        verbose_name = "حديث"
        verbose_name_plural = "الأحاديث"
        ordering = ['-created_at']

    def __str__(self):
        primary_text = self.get_primary_text()
        if primary_text:
            return primary_text.text[:50] + "..." if len(primary_text.text) > 50 else primary_text.text
        return self.text[:50] + "..." if len(self.text) > 50 else self.text

    def save(self, *args, **kwargs):
        # Auto-generate system hadith number if not set — use SELECT FOR UPDATE to
        # prevent race conditions when two requests arrive simultaneously.
        if not self.system_hadith_number:
            from django.db import transaction
            with transaction.atomic():
                last_hadith = (
                    Hadith.objects.select_for_update()
                    .order_by('-system_hadith_number')
                    .first()
                )
                if last_hadith and last_hadith.system_hadith_number:
                    self.system_hadith_number = last_hadith.system_hadith_number + 1
                else:
                    self.system_hadith_number = 1
        super().save(*args, **kwargs)

    def get_primary_text(self):
        """Get the primary text version"""
        try:
            return self.texts.filter(is_primary=True).first()
        except:
            # Fallback to creating a primary text from the main text field
            if self.text:
                return HadithText.objects.create(
                    hadith=self,
                    text=self.text,
                    is_primary=True
                )
            return None
    
    def get_all_texts(self):
        """Get all text versions"""
        return self.texts.all()
    
    def get_text_count(self):
        """Get count of all text versions"""
        return self.texts.count()
    
    def get_grade_display(self):
        grade_choices = {
            'sahih': 'صحيح',
            'hasan': 'حسن',
            'daif': 'ضعيف',
            'mawdu': 'موضوع'
        }
        return grade_choices.get(self.grade, self.grade)


class HadithText(models.Model):
    """Multiple text versions for a single hadith"""
    hadith = models.ForeignKey(Hadith, on_delete=models.CASCADE, related_name='texts', verbose_name="الحديث")
    text = models.TextField(verbose_name="نص الحديث")
    source_reference = models.CharField(max_length=200, null=True, blank=True, verbose_name="المصدر المحدد")
    narrator_chain = models.TextField(null=True, blank=True, verbose_name="سلسلة الرواة")
    variation_notes = models.TextField(null=True, blank=True, verbose_name="ملاحظات الاختلاف")
    is_primary = models.BooleanField(default=False, verbose_name="النص الأساسي")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "نص الحديث"
        verbose_name_plural = "نصوص الحديث"
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"{self.hadith.text[:30]}... - {self.text[:30]}..."
    
    def save(self, *args, **kwargs):
        # If this is the first text, make it primary
        if not self.pk and not self.hadith.texts.exists():
            self.is_primary = True
        super().save(*args, **kwargs)


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
    narrator = models.ForeignKey(Narrator, on_delete=models.CASCADE, verbose_name="الراوي", related_name='narrations')
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

    def save(self, *args, **kwargs):
        # Delete old avatar file from disk when it is replaced, to prevent orphaned files.
        if self.pk:
            try:
                old_instance = UserProfile.objects.get(pk=self.pk)
                old_avatar = old_instance.avatar
                if old_avatar and old_avatar != self.avatar:
                    if os.path.isfile(old_avatar.path):
                        os.remove(old_avatar.path)
            except UserProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class TeacherStudentRelationship(models.Model):
    """
    Model to store the teacher-student relationship between narrators
    """
    teacher = models.ForeignKey(
        'hadith_app.Narrator', 
        on_delete=models.CASCADE, 
        related_name='student_relationships',
        verbose_name="الشيخ"
    )
    student = models.ForeignKey(
        'hadith_app.Narrator', 
        on_delete=models.CASCADE, 
        related_name='teacher_relationships',
        verbose_name="الطالب"
    )
    notes = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="ملاحظات",
        help_text="ملاحظات حول علاقة التلمذة أو المصادر"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "علاقة تلمذة"
        verbose_name_plural = "علاقات التلامذة"
        unique_together = ['teacher', 'student']
        ordering = ['teacher__name', 'student__name']
    
    def __str__(self):
        return f"{self.student.name} طالب عن {self.teacher.name}"


class SanadText(models.Model):
    """
    Model to store the specific text narrated through a particular sanad.
    Each sanad can have its own text version of the hadith.
    """
    sanad = models.OneToOneField(
        'hadith_app.Sanad', 
        on_delete=models.CASCADE, 
        related_name='sanad_text',
        verbose_name="السند"
    )
    text = models.TextField(verbose_name="نص الحديث")
    source_reference = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name="المصدر المحدد"
    )
    variation_notes = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="ملاحظات الاختلاف",
        help_text="أي اختلافات في النص مقارنة بالنسخة الأساسية"
    )
    is_primary = models.BooleanField(
        default=False, 
        verbose_name="النص الأساسي",
        help_text="هل هذا هو النص الأساسي للحديث؟"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "نص السند"
        verbose_name_plural = "نصوص الأسانيد"
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"نص سند {self.sanad.id}: {self.text[:50]}..."
    
    def get_short_text(self):
        """Get a shortened version of the text for display"""
        return self.text[:100] + "..." if len(self.text) > 100 else self.text
    
    @classmethod
    def get_primary_for_hadith(cls, hadith):
        """Get the primary sanad text for a hadith"""
        return cls.objects.filter(
            sanad__hadith=hadith, 
            is_primary=True
        ).first()
    
    def save(self, *args, **kwargs):
        # If this is the first sanad text for this hadith, make it primary
        if not self.pk and not SanadText.objects.filter(
            sanad__hadith=self.sanad.hadith
        ).exists():
            self.is_primary = True
        
        # If setting this as primary, unset others
        if self.is_primary:
            SanadText.objects.filter(
                sanad__hadith=self.sanad.hadith
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when User is saved"""
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()


@receiver(post_save, sender=Hadith)
def index_hadith_for_rag(sender, instance, created, **kwargs):
    """Automatically index hadith for RAG system when created or updated"""
    try:
        # Import here to avoid circular imports
        from rag_app.services import RAGService
        
        # Only index if the hadith has text content
        if instance.text or instance.texts.exists():
            rag_service = RAGService()
            rag_service.index_hadiths([instance.id])
            
            action = "created" if created else "updated"
            print(f"Automatically indexed hadith #{instance.system_hadith_number} for RAG after {action}")
            
    except Exception as e:
        # Log error but don't raise to avoid breaking hadith creation
        print(f"Error auto-indexing hadith #{instance.system_hadith_number}: {e}")
        pass
