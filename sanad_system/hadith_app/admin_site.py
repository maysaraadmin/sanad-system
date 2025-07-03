from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class CustomAdminSite(AdminSite):
    site_header = _('نظام السند - لوحة التحكم')
    site_title = _('نظام السند')
    index_title = _('لوحة التحكم')
    
    def get_urls(self):
        urls = super().get_urls()
        return urls

admin_site = CustomAdminSite(name='customadmin')
