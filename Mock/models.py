from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.db.models import Q
from ckeditor_uploader.fields import RichTextUploadingField 
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from datetime import date
from django.utils.html import strip_tags 
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.db import transaction 
from django.core.files.storage import default_storage
import bleach
import re
 
class Center(models.Model):
    """
    Har bir alohida mijoz (O'quv Markazi) uchun asosiy model (Tenant).
    """
    name = models.CharField(max_length=255, verbose_name="Markaz nomi")
    slug = models.SlugField(unique=True,blank=False,  
        null=False, help_text="Sayt URL uchun unikal nom")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_centers',
        verbose_name="Bosh O'qituvchi / Ega"
    )
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_centers',
        blank=True,
        verbose_name="Markaz O'qituvchilari",
        help_text="Bu o'qituvchilar o'quvchilarni markazga qo'shish so'rovlarini tasdiqlashi mumkin."
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Aktiv (To'lov muddati o'tmagan)")



    @property
    def is_subscription_valid(self):
        try:
            latest_sub = self.subscriptions.filter(is_active=True).order_by('-end_date').first()
            if latest_sub:
                return latest_sub.end_date >= date.today()
            return False
        except AttributeError:
            return True
    
    def save(self, *args, **kwargs):
        """
        Markazni saqlash metodi: Faqat slugni avtomatik yaratishni o'z ichiga oladi.
        registration_code va is_primary logikasi butunlay olib tashlandi.
        """
        # 1. SLUGni avtomatik yaratish (Agar yaratilmagan bo'lsa)
        if not self.slug:
            self.slug = slugify(self.name)
            
        # is_primary ni tekshirish va boshqa markazlarni o'chirish logikasi olib tashlandi.
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "O'quv Markazi"
        verbose_name_plural = "O'quv Markazlari"

class CustomUser(AbstractUser):
    first_name = None
    last_name = None
    full_name = models.CharField(max_length=255, verbose_name="To'liq ism (F.I.Sh)")
    email = models.EmailField(unique=True, verbose_name="Elektron pochta")
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Telefon raqami")
    center = models.ForeignKey(
        Center,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name="O'quv Markazi"
    )
    ROLE_CHOICES = [
        ('student', "O'quvchi"),
        ('teacher', "O'qituvchi"),
        ('center_admin', "Markaz Admini"), 
        ('admin', "Platforma Super Admini"), 
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name="Foydalanuvchi roli")
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, verbose_name="Profil rasmi")
    bio = models.TextField(max_length=500, blank=True, verbose_name="O'zi haqida")
    ability = models.FloatField(default=0.0, verbose_name="Foydalanuvchi qobiliyati (Rasch)")
    teacher = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to=models.Q(role='teacher') | models.Q(role='center_admin'),
        related_name='students',
        verbose_name="Biriktirilgan Ustoz/Admin"
    )
    is_approved = models.BooleanField(default=True, verbose_name="Tasdiqlangan")
    is_banned = models.BooleanField(default=False, verbose_name="Bloklangan")

    USERNAME_FIELD = 'username' 
    REQUIRED_FIELDS = ['email', 'full_name'] 

    def is_center_active(self):
        if self.center:
            return self.center.is_subscription_valid
        return True

    def __str__(self):
        return self.username

    def get_full_name(self):
        return self.full_name.strip()

    def get_short_name(self):
        return self.full_name.strip().split(' ')[0]
    
    @property
    def balance(self):
        return self.balance_rel
    
    def has_active_subscription(self):
        """
        Foydalanuvchining aktiv obunasi bor-yo'qligini tekshiradi.
        """
        # UserSubscription modelini import qilingan deb hisoblaymiz
        try:
            from .models import UserSubscription
        except ImportError:
            # Agar boshqa joyda bo'lsa, to'g'ri joydan import qiling
            return False 

        return UserSubscription.objects.filter(
            user=self,
            end_date__gt=timezone.now() # Tugash sanasi hozirdan katta bo'lsa
        ).exists()
    
    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
  
class Group(models.Model):
    name = models.CharField(max_length=150, verbose_name="Guruh nomi")
    center = models.ForeignKey('Center', on_delete=models.CASCADE, related_name='groups')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_groups',
        limit_choices_to={'role__in': ['teacher', 'center_admin']},
        verbose_name="O'qituvchi"
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_groups',
        limit_choices_to={'role': 'student'},
        blank=True,
        verbose_name="O'quvchilar"
    )
    
    # YANGI: Kurslarga bog‘lash
    courses = models.ManyToManyField(
        'Course',
        related_name='groups_in_course',
        blank=True,
        verbose_name="Kurslar",
        help_text="Guruh bog'langan kurslar ro'yxati." 
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.center.name})"

    class Meta:
        unique_together = ('center', 'teacher', 'name')

class Subscription(models.Model):
    """
    O'quv markazining saytdan foydalanish muddatini boshqaradi.
    """
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name="O'quv Markazi"
    )
    start_date = models.DateField(auto_now_add=True, verbose_name="Boshlanish sanasi")
    end_date = models.DateField(verbose_name="Tugash sanasi")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To'lov miqdori")
    is_active = models.BooleanField(default=True, verbose_name="To'lov aktivmi?")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.center.is_active = self.center.is_subscription_valid
        self.center.save()

    def __str__(self):
        return f"{self.center.name} - {self.end_date} gacha"
    
    class Meta:
        verbose_name = "Obuna"
        verbose_name_plural = "Obunalar"

class SystemConfiguration(models.Model):
    """
    Tizimning global sozlamalarini saqlash uchun yagona model (Singleton).
    """
    question_calibration_threshold = models.PositiveIntegerField(
        default=30,
        verbose_name="Savolni kalibrovka qilish uchun minimal javoblar soni",
        help_text="Savolning qiyinlik darajasi shu sondagi javoblardan so'ng avtomatik hisoblanadi."
    )
    solutions_enabled = models.BooleanField(default=True, verbose_name="Savol yechimlarini yoqish")
    default_solutions_are_free = models.BooleanField(
        default=False,
        verbose_name="Standart holatda yechimlar bepulmi?",
        help_text="Agar bu yoqilgan bo'lsa, 'Yechim bepulmi?' deb belgilanmagan barcha savollar yechimi pullik bo'ladi."
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Tizimning global sozlamalari"

    class Meta:
        verbose_name = "Tizim sozlamasi"
        verbose_name_plural = "Tizim sozlamalari"

class SiteSettings(models.Model):
    payment_card_number = models.CharField(max_length=20, help_text="To'lov qabul qilinadigan plastik karta raqami. Format: 8600 1234 ...")
    payment_card_holder = models.CharField(max_length=100, help_text="Karta egasining ismi va familiyasi. Masalan: ALI VALIYEV")
    manager_phone_number = models.CharField(max_length=20, help_text="To'lovni tezkor tasdiqlash uchun menejer telefon raqami. Format: +998901234567")
    manager_telegram_username = models.CharField(max_length=100, blank=True, help_text="Menejerning telegram username'i (masalan, @menejer_username)")

    def __str__(self):
        return "Sayt Sozlamalari"

    class Meta:
        verbose_name = "Sayt Sozlamalari"
        verbose_name_plural = "Sayt Sozlamalari"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Promo kod"))
    DISCOUNT_TYPE_CHOICES = [('percentage', _('Foiz')), ('fixed', _('Fiks summa'))]
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage',
                                     verbose_name=_("Chegirma turi"))
    discount_percent = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Chegirma foizi"),
        help_text=_("Foiz chegirmasi uchun, masalan, 10% uchun 10 kiriting (0-100 oralig'ida bo'lishi kerak)")
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_("Fiks chegirma summasi"),
        help_text=_("Fiks summa chegirmasi uchun, masalan, 50000 so'm")
    )
    valid_from = models.DateTimeField(default=timezone.now, verbose_name=_("Amal qilish boshlanishi"))
    valid_until = models.DateTimeField(verbose_name=_("Amal qilish tugashi"))
    max_uses = models.PositiveIntegerField(default=1, verbose_name=_("Maksimal ishlatishlar soni"))
    used_count = models.PositiveIntegerField(default=0, editable=False, verbose_name=_("Ishlatilganlar soni"))
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='promo_codes', verbose_name=_("O'quv Markazi")
    )

    def clean(self):
        super().clean()
        if self.discount_type == 'percentage':
            if self.discount_percent is None:
                raise ValidationError(_("Foiz chegirmasi uchun 'discount_percent' to'ldirilishi kerak."))
            if not (0 <= self.discount_percent <= 100):
                 raise ValidationError(_("Chegirma foizi 0 dan 100 gacha bo'lishi kerak."))

        elif self.discount_type == 'fixed':
            if self.discount_amount is None:
                raise ValidationError(_("Fiks summa chegirmasi uchun 'discount_amount' to'ldirilishi kerak."))
            
        # Ikkala chegirma turiga ham to'ldirilmaganligini tekshirish
        if self.discount_type == 'percentage' and self.discount_amount is not None:
             raise ValidationError(_("Agar chegirma turi foiz bo'lsa, 'Fiks chegirma summasi' bo'sh bo'lishi kerak."))
        if self.discount_type == 'fixed' and self.discount_percent is not None:
             raise ValidationError(_("Agar chegirma turi fiks bo'lsa, 'Chegirma foizi' bo'sh bo'lishi kerak."))


    def is_valid(self):
        now = timezone.now()
        # Qiyosni > dan >= ga o'zgartirdim, chunki tugash vaqti ham muhim
        return self.is_active and self.valid_from <= now and self.valid_until > now and self.used_count < self.max_uses

    def __str__(self):
        if self.discount_type == 'percentage':
            return f"{self.code} ({self.discount_percent}%)"
        return f"{self.code} ({self.discount_amount} so'm)"

    class Meta:
        verbose_name = _("Promo kod")
        verbose_name_plural = _("Promo kodlar")

class ExamPackage(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Paket nomi"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Tavsif"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Narxi (so'mda)"))
    includes_flashcards = models.BooleanField(default=False, verbose_name=_("Flashcardlar to'plamini o'z ichiga oladimi?"))
    exam_credits = models.PositiveIntegerField(verbose_name=_("Beriladigan imtihonlar soni (kredit)"))
    solution_view_credits_on_purchase = models.PositiveIntegerField(
        default=0, verbose_name=_("Beriladigan yechimlar soni (kredit)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))
    # 'Exam' modeliga M2M aloqasi
    exams = models.ManyToManyField('Exam', related_name='packages', blank=True, verbose_name=_("Paketdagi imtihonlar"))
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='exam_packages', verbose_name=_("O'quv Markazi")
    )

    def __str__(self):
        return f"{self.name} - {self.exam_credits} imtihon / {self.solution_view_credits_on_purchase} yechim ({self.price} so'm)"

    class Meta:
        verbose_name = _("Imtihon paketi")
        verbose_name_plural = _("Imtihon paketlari")

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Obuna rejasi nomi"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Tavsif"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Narxi (so'mda)"))
    duration_days = models.PositiveIntegerField(verbose_name=_("Amal qilish muddati (kunda)"))
    includes_flashcards = models.BooleanField(default=False, verbose_name=_("Flashcardlar to'plamini o'z ichiga oladimi?"))
    includes_solution_access = models.BooleanField(
        default=False, verbose_name=_("Yechimlarni ko'rishni o'z ichiga oladimi?")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))

    def __str__(self):
        return f"{self.name} - {self.duration_days} kun ({self.price} so'm)"

    class Meta:
        verbose_name = _("Obuna rejasi")
        verbose_name_plural = _("Obuna rejalari")

class UserBalance(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='balance',
                                 verbose_name=_("Foydalanuvchi"))
    exam_credits = models.PositiveIntegerField(default=0, verbose_name=_("Mavjud imtihon kreditlari"))
    solution_view_credits = models.PositiveIntegerField(default=0, verbose_name=_("Mavjud yechim kreditlari"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.exam_credits} imtihon / {self.solution_view_credits} yechim"

    class Meta:
        verbose_name = _("Foydalanuvchi balansi")
        verbose_name_plural = _("Foydalanuvchi balanslari")

class UserSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription',
                                 verbose_name=_("Foydalanuvchi"))
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, verbose_name=_("Obuna rejasi"))
    start_date = models.DateTimeField(verbose_name=_("Boshlangan sana"))
    end_date = models.DateTimeField(verbose_name=_("Tugash sana"))
    auto_renewal = models.BooleanField(default=False, verbose_name=_("Avtomatik uzaytirish"))
    
    # Yangi maydon: uzaytirilganda oldingi tugash sanasidan hisoblash uchun
    is_ever_active = models.BooleanField(default=False, editable=False, verbose_name=_("Avval faol bo'lganmi"))


    def is_active(self):
        return self.end_date > timezone.now()

    is_active.boolean = True
    is_active.short_description = _("Aktivmi?")

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'Yoq'} ({'Aktiv' if self.is_active() else 'Aktiv emas'})"

    class Meta:
        verbose_name = _("Foydalanuvchi obunasi")
        verbose_name_plural = _("Foydalanuvchi obunalari")

class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', _('To\'lov kutilmoqda')),
        ('moderation', _('Tekshirilmoqda')),
        ('completed', _('Tasdiqlangan')),
        ('rejected', _('Rad etilgan')),
    ]
    PURCHASE_TYPE_CHOICES = [('package', _('Paket')), ('subscription', _('Obuna')),('course', _('Kurs'))]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchases', verbose_name=_("Foydalanuvchi"))
    purchase_type = models.CharField(max_length=20, choices=PURCHASE_TYPE_CHOICES, verbose_name=_("Xarid turi"))
    package = models.ForeignKey(ExamPackage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Paket"))
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Obuna rejasi"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Boshlang'ich summa"))
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Promo kod"))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Yakuniy summa"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name=_("Holati"))
    payment_screenshot = models.FileField(upload_to='screenshots/%Y/%m/', null=True, blank=True, verbose_name=_("To'lov skrinshoti"))
    payment_comment = models.TextField(blank=True, null=True, verbose_name=_("To'lovga izoh"))
    course = models.ForeignKey(
        'Course', # Yuqoridagi Course modeliga bog'lanadi
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Kurs")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Xarid #{self.id} - {self.user.username if self.user else 'Noma`lum'}"

    @transaction.atomic
    def fulfill(self):
        """
        To‘lov tasdiqlanganda foydalanuvchiga obuna yoki kredit beradi.
        Muhim: status='completed' bo‘lsa HAM ishlaydi — chunki approve_payment da chaqiriladi!
        """
        # XATO: Bu qatorni o‘chirib tashlang!
        # if self.status == 'completed':
        #     return

        now = timezone.now()

        # 1. Promokod hisoblash
        if self.promo_code and self.promo_code.is_valid():
            self.promo_code.used_count = models.F('used_count') + 1
            self.promo_code.save(update_fields=['used_count'])

        # 2. Obuna rejasi sotilgan bo‘lsa
        if self.purchase_type == 'subscription' and self.subscription_plan:
            plan = self.subscription_plan

            user_sub, created = UserSubscription.objects.get_or_create(
                user=self.user,
                defaults={
                    'plan': plan,
                    'start_date': now,
                    'end_date': now + timedelta(days=plan.duration_days),
                    'is_ever_active': True,
                }
            )

            if not created:
                # Mavjud obuna bor
                if user_sub.end_date > now:
                    # Hozirgi obuna hali tugamagan → qo‘shib uzaytiramiz
                    user_sub.end_date += timedelta(days=plan.duration_days)
                else:
                    # Tugagan → yangidan boshlaymiz
                    user_sub.start_date = now
                    user_sub.end_date = now + timedelta(days=plan.duration_days)
                user_sub.plan = plan
                user_sub.is_ever_active = True
                user_sub.save()

        # 3. Paket sotilgan bo‘lsa — kredit beramiz
        elif self.purchase_type == 'package' and self.package:
            balance, _ = UserBalance.objects.get_or_create(user=self.user, defaults={'exam_credits': 0, 'solution_view_credits': 0})
            balance.exam_credits = models.F('exam_credits') + self.package.exam_credits
            balance.solution_view_credits = models.F('solution_view_credits') + self.package.solution_view_credits_on_purchase
            balance.save(update_fields=['exam_credits', 'solution_view_credits'])
        
        # 4. Kurs sotilgan bo'lsa
        if self.purchase_type == 'course' and self.course:
            # Foydalanuvchini kursga yozamiz
            # DIQQAT: Kurslar Group modeli orqali bog'langan bo'lsa,
            # foydalanuvchini kursga biriktirilgan 'default' yoki maxsus guruhga qo'shish kerak.
            
            # --- MISOL uchun soddalashtirilgan mantiq: ---
            
            # 1. Kursga tegishli bo'lgan guruhni topamiz
            # Sizning tizimingizda qandaydir 'default' guruh yoki to'lovchi-talabalar guruhi bo'lishi kerak
            try:
                # Eslatma: Course modelida 'groups_in_course' ForeignKey bor deb faraz qilamiz
                default_group = self.course.groups_in_course.first() 
                if default_group:
                    default_group.students.add(self.user)
                
            except AttributeError:
                # Agar Course modelida students/groups bog'lanishi boshqacha bo'lsa, uni to'g'irlash kerak
                # Masalan, bevosita M2M aloqa bo'lsa: self.course.students.add(self.user)
                pass 
            # ---------------------------------------------
        # 5. Statusni oxirida o‘zgartiramiz (fulfill tugagandan keyin!)
        self.status = 'completed'
        self.save(update_fields=['status', 'updated_at'])


    class Meta:
        verbose_name = _("Xarid")
        verbose_name_plural = _("Xaridlar")
        ordering = ['-created_at']

# =================================================================
# 2. Flashcard Modellariga Kiritilgan O'zgarishlar
# =================================================================
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

class Tag(models.Model):
    """
    Flashcardlar uchun mavzu/teg model. Endi URL manziliga ta'sir qilmaydi.
    """
    name = models.CharField(max_length=100, verbose_name=_("Teg/Mavzu nomi"))
    
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children',
        verbose_name=_("Ota-ona teg (yuqori darajali mavzu)")
    )
    
    description = models.TextField(
        blank=True, null=True, verbose_name=_("Tavsif"),
        help_text=_("Ushbu teg/mavzu haqida qisqacha ma'lumot")
    )
    
    # 'Center' modeli shu faylda yoki boshqa appda import qilingan deb faraz qilinadi
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='tags', verbose_name=_("Tegishli Markaz"), null=True
    )
    
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan vaqt"))
    # models.py → Tag class ichiga qo‘shing (oxiriga yoki istalgan joyga)

    def get_full_hierarchy(self):
        """
        Masalan: Matematika → Algebra → Chiziqli tenglamalar
        Yoki: Ingliz tili → Grammar → Present Simple
        """
        hierarchy = []
        current = self
        
        while current:
            hierarchy.append(current.name)
            current = current.parent
        
        return " → ".join(reversed(hierarchy))
    
    def __str__(self):
        # Center ID bilan ko'rsatish, agar center mavjud bo'lsa
        center_info = f" (Center: {self.center_id})" if self.center_id else ""
        if self.parent:
            return f"{self.parent.name} > {self.name}{center_info}"
        return f"{self.name}{center_info}"

    # ❌ Avtomatik slug yaratish uchun save() metodi olib tashlangan

    class Meta:
        verbose_name = _("Teg/Mavzu")
        verbose_name_plural = _("Teglar/Mavzular")
        
    
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['parent']),
        ]

class UserTagPerformance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tag_performances')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='user_performances')
    correct_answers = models.PositiveIntegerField(default=0, verbose_name=_("To'g'ri javoblar soni"))
    incorrect_answers = models.PositiveIntegerField(default=0, verbose_name=_("Noto'g'ri javoblar soni"))
    total_time_spent = models.PositiveIntegerField(default=0, verbose_name=_("Sarflangan umumiy vaqt (soniya)"))
    attempts_count = models.PositiveIntegerField(default=0, verbose_name=_("Urinishlar soni"))
    average_difficulty = models.FloatField(default=0.0, verbose_name=_("O'rtacha qiyinlik (Rasch)"))
    last_attempted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Oxirgi urinilgan vaqt"))

    class Meta:
        verbose_name = _("Foydalanuvchi teg/mavzu bo'yicha ko'rsatkichi")
        verbose_name_plural = _("Foydalanuvchi teglar/mavzular bo'yicha ko'rsatkichlari")
        unique_together = ('user', 'tag')

    def __str__(self):
        return f"{self.user.username} - {self.tag.name}"

    def success_rate(self):
        total = self.correct_answers + self.incorrect_answers
        return (self.correct_answers / total * 100) if total > 0 else 0.0
 
class Flashcard(models.Model):
    # CKEditor matnini tozalash uchun yordamchi metod
    def _clean_apostrophes(self, text):
        if not text:
            return text
        text = str(text).replace('‘', "'").replace('’', "'").replace('`', "'")
        return text

    CONTENT_TYPE_CHOICES = [
        ('word', _("So'z/Ibora")), 
        ('formula', _("Formula"))
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='word', verbose_name=_("Kontent turi"))
    english_content = models.TextField(verbose_name=_("Inglizcha kontent (HTML)"), help_text=_("CKEditor kodi bu yerda to'g'ridan-to'g'ri bo'lishi kerak"))
    uzbek_meaning = models.TextField(verbose_name=_("O'zbekcha ma'nosi (HTML)"))
    context_sentence = models.TextField(blank=True, null=True, verbose_name=_("Kontekst (gap) (HTML)"))
    author = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='flashcards', verbose_name=_("Muallif"), null=True) 
    source_question = models.ForeignKey( 'Question', on_delete=models.SET_NULL, related_name='associated_flashcards', verbose_name=_("Manba-savol"), null=True, blank=True)
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='flashcards', verbose_name=_("Tegishli Markaz"), null=True
    )

    # *** YAXSHILASH: Tag modelini qo'shish ***
    # Bu maydon Flashcardni bir yoki bir nechta mavzuga/fanga bog'laydi.
    tags = models.ManyToManyField('Tag', related_name='flashcards', blank=True, verbose_name=_("Tegishli Taglar/Mavzular"))
    # *****************************************

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Flashcard (lug'at)")
        verbose_name_plural = _("Flashcardlar (lug'atlar)")
        unique_together = ('english_content', 'center') 
        ordering = ['english_content']

    # ... qolgan metodlar (save va __str__) o'zgarishsiz qoladi.
    def save(self, *args, **kwargs):
        """Ma'lumotlar bazasiga saqlashdan oldin CKEditor matnlaridagi 
        O'zbekcha apostrof xatolarini to'g'irlaydi."""
        
        # Barcha matn maydonlarini tozalash
        self.uzbek_meaning = self._clean_apostrophes(self.uzbek_meaning)
        self.english_content = self._clean_apostrophes(self.english_content)
        if self.context_sentence:
            self.context_sentence = self._clean_apostrophes(self.context_sentence)
            
        super().save(*args, **kwargs)

    def __str__(self):
        """Obyektni odam o'qishi uchun qisqa va toza formatda qaytaradi."""
        # bleach kutubxonasini import qilishni unutmang, agar u sizning kodingizda bo'lsa
        try:
            import bleach
        except ImportError:
            # Agar bleach import qilinmagan bo'lsa, oddiy qisqartirish
            cleaned_english_content = (self.english_content or '')[:50]
            cleaned_uzbek_meaning = (self.uzbek_meaning or '')[:50]
            return f"{cleaned_english_content} - {cleaned_uzbek_meaning}"
            
        cleaned_english_content = self._clean_apostrophes(bleach.clean(self.english_content or '', tags=[], strip=True))
        cleaned_uzbek_meaning = self._clean_apostrophes(bleach.clean(self.uzbek_meaning or '', tags=[], strip=True))
        
        return f"{cleaned_english_content[:50]} - {cleaned_uzbek_meaning[:50]}"

class UserFlashcardStatus(models.Model):
    STATUS_CHOICES = [('not_learned', _('O\'rganilmagan')), ('learning', _('O\'rganilmoqda')), ('learned', _('O\'rganilgan'))]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flashcard_statuses')
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name='user_statuses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_learned', db_index=True,
                             verbose_name=_("O'zlashtirish holati"))
    last_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Oxirgi ko'rilgan vaqt"))
    next_review_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_("Keyingi takrorlash vaqti"))
    ease_factor = models.FloatField(default=2.5, verbose_name=_("Osonlik faktori (SM2)"))
    review_interval = models.PositiveIntegerField(default=1, verbose_name=_("Takrorlash intervali (kunda)"))
    repetition_count = models.PositiveIntegerField(default=0, verbose_name=_("Muvaffaqiyatli takrorlash soni"))
    last_quality_rating = models.PositiveSmallIntegerField(default=5, verbose_name=_("Oxirgi baho (0-5)"))

    class Meta:
        verbose_name = _("Foydalanuvchi flashcard holati (SM2)")
        verbose_name_plural = _("Foydalanuvchi flashcard holatlari (SM2)")
        unique_together = ('user', 'flashcard')

    def __str__(self):
        return f"{self.user.username} - {self.flashcard.english_content[:30]}: {self.get_status_display()}"

class FlashcardReviewLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flashcard_reviews')
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name='reviews_log')
    quality_rating = models.PositiveSmallIntegerField(verbose_name=_("Sifat bahosi (0-5)"))
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ko'rib chiqish vaqti"))
    
    class Meta:
        verbose_name = _("Flashcard takrorlash logi")
        verbose_name_plural = _("Flashcard takrorlash loglari")
        ordering = ['-reviewed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.flashcard.english_content[:30]} - Baho: {self.quality_rating}"

class UserFlashcardDeck(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flashcard_decks')
    title = models.CharField(max_length=200, verbose_name=_("To'plam nomi"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Tavsif"))
    flashcards = models.ManyToManyField(Flashcard, blank=True, verbose_name=_("To'plamdagi kartochkalar"))
    created_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='flashcard_decks', verbose_name=_("Tegishli Markaz"), null=True
    )

    class Meta:
        verbose_name = _("Shaxsiy flashcard to'plami")
        verbose_name_plural = _("Shaxsiy flashcard to'plamlari")

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class FlashcardExam(models.Model):
    source_exam = models.OneToOneField('Exam', on_delete=models.CASCADE, related_name='flashcard_exam',
                                     verbose_name=_("Asosiy imtihon"))
    title = models.CharField(max_length=255, verbose_name=_("Flashcard mashg'ulot nomi"))
    flashcards = models.ManyToManyField('Flashcard', related_name='flashcard_exams', blank=True, verbose_name=_("Flashcardlar"))
    is_exam_review = models.BooleanField(default=True, verbose_name=_("Imtihon takrorlash to'plami"))
    created_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='flashcard_exams', verbose_name=_("Tegishli Markaz"), null=True
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Flashcard mashg'uloti")
        verbose_name_plural = _("Flashcard mashg'ulotlari")

# =================================================================
# 3. KONTENT VA SAVOLLAR BANKI MODELLARI (Katta O'zgarishlar Yo'q)
# =================================================================
 
class Topic(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Mavzu nomi"))
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Ustoz"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Tartib raqami"))
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='topics', verbose_name=_("Tegishli Markaz"), null=True
    )

    class Meta:
        verbose_name = _("Umumiy mavzu")
        verbose_name_plural = _("Umumiy mavzular")
        ordering = ['order']
        unique_together = ('name', 'teacher', 'center')

    def __str__(self):
        return self.name

class Subtopic(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Ichki mavzu nomi"))
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='subtopics', verbose_name=_("Umumiy mavzu"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Tartib raqami"))
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='subtopics', verbose_name=_("Tegishli Markaz"), null=True
    )

    class Meta:
        verbose_name = _("Ichki mavzu")
        verbose_name_plural = _("Ichki mavzular")
        ordering = ['order']
        unique_together = ('name', 'topic', 'center')

    def __str__(self):
        return f"{self.name} ({self.topic.name})"

class Passage(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Matn sarlavhasi"))
    content = models.TextField(verbose_name=_("Matn (HTML)")) # RichTextUploadingField o'rniga TextField ishlatildi (izoh qoldirilgan)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='passages',
                              verbose_name=_("Muallif"))
    created_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', on_delete=models.CASCADE, related_name='passages', verbose_name=_("Tegishli Markaz"), null=True
    )

    class Meta:
        verbose_name = _("Matn (Passage)")
        verbose_name_plural = _("Matnlar (Passages)")

    def __str__(self):
        return self.title

class RaschDifficultyLevel(models.Model):
    center = models.ForeignKey(
        'Center',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='rasch_levels',
        verbose_name="Markaz"
    )
    name = models.CharField(max_length=50, verbose_name="Daraja nomi")
    min_difficulty = models.FloatField(default=-3.0)
    max_difficulty = models.FloatField(default=3.0)

    class Meta:
        unique_together = ('name', 'center')  # bir markazda bir xil nom bo‘lmasin
        verbose_name = "Rasch darajasi"
        verbose_name_plural = "Rasch darajalari"

    def __str__(self):
        if self.center:
            return f"[{self.center.name}] {self.name}"
        return f"[Global] {self.name}"

class Question(models.Model):
    text = RichTextUploadingField(verbose_name="Savol matni", default="<p></p>")
    image = models.ImageField(upload_to='questions/', blank=True, null=True, verbose_name="Savol rasmi")
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, null=True, blank=True, related_name='questions', verbose_name="Matn")
    subtopic = models.ForeignKey(Subtopic, on_delete=models.PROTECT, related_name='questions', verbose_name="Ichki mavzu")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='questions', verbose_name="Muallif")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Teglar")
    correct_short_answer = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="To'g'ri qisqa javob"
    )
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='questions', 
        verbose_name="Tegishli Markaz",
        null=True
    )
    flashcards = models.ManyToManyField('Flashcard', related_name='questions', blank=True, verbose_name="Savolga oid flashcardlar")
    ANSWER_CHOICES = (('single', 'Yagona tanlov'), ('multiple', 'Ko\'p tanlov'), ('short_answer', 'Qisqa javob'))
    answer_format = models.CharField(max_length=20, choices=ANSWER_CHOICES, default='single', verbose_name="Javob formati")
    difficulty = models.FloatField(default=0.0, db_index=True, verbose_name="Qiyinlik darajasi (IRT difficulty)")
    discrimination = models.FloatField(default=1.0, verbose_name="Farqlash parametri (IRT discrimination)")
    guessing = models.FloatField(default=0.25, verbose_name="Taxmin parametri (IRT guessing)")
    difficulty_level = models.ForeignKey(RaschDifficultyLevel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Qiyinlik darajasi")
    STATUS_CHOICES = (('draft', 'Qoralama'), ('published', 'Nashr qilingan'), ('archived', 'Arxivlangan'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True, verbose_name="Holati")
    is_calibrated = models.BooleanField(default=False, db_index=True, verbose_name="Kalibrlanganmi?")
    response_count = models.PositiveIntegerField(default=0, verbose_name="Javoblar soni")
    is_solution_free = models.BooleanField(default=False, verbose_name="Yechim bepulmi?")
    version = models.PositiveIntegerField(default=1, verbose_name="Versiya")
    parent_question = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='versions', verbose_name="Asl (ota-ona) savol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_calibration = models.ForeignKey(
        'QuestionCalibration',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='current_for_question',
        verbose_name="Hozirgi kalibratsiya"
    )
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['-created_at']
    # models.py → Question modelida

    def save(self, *args, **kwargs):
        # Agar update_fields berilgan bo'lsa, uni o'zgartirish uchun olish
        update_fields = kwargs.get('update_fields')

        # 1. difficulty_level ni avto belgilash
        if self.difficulty is not None:
            level = None

            # Avval markazniki
            if self.center:
                level = RaschDifficultyLevel.objects.filter(
                    center=self.center,
                    min_difficulty__lte=self.difficulty,
                    max_difficulty__gte=self.difficulty
                ).first()

            # Agar topilmasa — global (center=None)
            if not level:
                level = RaschDifficultyLevel.objects.filter(
                    center__isnull=True,
                    min_difficulty__lte=self.difficulty,
                    max_difficulty__gte=self.difficulty
                ).first()

            # Agar topilsa va o'zgargan bo'lsa — yangilaymiz
            if level and self.difficulty_level != level:
                self.difficulty_level = level
                if update_fields is not None:
                    if 'difficulty_level' not in update_fields:
                        update_fields = list(update_fields) + ['difficulty_level']
                else:
                    update_fields = ['difficulty_level']

        # 2. is_calibrated ni belgilash
        if self.pk:
            try:
                old = Question.objects.only('difficulty', 'discrimination', 'guessing').get(pk=self.pk)
                changed = (
                    abs(old.difficulty - self.difficulty) > 0.001 or
                    abs(old.discrimination - self.discrimination) > 0.001 or
                    abs(old.guessing - self.guessing) > 0.001
                )
                if changed:
                    self.is_calibrated = True
            except Question.DoesNotExist:
                pass
        else:
            self.is_calibrated = (
                self.difficulty not in [None, 0.0] or
                self.discrimination not in [None, 1.0] or
                self.guessing not in [None, 0.25]
            )

        # AGAR update_fields bor bo'lsa — kwargs dan olib tashlaymiz va to'g'ridan-to'g'ri beramiz
        if update_fields is not None:
            kwargs['update_fields'] = update_fields

        # super() ga faqat bir marta update_fields beramiz
        super().save(*args, **kwargs)


    def __str__(self):
        cleaned_text = bleach.clean(self.text, tags=[], strip=True)
        return f"{cleaned_text[:60]}... (v{self.version})"

# models.py da Question dan keyin yozing
class QuestionCalibration(models.Model):
    question = models.ForeignKey(
        'Question',  # ← string ichida, shunda xato yo‘q!
        on_delete=models.CASCADE,
        related_name='calibrations',
        verbose_name="Savol"
    )
    calibrated_at = models.DateTimeField(auto_now_add=True, verbose_name="Kalibratsiya sanasi")
    response_count_used = models.PositiveIntegerField(verbose_name="Ishlatilgan javoblar soni")
    
    difficulty = models.FloatField(verbose_name="Qiyinlik (b)")
    discrimination = models.FloatField(default=1.0, verbose_name="Farqlash (a)")
    guessing = models.FloatField(default=0.25, verbose_name="Taxmin (c)")
    
    method = models.CharField(
        max_length=20,
        choices=[
            ('rasch_simple', 'Oddiy Rasch'),
            ('2pl', '2PL Model'),
            ('3pl', '3PL Model'),
        ],
        default='rasch_simple',
        verbose_name="Usul"
    )
    notes = models.TextField(blank=True, verbose_name="Izohlar")

    class Meta:
        ordering = ['-calibrated_at']
        verbose_name = "Savol kalibratsiyasi"
        verbose_name_plural = "Savollar kalibratsiyasi"

    def __str__(self):
        return f"Savol {self.question_id} → {self.calibrated_at.date()} ({self.response_count_used} javob)"
    
    
class QuestionSolution(models.Model):
    question = models.OneToOneField('Question', on_delete=models.CASCADE, related_name='solution', verbose_name="Savol")
    hint = RichTextUploadingField(blank=True, null=True, verbose_name="Yechim uchun maslahat")
    detailed_solution = RichTextUploadingField(blank=True, null=True, verbose_name="Yechim")
    
    class Meta:
        verbose_name = "Savol yechimi"
        verbose_name_plural = "Savollar yechimi"

    def __str__(self):
        return f"Savol: {self.question.id} yechimi"

class AnswerOption(models.Model):
    text = RichTextUploadingField(verbose_name="Variant matni", default="<p></p>")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options', verbose_name="Savol")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob")

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"

    def __str__(self):
        cleaned_text = strip_tags(self.text)
        return cleaned_text[:70]

    def save(self, *args, **kwargs):
        cleaned_text = self.text.strip()
        if cleaned_text.startswith('<p>') and cleaned_text.endswith('</p>'):
            cleaned_text = cleaned_text[3:-4].strip()
        self.text = cleaned_text
        super().save(*args, **kwargs)

class QuestionReview(models.Model):
    REVIEW_STATUS_CHOICES = [('open', 'Ochiq'), ('in_progress', 'Ko\'rib chiqilmoqda'), ('resolved', 'Hal qilindi')]
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='reviews', verbose_name="Savol")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            verbose_name="Xabar bergan foydalanuvchi")
    comment = models.TextField(verbose_name="Izoh")
    status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default='open', db_index=True,
                             verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        cleaned_text = bleach.clean(self.question.text, tags=[], strip=True)
        return f"{cleaned_text[:30]}... bo'yicha xabar"

    class Meta:
        verbose_name = "Savol bo'yicha shikoyat"
        verbose_name_plural = "Savollar bo'yicha shikoyatlar"
        ordering = ['-created_at']

class Exam(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Ustoz")
    title = models.CharField(max_length=200, verbose_name="Test nomi")
    is_subject_exam = models.BooleanField(
        default=False, 
        verbose_name="Mavzu testi", 
        help_text="Agar bu imtihon to'liq SAT sinovi emas, balki biror mavzu bo'yicha test bo'lsa"
    )
    passing_percentage = models.PositiveIntegerField(
        default=60, 
        verbose_name="O'tish foizi (%)",
        help_text="O'quvchi keyingi darsga o'tishi uchun to'plashi kerak bo'lgan minimal foiz (0-100)"
    )
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    is_premium = models.BooleanField(default=True, verbose_name="Pullik imtihon")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='exams', 
        verbose_name="Tegishli Markaz",
        null=True
    )
    sections = models.ManyToManyField(
        'ExamSection',
        through='ExamSectionOrder', 
        related_name='exams',
        verbose_name="Imtihon bo‘limlari"
    )

    class Meta:
        verbose_name = "Imtihon"
        verbose_name_plural = "Imtihonlar"
        unique_together = ('title', 'center')
        ordering = ['title']

    def get_or_create_flashcard_exam(self):
        if hasattr(self, 'flashcard_exam'):
            return getattr(self, 'flashcard_exam', None)
        question_ids = ExamSectionStaticQuestion.objects.filter(
            exam_section__in=self.sections.all() 
        ).values_list('question_id', flat=True).distinct()
        flashcard_ids = Flashcard.objects.filter(
            questions__id__in=question_ids
        ).values_list('id', flat=True).distinct()
        if not flashcard_ids:
            return None
        flashcard_exam, created = FlashcardExam.objects.get_or_create(
            source_exam=self,
            defaults={'title': f"{self.title} - Flashcard Mashg'uloti"}
        )
        flashcard_exam.flashcards.set(flashcard_ids)
        return flashcard_exam
    
    def __str__(self):
        return self.title

class ExamSection(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="Bo‘lim nomi", 
                           help_text="Masalan: Qiyin darajali Writing, Yengil darajali Math-Calc.")
    SECTION_TYPES = (
        ('subject_test', 'Mavzu testi'),
        ('read_write_m1', 'Reading'),
        ('read_write_m2', 'Writing and Language'),
        ('math_no_calc', 'Math (No Calculator)'),
        ('math_calc', 'Math (Calculator)'),
    )
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES, verbose_name="Bo‘lim turi")
    duration_minutes = models.PositiveIntegerField(verbose_name="Davomiyligi (minut)")
    max_questions = models.PositiveIntegerField(verbose_name="Maksimal savollar soni")
    static_questions = models.ManyToManyField('Question', through='ExamSectionStaticQuestion',
                                            related_name='static_exam_sections', blank=True,
                                            verbose_name="Statik savollar")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    min_difficulty = models.FloatField(null=True, blank=True, verbose_name="Minimal qiyinlik (IRT)")
    max_difficulty = models.FloatField(null=True, blank=True, verbose_name="Maksimal qiyinlik (IRT)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='exam_sections', 
        verbose_name="Tegishli Markaz",
        null=True
    )

    class Meta:
        verbose_name = "Bo‘lim shabloni"
        verbose_name_plural = "Bo‘lim shablonlari"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_section_type_display()})"

class ExamSectionOrder(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='examsectionorder')
    exam_section = models.ForeignKey(ExamSection, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(verbose_name="Tartib raqami")
    
    class Meta:
        unique_together = ('exam', 'order')
        ordering = ['order']
        verbose_name = "Imtihon bo‘limi tartibi"

    def __str__(self):
        return f"{self.exam.title} - {self.order}-o‘rin: {self.exam_section.name}"

class ExamSectionStaticQuestion(models.Model):
    exam_section = models.ForeignKey(ExamSection, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    question_number = models.PositiveIntegerField(verbose_name="Savol tartib raqami")

    class Meta:
        ordering = ['question_number']
        unique_together = ('exam_section', 'question')
        verbose_name = "Bo'limning statik savoli"
        verbose_name_plural = "Bo'limning statik savollari"

class UserAttempt(models.Model):
    """
    Foydalanuvchining imtihon urinishini kuzatadi.
    MUHIM: Qaysi markazda sodir bo'lganligi uchun 'center' maydoni qo'shildi.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attempts',
                             verbose_name="Foydalanuvchi")
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, verbose_name="Imtihon", related_name='user_attempts')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqti")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan vaqti")
    is_completed = models.BooleanField(default=False, db_index=True, verbose_name="Tugatilgan")
    final_ebrw_score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Yakuniy EBRW balli")
    final_math_score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Yakuniy Math balli")
    final_total_score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Yakuniy umumiy ball")
    correct_percentage = models.FloatField(default=0.0, verbose_name="To'g'ri javoblar foizi")
    mode = models.CharField(max_length=50, default='exam', verbose_name="Imtihon rejimi")

    # YANGI MAYDON: Ushbu urinish qaysi markazda amalga oshirilganini belgilaydi
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='center_attempts', 
        verbose_name="Tegishli Markaz",
        null=True
    )

    class Meta:
        verbose_name = "Foydalanuvchi urinishi"
        verbose_name_plural = "Foydalanuvchi urinishlari"

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} ({self.mode})"

    def is_passed(self):
        if self.exam.is_subject_exam:
            return self.correct_percentage >= self.exam.passing_percentage
        return True

class UserAttemptSection(models.Model):
    """
    Foydalanuvchining imtihon bo'limini ishlash urinishini kuzatadi.
    MUHIM: Qaysi markazda sodir bo'lganligi uchun 'center' maydoni qo'shildi.
    """
    attempt = models.ForeignKey(UserAttempt, on_delete=models.CASCADE, related_name='section_attempts',
                                 verbose_name="Urinish")
    section = models.ForeignKey('ExamSection', on_delete=models.CASCADE, verbose_name="Bo‘lim")
    score = models.PositiveIntegerField(default=0, verbose_name="Bo‘lim balli")
    correct_answers_count = models.PositiveIntegerField(default=0, verbose_name="To'g'ri javoblar soni")
    incorrect_answers_count = models.PositiveIntegerField(default=0, verbose_name="Noto'g'ri javoblar soni")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan vaqti")
    questions = models.ManyToManyField(
        'Question', 
        through='UserAttemptQuestion', 
        related_name='attempted_in_sections', 
        blank=True,
        verbose_name="Berilgan savollar"
    )
    remaining_time_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="Qolgan vaqt (soniya)")
    is_completed = models.BooleanField(default=False, verbose_name="Yakunlangan")

    # YANGI MAYDON: Ushbu urinish bo'limi qaysi markazda amalga oshirilganini belgilaydi
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='center_section_attempts', 
        verbose_name="Tegishli Markaz",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Bo‘lim urinishi"
        verbose_name_plural = "Bo‘lim urinishlari"
        unique_together = ('attempt', 'section')

    def __str__(self):
        return f"{self.attempt} - {self.section}"

class UserAttemptQuestion(models.Model):
    """
    Urinish ichidagi savollarning tartibini saqlaydi (o'zgarishsiz qoldi).
    """
    attempt_section = models.ForeignKey('UserAttemptSection', on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    question_number = models.PositiveIntegerField(
        verbose_name="Savol tartibi",
        default=1
    )
    
    class Meta:
        verbose_name = "Urinish savoli tartibi"
        verbose_name_plural = "Urinish savollari tartibi"
        unique_together = ('attempt_section', 'question')
        ordering = ['question_number']

    def __str__(self):
        return f"S-{self.attempt_section.id} Q-{self.question_number}: {self.question.id}"

class UserAnswer(models.Model):
    """
    Joriy urinishdagi foydalanuvchi javoblarini saqlaydi (o'zgarishsiz qoldi).
    """
    attempt_section = models.ForeignKey(UserAttemptSection, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    selected_options = models.ManyToManyField('AnswerOption', blank=True, verbose_name="Tanlangan variantlar")
    short_answer_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qisqa javob matni")
    is_correct = models.BooleanField(null=True, verbose_name="To'g'riligi")
    is_marked_for_review = models.BooleanField(default=False, verbose_name="Ko'rib chiqish uchun belgilangan")
    answered_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="Sarflangan vaqt (soniya)")

    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"
        unique_together = ('attempt_section', 'question')

    def __str__(self):
        return f"{self.attempt_section.attempt.user.username} javobi"

class UserAnswerArchive(models.Model):
    """
    Arxivlangan foydalanuvchi javoblarini saqlaydi.
    MUHIM: Qaysi markazga tegishli ekanligini bildirish uchun 'center' maydoni qo'shildi.
    """
    attempt_section = models.ForeignKey('UserAttemptSection', on_delete=models.CASCADE, related_name='archived_answers')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    selected_options = models.ManyToManyField('AnswerOption', blank=True, verbose_name="Tanlangan variantlar")
    short_answer_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qisqa javob matni")
    is_correct = models.BooleanField(null=True, verbose_name="To'g'riligi")
    answered_at = models.DateTimeField()
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="Sarflangan vaqt (soniya)")

    # YANGI MAYDON: Javob arxivini markaz bo'yicha ajratish uchun
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='archived_answers_by_center', 
        verbose_name="Tegishli Markaz",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Arxivlangan foydalanuvchi javobi"
        verbose_name_plural = "Arxivlangan foydalanuvchi javoblari"

    def __str__(self):
        return f"Arxiv: {self.attempt_section.attempt.user.username} javobi"
 
# =================================================================
# 5.5. Kurs va kurs mavzulari va mavzu testlar ishlash
# =================================================================

COURSE_TYPE_CHOICES = (
    ('online', 'Online Kurs'),
    ('offline', 'Offline Kurs (An\'anaviy)'),
)

ONLINE_LESSON_FLOW_CHOICES = (
    ('self_paced', 'Ixtiyoriy (Talaba o\'zi boshqaradi)'),
    ('scheduled', 'Jadval asosida (Muddatli/Vaqtli)'),
)

RESOURCE_TYPE_CHOICES = (
    ('video', 'Videodars Linki'),
    ('task', 'Vazifa/Amaliyot Linki'),
    ('solution_video', 'Yechim Videolinki'),
    ('solution_file', 'Yechim Fayli Linki/Yuklama'),
    ('other', 'Boshqa Resurs (PDF, Google Doc va h.k.)'),
)

class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name="Kurs nomi")
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Ustoz")
    course_type = models.CharField(
        max_length=10, 
        choices=COURSE_TYPE_CHOICES, 
        default='online', 
        verbose_name="Kurs turi"
    )
    online_lesson_flow = models.CharField(
        max_length=10, 
        choices=ONLINE_LESSON_FLOW_CHOICES, 
        default='self_paced', 
        verbose_name="Online darslar turi",
        help_text="'Ixtiyoriy'da tezlik talabaga bog'liq, 'Jadval asosida'da vaqt cheklangan."
    )
    is_premium = models.BooleanField(default=True, verbose_name="Pullik kurs")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Kurs narxi"
    )
    course_img = models.ImageField(
        upload_to='course_images/', 
        blank=True, 
        null=True, 
        verbose_name="Kurs rasmi (bosh rasm)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='courses', 
        verbose_name="Tegishli Markaz",
        null=True
    )
    

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        unique_together = ('title', 'center')
        ordering = ['title']

    def __str__(self):
        return self.title

    @property
    def is_online(self):
        return self.course_type == 'online'
    
    @property
    def is_scheduled(self):
        return self.is_online and self.online_lesson_flow == 'scheduled'

class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules', verbose_name="Kurs")
    title = models.CharField(max_length=200, verbose_name="Modul nomi")
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        verbose_name = "Kurs Moduli"
        verbose_name_plural = "Kurs Modullari"
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='lessons', verbose_name="Modul")
    title = models.CharField(max_length=200, verbose_name="Dars nomi")
    related_exam = models.ForeignKey( 
        'Exam', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='lessons_linked', # related_name ni o'zgartirish kerak, chunki 'lesson' endi ko'plik bo'ladi
        verbose_name="Mavzu testi",
        help_text="Bu darsga test biriktirilishi shart emas. Agar biriktirilsa, keyingi darsga o'tish uchun talab etiladi."
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"
        ordering = ['module__order', 'order']
        unique_together = ('module', 'order')

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def has_resources(self):
        return self.resources.exists()

    @property
    def has_exam(self):
        return self.related_exam is not None

class LessonResource(models.Model):
    lesson = models.ForeignKey(
        Lesson, 
        on_delete=models.CASCADE, 
        related_name='resources', 
        verbose_name="Dars"
    )
    resource_type = models.CharField(
        max_length=20, 
        choices=RESOURCE_TYPE_CHOICES, 
        verbose_name="Resurs turi"
    )
    link = models.URLField(
        max_length=500, 
        verbose_name="Resurs linki",
        help_text="Video, fayl yoki boshqa materialga tashqi URL manzil."
    )
    title = models.CharField(
        max_length=200, 
        verbose_name="Resurs nomi (Masalan: 1-qism)", 
        blank=True, 
        null=True
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        verbose_name = "Dars Resursi"
        verbose_name_plural = "Dars Resurslari"
        ordering = ['resource_type', 'order']

    def __str__(self):
        return f"{self.get_resource_type_display()} - {self.lesson.title}"

# --- YANGI QO'SHILGAN MODEL: Talaba Resursni ko'rganini qayd etadi ---
class UserResourceView(models.Model):
    """
    Foydalanuvchining ma'lum bir LessonResource ga kirishini (ko'rishini) kuzatadi.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='resource_views',
        verbose_name="Foydalanuvchi"
    )
    lesson_resource = models.ForeignKey(
        'LessonResource', 
        on_delete=models.CASCADE, 
        related_name='user_views',
        verbose_name="Resurs"
    )
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="Ko'rilgan vaqt")

    class Meta:
        verbose_name = "Foydalanuvchi Resurs Ko'ruvchi"
        verbose_name_plural = "Foydalanuvchi Resurs Ko'ruvchilari"
        # Bir foydalanuvchi, bir resursni faqat bir marta ko'rdi deb qayd etiladi.
        unique_together = ('user', 'lesson_resource')

    def __str__(self):
        return f"{self.user.username} - {self.lesson_resource.title} ko'rildi"
    
class CourseSchedule(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='schedule_slots', 
        verbose_name="Kurs"
    )
    # Hafta kunlari: 1=Dushanba, 7=Yakshanba
    DAY_OF_WEEK_CHOICES = [
        (1, 'Dushanba'), (2, 'Seshanba'), (3, 'Chorshanba'), (4, 'Payshanba'), 
        (5, 'Juma'), (6, 'Shanba'), (7, 'Yakshanba')
    ]
    day_of_week = models.IntegerField(
        choices=DAY_OF_WEEK_CHOICES, 
        verbose_name="Hafta kuni",
        default=1
    )
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    
    # BU YERDA KETMA-KETLIK ANQLANADI
    # Masalan: Dushanba 16:00 (1-slot), Chorshanba 18:00 (2-slot).
    order_in_cycle = models.PositiveIntegerField(
        verbose_name="Haftalik sikldagi tartibi",
        help_text="Bu slot haftalik darslar siklida nechanchi o'rinda turishini ko'rsatadi (1 dan boshlab).",
        default=1
    )
    
    # Kiritilgan qo'shimcha mantiq: Darslar qaysi slotdan boshlanishi kerak?
    is_start_slot = models.BooleanField(
        default=False,
        verbose_name="Boshlang'ich slot",
        help_text="Agar Kurs yangi guruh uchun boshlansa, Lesson 1 aynan shu slotga moslanadi."
    )

    class Meta:
        verbose_name = "Takrorlanuvchi Jadval Sloti"
        verbose_name_plural = "Takrorlanuvchi Jadval Slotlari"
        # Bitta kursda bir xil kun/vaqt slotiga ruxsat berilmaydi
        unique_together = ('course', 'day_of_week', 'start_time')
        # Sikldagi tartib bo'yicha saralash
        ordering = ['order_in_cycle', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.course.title} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')} (Slot #{self.order_in_cycle})"

class UserSolutionView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solution_views')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='solution_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    credit_spent = models.BooleanField(default=False, verbose_name="Kredit sarflandimi?")

    class Meta:
        verbose_name = "Ko'rilgan savol yechimi"
        verbose_name_plural = "Ko'rilgan savol yechimlari"
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} -> {self.question.id}-savol yechimi"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar matni")
    is_read = models.BooleanField(default=False, db_index=True, verbose_name="O'qilganmi?")
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"

    def __str__(self):
        return f"{self.user.username} uchun xabarnoma"

class Badge(models.Model):
    TRIGGER_TYPES = [
        ('exam_completed', 'Imtihon yakunlandi'),
        ('score_achieved', 'Ball yetkazildi'),
        ('streak', 'Ketma-ketlik'),
        ('flashcard_learned', 'Flashcard o\'rganildi'),
        ('daily_high_score', 'Eng yaxshi kunlik natija'),
        ('referral', 'Do\'stlarni taklif qilish'),
    ]
    title = models.CharField(max_length=100, unique=True, verbose_name="Nishon nomi")
    description = models.TextField(verbose_name="Tavsif")
    icon = models.ImageField(upload_to='badges/', verbose_name="Nishon ikonasi")
    trigger_type = models.CharField(
        max_length=50,
        choices=TRIGGER_TYPES,
        verbose_name="Meyor turi",
        help_text="Nishon qachon berilishini tanlang"
    )
    exam_count = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Imtihonlar soni (imtihon yakunlash meyorida)",
        help_text="Agar 'Imtihon yakunlandi' tanlangan bo'lsa, shu son yetkazilsa nishon beriladi"
    )
    min_score = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Minimal ball (ball yetkazish meyorida)",
        help_text="Agar 'Ball yetkazildi' tanlangan bo'lsa, shu balldan yuqori bo'lsa nishon beriladi"
    )
    streak_days = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Ketma-ket kunlar soni (ketma-ketlik meyorida)",
        help_text="Agar 'Ketma-ketlik' tanlangan bo'lsa, shu kun ketma-ket mashq qilinsa nishon beriladi"
    )
    flashcard_count = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Flashcardlar soni (flashcard o'rganish meyorida)",
        help_text="Agar 'Flashcard o'rganildi' tanlangan bo'lsa, shu son o'rganilsa nishon beriladi"
    )
    daily_min_score = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Kunlik minimal ball (eng yaxshi kunlik natija meyorida)"
    )
    referral_count = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Taklif qilingan do'stlar soni (referral meyorida)"
    )
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='badges', 
        verbose_name="Tegishli Markaz",
        null=True
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Nishon (Yutuq)"
        verbose_name_plural = "Nishonlar (Yutuqlar)"

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_users')
    awarded_at = models.DateTimeField(auto_now_add=True)
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='user_badges', 
        verbose_name="Tegishli Markaz",
        null=True
    )

    class Meta:
        unique_together = ('user', 'badge', 'center')
        verbose_name = "Foydalanuvchi nishoni"
        verbose_name_plural = "Foydalanuvchi nishonlari"

    def __str__(self):
        return f"{self.user.username} - {self.badge.title}"

class LeaderboardEntry(models.Model):
    LEADERBOARD_TYPES = [
        ('effort', 'Mehnat bo\'yicha (ko\'p imtihon ishlaganlar)'),
        ('performance', 'Natija bo\'yicha (yuqori ball olganlar)'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaderboard_entries')
    leaderboard_type = models.CharField(max_length=20, choices=LEADERBOARD_TYPES, verbose_name="Leaderboard turi")
    week_number = models.PositiveIntegerField(verbose_name="Hafta raqami")
    score = models.PositiveIntegerField(default=0, verbose_name="Ball yoki ko'rsatkich")
    updated_at = models.DateTimeField(auto_now=True)
    center = models.ForeignKey(
        'Center', 
        on_delete=models.CASCADE, 
        related_name='leaderboard_entries', 
        verbose_name="Tegishli Markaz",
        null=True
    )

    class Meta:
        verbose_name = "Leaderboard kirishi"
        verbose_name_plural = "Leaderboard kirishlari"
        unique_together = ('user', 'leaderboard_type', 'week_number', 'center')
        indexes = [
            models.Index(fields=['leaderboard_type', 'week_number', '-score']),
        ]
        ordering = ['-score']

    def __str__(self):
        return f"{self.user.username} - {self.get_leaderboard_type_display()} (Hafta {self.week_number}): {self.score}"

class UserMissionProgress(models.Model):
    # Foydalanuvchi ushbu model hozircha ishlatilmasligini tasdiqladi, shuning uchun o'zgarishsiz qoldi.
    # Agar keyinchalik Markaz bo'yicha mustaqil progress kerak bo'lsa, o'zgarishi mumkin.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mission_progress')
    exam_attempts_completed = models.PositiveIntegerField(default=0, verbose_name="Yakunlangan exam mode urinishlari")
    study_attempts_completed = models.PositiveIntegerField(default=0, verbose_name="Yakunlangan study mode urinishlari")
    highest_score = models.PositiveIntegerField(default=0, verbose_name="Eng yuqori ball (exam mode)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Foydalanuvchi missiya progressi"
        verbose_name_plural = "Foydalanuvchi missiya progresslari"

    def __str__(self):
        return f"{self.user.username} - Exam: {self.exam_attempts_completed}, Study: {self.study_attempts_completed}"
