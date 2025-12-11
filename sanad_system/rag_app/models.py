from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid


class RAGQuery(models.Model):
    """Store user queries and their responses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.TextField(verbose_name="السؤال")
    response = models.TextField(verbose_name="الإجابة")
    context_used = models.JSONField(default=list, verbose_name="السياق المستخدم")
    embedding_model = models.CharField(max_length=100, default="arabic-embedding", verbose_name="نموذج التضمين")
    llm_model = models.CharField(max_length=100, default="arabic-llm", verbose_name="نموذج اللغة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "استعلام RAG"
        verbose_name_plural = "استعلامات RAG"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.query[:50]}... - {self.created_at}"


class DocumentEmbedding(models.Model):
    """Store document embeddings for RAG system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.CharField(
        max_length=20,
        choices=[
            ('hadith', 'حديث'),
            ('narrator', 'راوي'),
            ('book', 'كتاب'),
            ('category', 'تصنيف')
        ],
        verbose_name="نوع المحتوى"
    )
    content_id = models.IntegerField(verbose_name="معرف المحتوى")
    text_content = models.TextField(verbose_name="نص المحتوى")
    embedding_vector = models.JSONField(verbose_name="متجه التضمين")
    embedding_model = models.CharField(max_length=100, default="arabic-embedding", verbose_name="نموذج التضمين")
    metadata = models.JSONField(default=dict, verbose_name="البيانات الوصفية")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "تضمين المستند"
        verbose_name_plural = "تضمينات المستندات"
        unique_together = ['content_type', 'content_id', 'embedding_model']
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()} - {self.content_id}"


class RAGConfiguration(models.Model):
    """Store RAG system configuration"""
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم الإعداد")
    embedding_model = models.CharField(max_length=100, verbose_name="نموذج التضمين")
    llm_model = models.CharField(max_length=100, verbose_name="نموذج اللغة")
    chunk_size = models.IntegerField(default=500, verbose_name="حجم الجزء")
    chunk_overlap = models.IntegerField(default=50, verbose_name="تداخل الأجزاء")
    max_context = models.IntegerField(default=5, verbose_name="الحد الأقصى للسياق")
    similarity_threshold = models.FloatField(default=0.7, verbose_name="عتبة التشابه")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "إعدادات RAG"
        verbose_name_plural = "إعدادات RAG"

    def __str__(self):
        return self.name
