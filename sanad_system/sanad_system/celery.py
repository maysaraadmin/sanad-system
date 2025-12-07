import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sanad_system.settings')

app = Celery('sanad_system')

# Configure Celery using settings from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Configure for memory broker
app.conf.update(
    task_always_eager=False,
    task_eager_propagates=True,
    worker_prefetch_multiplier=1,
)
