from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import RAGConfiguration
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user-related data when a new user is created"""
    if created:
        logger.info(f"New user created: {instance.username}")


@receiver(post_save, sender=RAGConfiguration)
def handle_rag_config_change(sender, instance, created, **kwargs):
    """Handle changes to RAG configuration"""
    if created:
        logger.info(f"New RAG configuration created: {instance.name}")
    else:
        logger.info(f"RAG configuration updated: {instance.name}")
