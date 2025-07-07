import os
import shutil
import os
import shutil
import datetime
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from hadith_app.models import Hadith, Narrator
from django.template.response import TemplateResponse

class CustomAdminSite(AdminSite):
    site_header = _('نظام السند - لوحة التحكم')
    site_title = _('نظام السند')
    index_title = _('لوحة التحكم')
    login_template = 'admin/login.html'
    logout_template = 'registration/logged_out.html'
    
    def get_system_stats(self):
        """Get system statistics and status."""
        User = get_user_model()
        
        # Calculate storage usage
        total, used, free = shutil.disk_usage('/')
        storage_total = f"{total // (2**30)} GB"
        storage_used = f"{used // (2**30)} GB"
        storage_percent = round((used / total) * 100, 1)
        
        # Check database status
        try:
            # Test database connection
            Hadith.objects.first()
            db_status = 'online'
        except:
            db_status = 'offline'
        
        # Get active users (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_users = User.objects.filter(last_login__gte=thirty_days_ago).count()
        
        return {
            'hadith_count': Hadith.objects.count(),
            'narrator_count': Narrator.objects.count(),
            'user_count': User.objects.count(),
            'active_users': active_users,
            'system_status': 'healthy' if db_status == 'online' else 'degraded',
            'database_status': db_status,
            'storage_status': 'ok' if storage_percent < 90 else 'warning',
            'storage_total': storage_total,
            'storage_used': storage_used,
            'storage_percent': storage_percent,
        }
    
    def get_recent_activities(self):
        """Generate sample recent activities."""
        now = timezone.now()
        return [
            {
                'type': 'success',
                'icon': 'user-plus',
                'message': _('New user registered: admin'),
                'time': '10:30 AM',
                'date': now.strftime('%b %d, %Y')
            },
            {
                'type': 'info',
                'icon': 'book',
                'message': _('New hadith added: #1234'),
                'time': 'Yesterday',
                'date': (now - timedelta(days=1)).strftime('%b %d, %Y')
            },
            {
                'type': 'warning',
                'icon': 'exclamation-triangle',
                'message': _('Storage usage is high (85% used)'),
                'time': 'Jul 6',
                'date': (now - timedelta(days=2)).strftime('%b %d, %Y')
            },
            {
                'type': 'error',
                'icon': 'server',
                'message': _('Database backup failed'),
                'time': 'Jul 5',
                'date': (now - timedelta(days=3)).strftime('%b %d, %Y')
            },
        ]
    
    def index(self, request, extra_context=None):
        """Override the admin index view to use our custom dashboard."""
        app_list = self.get_app_list(request)
        
        context = {
            **self.each_context(request),
            'title': self.index_title,
            'app_list': app_list,
            'stats': self.get_system_stats(),
            'recent_activities': self.get_recent_activities(),
            **(extra_context or {}),
        }
        
        request.current_app = self.name
        return TemplateResponse(request, 'admin/dashboard.html', context)
    
    def get_urls(self):
        urls = super().get_urls()
        return urls

# Use the custom admin site
admin_site = CustomAdminSite(name='customadmin')
