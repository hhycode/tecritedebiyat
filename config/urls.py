from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView

from core.sitemaps import BlogYazisiSitemap, KitapSitemap, StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "kitaplar": KitapSitemap,
    "blog": BlogYazisiSitemap,
}

urlpatterns = [
    path('admin/', include('core.admin_urls')),
    path('admin/', admin.site.urls),
    path('superadmin/', RedirectView.as_view(pattern_name='superadmin_dashboard', permanent=False)),
    path('django-admin/', RedirectView.as_view(pattern_name='superadmin_dashboard', permanent=False)),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots_txt'),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
