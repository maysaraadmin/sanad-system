from django.apps import AppConfig


class PdfReaderConfig(AppConfig):
    """
    Configuration class for the pdf_reader app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdf_reader'
    verbose_name = 'PDF Reader'
    
    def ready(self):
        """
        Override this method to perform initialization tasks.
        Import signals here to avoid AppRegistryNotReady exceptions.
        """
        # Import signals to register them
        import pdf_reader.signals  # noqa
