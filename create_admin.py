import os
import django
from django.contrib.auth import get_user_model

# Loyiha sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ieltsapp.settings')
django.setup()

User = get_user_model()

# Superuser ma'lumotlari
USERNAME = os.environ.get("DJANGO_SUPERUSER_USERNAME", "Shohrux")
EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL", "shohrux9066@gmail.com")
PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Salom1234") 

if not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
    print(f"Superuser '{USERNAME}' muvaffaqiyatli yaratildi.")
else:
    print(f"Superuser '{USERNAME}' allaqachon mavjud.")