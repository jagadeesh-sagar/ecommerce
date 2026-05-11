import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

app = Celery('ecommerce')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto discover tasks.py in each installed app
app.autodiscover_tasks()