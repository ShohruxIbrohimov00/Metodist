# create_admin.py
import os
import django
from django.contrib.auth import get_user_model
from django.db import IntegrityError

# Loyiha sozlamalarini yuklash
# 'Ieltsapp.settings' o'rniga o'zingizning asosiy loyiha nomingizni qo'ying
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ieltsapp.settings')
django.setup()

User = get_user_model()

# Environment Variables'dan ma'lumotlarni olish
USERNAME = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "parol123") 

if not User.objects.filter(username=USERNAME).exists():
    try:
        User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
        print(f"Superuser '{USERNAME}' muvaffaqiyatli yaratildi (Avtomatik).")
    except IntegrityError:
        # Agar e-mail yoki username allaqachon mavjud bo'lsa
        print(f"Xatolik: Superuser yaratilmadi. E-mail/Username allaqachon mavjud bo'lishi mumkin.")
else:
    print(f"Superuser '{USERNAME}' allaqachon mavjud.")