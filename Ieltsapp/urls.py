"""
URL configuration for Ieltsapp project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # CKEditor oʻzining rasmiy uploader URL lari (MUHIM!)
    path('ckeditor/', include('ckeditor_uploader.urls')),

    # Sizning app
    path('', include('Mock.urls')),

    # Select2
    path('select2/', include('django_select2.urls')),
]

# MEDIA fayllarni har doim serve qilish (productionda ham kerak!)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Agar DEBUG=True boʻlsa static ham serve qiladi (qulaylik uchun)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
