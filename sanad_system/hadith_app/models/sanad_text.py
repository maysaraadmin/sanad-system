"""
Sanad Text Model

This module defines the SanadText model for storing specific text versions
for each sanad (chain of narrators) of a hadith.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class SanadText(models.Model):
    """
    Model to store the specific text narrated through a particular sanad.
    Each sanad can have its own text version of the hadith.
    """
    sanad = models.OneToOneField(
        'hadith_app.Sanad', 
        on_delete=models.CASCADE, 
        related_name='sanad_text',
        verbose_name=_("السند")
    )
    text = models.TextField(
        verbose_name=_("نص الحديث")
    )
    source_reference = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        verbose_name=_("المصدر المحدد")
    )
    variation_notes = models.TextField(
        null=True, 
        blank=True, 
        verbose_name=_("ملاحظات الاختلاف"),
        help_text=_("أي اختلافات في النص مقارنة بالنسخة الأساسية")
    )
    is_primary = models.BooleanField(
        default=False, 
        verbose_name=_("النص الأساسي"),
        help_text=_("هل هذا هو النص الأساسي للحديث؟")
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("تاريخ الإنشاء")
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("تاريخ التحديث")
    )
    
    class Meta:
        verbose_name = _("نص السند")
        verbose_name_plural = _("نصوص الأسانيد")
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
