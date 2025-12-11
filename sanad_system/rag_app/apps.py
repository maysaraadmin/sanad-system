from django.apps import AppConfig


class RagAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rag_app'
    verbose_name = 'RAG System'

    def ready(self):
        import rag_app.signals
