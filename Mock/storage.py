# Mock/storage.py
import requests
from django.core.files.storage import Storage
from django.conf import settings
from django.utils.deconstruct import deconstructible
from urllib.parse import urljoin
from io import BytesIO

@deconstructible
class BunnyStorage(Storage):
    """
    Custom Bunny.net CDN Storage Backend for Django
    """
    def __init__(self):
        self.storage_zone = settings.BUNNY_STORAGE_ZONE_NAME
        self.password = settings.BUNNY_STORAGE_PASSWORD
        self.region = settings.BUNNY_REGION
        self.cdn_hostname = settings.BUNNY_CDN_HOSTNAME
        
        # Storage API endpoint (region bo'yicha)
        if self.region == 'de':
            self.storage_url = f'https://storage.bunnycdn.com/{self.storage_zone}/'
        else:
            self.storage_url = f'https://{self.region}.storage.bunnycdn.com/{self.storage_zone}/'
    
    def _normalize_name(self, name):
        """
        Fayl nomini tozalash va normallash
        """
        # Windows path separatorlarini o'chirish
        name = name.replace('\\', '/')
        # Boshidagi slash ni olib tashlash
        if name.startswith('/'):
            name = name[1:]
        return name
        
    def _open(self, name, mode='rb'):
        """
        Faylni Bunny.net dan o'qish
        """
        name = self._normalize_name(name)
        url = urljoin(self.storage_url, name)
        headers = {'AccessKey': self.password}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return BytesIO(response.content)
            else:
                raise IOError(f"Faylni o'qib bo'lmadi: {response.status_code}")
        except Exception as e:
            raise IOError(f"Bunny.net dan o'qishda xato: {str(e)}")
        
    def _save(self, name, content):
        """
        Faylni Bunny.net ga yuklash
        """
        name = self._normalize_name(name)
        url = urljoin(self.storage_url, name)
        headers = {
            'AccessKey': self.password,
            'Content-Type': 'application/octet-stream'
        }
        
        # Faylni boshidan o'qish
        content.seek(0)
        file_data = content.read()
        
        try:
            response = requests.put(url, headers=headers, data=file_data)
            
            if response.status_code in [200, 201]:
                return name
            else:
                raise Exception(f"Bunny upload failed: {response.status_code} - {response.text}")
        except Exception as e:
            raise Exception(f"Bunny.net ga yuklashda xato: {str(e)}")
    
    def delete(self, name):
        """
        Faylni o'chirish
        """
        name = self._normalize_name(name)
        url = urljoin(self.storage_url, name)
        headers = {'AccessKey': self.password}
        
        try:
            response = requests.delete(url, headers=headers)
            if response.status_code not in [200, 204]:
                print(f"Faylni o'chirishda ogohlantirish: {response.status_code}")
        except Exception as e:
            print(f"Bunny.net dan o'chirishda xato: {str(e)}")
    
    def exists(self, name):
        """
        Fayl mavjudligini tekshirish
        """
        name = self._normalize_name(name)
        url = urljoin(self.storage_url, name)
        headers = {'AccessKey': self.password}
        
        try:
            response = requests.head(url, headers=headers)
            return response.status_code == 200
        except:
            return False
    
    def url(self, name):
        """
        Faylning CDN URL manzilini qaytarish
        """
        name = self._normalize_name(name)
        # MUHIM: CDN hostname faqat https:// bilan
        return f'https://{self.cdn_hostname}/{name}'
    
    def size(self, name):
        """
        Fayl hajmini qaytarish
        """
        name = self._normalize_name(name)
        url = urljoin(self.storage_url, name)
        headers = {'AccessKey': self.password}
        
        try:
            response = requests.head(url, headers=headers)
            return int(response.headers.get('Content-Length', 0))
        except:
            return 0
    
    def get_accessed_time(self, name):
        """
        Fayl access vaqtini qaytarish (Bunny.net da mavjud emas)
        """
        return None
    
    def get_created_time(self, name):
        """
        Fayl yaratilgan vaqtini qaytarish (Bunny.net da mavjud emas)
        """
        return None
    
    def get_modified_time(self, name):
        """
        Fayl o'zgartirilgan vaqtini qaytarish (Bunny.net da mavjud emas)
        """
        return None


# ----------------------------------------------------
# MEDIA FILES — BUNNY.NET (Production)
# ----------------------------------------------------
if not DEBUG:
    # Custom storage class ishlatamiz
    DEFAULT_FILE_STORAGE = 'Mock.storage.BunnyStorage'

    # Bunny sozlamalari
    BUNNY_STORAGE_ZONE_NAME = config('BUNNY_STORAGE_ZONE_NAME')  # satmakonvideolari
    BUNNY_STORAGE_PASSWORD = config('BUNNY_STORAGE_PASSWORD')    # 761c7518-e520-416b-8f7af941bf23-d285-4374
    BUNNY_REGION = config('BUNNY_REGION', default='de')          # de
    BUNNY_CDN_HOSTNAME = config('BUNNY_CDN_PULL_ZONE_HOST')      # satmakon-cdn.b-cdn.net

    # MUHIM: MEDIA_URL CDN Pull Zone bo'lishi kerak
    MEDIA_URL = f'https://{BUNNY_CDN_HOSTNAME}/'
    
    # CKEditor uploads
    CKEDITOR_UPLOAD_PATH = "uploads/"

else:
    # Local development uchun
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    CKEDITOR_UPLOAD_PATH = "uploads/"
