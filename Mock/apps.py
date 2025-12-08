from django.apps import AppConfig
from django.db.utils import ProgrammingError, OperationalError
import sys # sys.argv ni olish uchun import qilinadi

class MockAppConfig(AppConfig):
    # Bu yerda ilovaning nomi va avtomatik maydon turi ko'rsatiladi
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Mock'
    verbose_name = "Mock Loyihasi" # Ilovaning O'zbekcha nomi

    def ready(self):
        """
        Dastur (App) to'liq yuklangandan so'ng ishga tushadi. 
        Asosiy ('SAT Makon') markazini bazada mavjudligini kafolatlaydi.
        """
        # Faqat 'makemigrations' yoki 'migrate' kabi baza bilan ishlaydigan 
        # komandalar ishlayotganda (jadval hali yaratilmagan bo'lishi mumkin)
        # bu mantiqni o'tkazib yuboramiz.
        if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
            return

        try:
            # Siklik bog'lanish (Circular Import) yuzaga kelmasligi uchun 
            # Modellarni 'ready' ichida import qilish tavsiya etiladi.
            from .models import Center
            
            DEFAULT_NAME = "SAT Makon"
            DEFAULT_SLUG = "satmakon"
            
            # 1. Ma'lumotlar bazasiga kirish.
            # Agar 'SAT Makon' mavjud bo'lmasa, uni yarat.
            if not Center.objects.filter(name=DEFAULT_NAME).exists():
                # Center modelida 'owner' (null=True) va 'registration_code' (save() da yaratiladi)
                # majburiy emasligi sababli, faqat 'name' va 'slug' yetarli.
                Center.objects.create(
                    name=DEFAULT_NAME,
                    slug=DEFAULT_SLUG,
                )
                print(f"|--- ASOSIY MA'LUMOTLAR: '{DEFAULT_NAME}' markazi avtomatik yaratildi. ---|")
            
        except (ProgrammingError, OperationalError):
            # Agar baza jadvali (Center) hali yaratilmagan bo'lsa yoki baza serveri ulanishga tayyor bo'lmasa.
            pass
        except Exception as e:
            # Boshqa kutilmagan xatoliklar.
            print(f"|--- DIQQAT XATO: AppConfig ichida asosiy markazni yaratishda xato: {e.__class__.__name__}: {e} ---|")
