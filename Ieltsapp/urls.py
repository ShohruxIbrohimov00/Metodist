from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),   # MUHIM!
    path('', include('Mock.urls')),
    path('select2/', include('django_select2.urls')),
]

# Media fayllarni har doim serve qilish (Bunny CDN + local)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Debug rejimida static ham serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
