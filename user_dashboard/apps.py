from django.apps import AppConfig
from django.conf import settings


class UserDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_dashboard'

    def ready(self):
        import user_dashboard.signals

        if getattr(settings, 'USE_S3', False):
            from django.core.files.storage import default_storage
            from storages.backends.s3boto3 import S3Boto3Storage
            default_storage._wrapped = S3Boto3Storage()
