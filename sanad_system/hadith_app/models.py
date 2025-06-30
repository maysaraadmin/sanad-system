from django.db import models
from django.contrib.auth.models import User

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