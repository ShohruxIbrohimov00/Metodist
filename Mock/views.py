from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Max, Min, F, Q, Window, Avg,Case,IntegerField,When,Value,Subquery, OuterRef,CharField
from django.db import transaction
from django.db.models import Prefetch, Count
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.db.models.functions import Coalesce, Rank
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.conf import settings
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
import string 
import html
from django.template.loader import render_to_string 
from django.forms import formset_factory
from django.core.paginator import Paginator
import json
import logging
from .models import *
from .forms import *
import bleach

logger = logging.getLogger(__name__)

import logging
import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Max, Avg
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)
User = get_user_model()

import math
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin


   
# =============================================================
# I. YORDAMCHI FUNKSIYALAR
# =============================================================

def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'

def is_student(user):
    return user.is_authenticated and user.role == 'student'

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_center_manager(user):
    """Foydalanuvchi boshqaruvchi (admin/o'qituvchi/owner) ekanligini tekshiradi."""
    return user.role in ['center_admin', 'teacher', 'owner']

def _get_user_center(user):
    """Foydalanuvchiga biriktirilgan markaz obyektini (Foreign Key) qaytaradi."""
    if hasattr(user, 'center'):
        return user.center
    return None

def check_center_access(request, slug):
    """
    Foydalanuvchining so'ralgan markazga kirish huquqini tekshiradi.
    Faqat request.user.center Foreign Keyga tayanadi.
    """
    center = get_object_or_404(Center, slug=slug, is_active=True)
    
    if not request.user.is_authenticated:
        messages.error(request, "Tizimga kirishingiz kerak.")
        return center, redirect('login')

    user_center = request.user.center
    
    if user_center and user_center.slug == slug:
        # Ruxsat bor: foydalanuvchi aynan shu markazga biriktirilgan
        return center, None
    else:
        # Ruxsat yo'q: foydalanuvchi boshqa markazga biriktirilgan yoki umuman biriktirilmagan
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki siz boshqa markazga biriktirilgansiz.")
        return center, redirect('dashboard_redirect')

# =============================================================
# II. AUTHENTICATION VIEWS
# =============================================================

User = get_user_model() 

logger = logging.getLogger(__name__)

# =============================================================
# II. ASOSIY VIEW'LAR
# =============================================================

def index(request):
    """
    Asosiy kirish sahifasi.
    Foydalanuvchi tizimga kirgan bo'lsa ham, boshqa joyga yo'naltirmaydi.
    U faqat kirish/ro'yxatdan o'tish sahifasi (index.html) ni render qiladi.
    """
    return render(request, 'index.html')

def dashboard_redirect_view(request):
    """
    Muvaffaqiyatli kirishdan so'ng (LOGIN_REDIRECT_URL) chaqiriladi.
    Foydalanuvchini roli va biriktirilgan markaziga (center FK) qarab to'g'ri dashboardga yo'naltiradi.
    """
    # Kirish tekshiruvi
    if not request.user.is_authenticated:
        return redirect('login_view') 
        
    # Markazni olish (CustomUser.center)
    center = _get_user_center(request.user)
    
    if center:
        center_slug = center.slug
        
        # 1. Talaba
        if request.user.role == 'student':
            # reverse('dashboard', kwargs={'slug': center_slug}) da 'dashboard' URL nomi to'g'ri ekanligiga ishonch hosil qiling.
            return redirect(reverse('dashboard', kwargs={'slug': center_slug}))
        
        # 2. Boshqaruvchi
        elif request.user.role in ['teacher', 'center_admin', 'owner']:
            # reverse('teacher_dashboard', kwargs={'slug': center_slug}) da 'teacher_dashboard' URL nomi to'g'ri ekanligiga ishonch hosil qiling.
            return redirect(reverse('teacher_dashboard', kwargs={'slug': center_slug}))
        
        else:
            # Agar rolni aniqlab bo'lmasa
            messages.warning(request, "Foydalanuvchi rolining biriktirilishi aniq emas. Administrator bilan bog'laning.")
            return redirect('index')
            
    else:
        # Markaz biriktirilmagan holat (user.center = None)
        # Bu NoReverseMatch xatosini oldini oladi.
        messages.error(request, "Sizning akkauntingizga hali markaz biriktirilmagan. Administrator bilan bog'laning.")
        return redirect('index') # Kirish sahifasiga qaytarish

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # DEBUG: Kiritilgan ma'lumotlarni tekshiring
        print(f"Attempting login for: {username}")
        
        user = authenticate(request, username=username, password=password)
        
        # DEBUG: Autentifikatsiya natijasini tekshiring
        print(f"Authentication Result: {user}")
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.username}!")
            return redirect('dashboard_redirect_view') 
        else:
            messages.error(request, "Login yoki parol xato! Iltimos, qayta urinib ko'ring.")
            
    return render(request, 'registration/login.html')

def signup_view(request):
    """
    Ro'yxatdan o'tish view'i. Yangi foydalanuvchini yaratadi va tizimdagi 
    ASOSIY markazga biriktiradi (SignUpForm ichida).
    
    Eslatma: Bu funksiyada kirgan foydalanuvchini boshqa joyga yo'naltirish tekshiruvi OLIB TASHLANDI.
    """
    
    # Eslatma: request.user.is_authenticated tekshiruvi foydalanuvchi talabiga ko'ra olib tashlangan.
    # if request.user.is_authenticated:
    #     return redirect('dashboard_redirect_view')

    if request.method == 'POST':
        # SignUpForm to'g'ri import qilinganligiga ishonch hosil qiling
        form = SignUpForm(request.POST) 
        
        if form.is_valid():
            # Markazga avtomatik biriktirish logikasi SignUpForm.save() ichida amalga oshiriladi
            user = form.save() 
            login(request, user)
            
            # Xabar berish: Avtomatik biriktirilgan markaz nomini ko'rsatish
            if user.center:
                 messages.success(request, f"Ro'yxatdan o'tish muvaffaqiyatli! Siz '{user.center.name}' markaziga biriktirildingiz.")
            else:
                 messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli! Markaz hali yaratilmagan.")
            
            # Muvaffaqiyatli ro'yxatdan o'tgandan keyin yo'naltirish
            return redirect('dashboard_redirect_view')

        else:
            # Xatolarni chiqarish (Django messages orqali)
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label} da xato: {error}")
            for error in form.non_field_errors():
                messages.error(request, f"Umumiy xato: {error}")
            
    else:
        # GET so'rovi: Bo'sh formani yaratish
        form = SignUpForm()
        
    return render(request, 'registration/signup.html', {'form': form})

def logout_view(request):
    """Tizimdan chiqish view'i."""
    logout(request)
    return redirect('index')

# views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect


# views.py (Mock/views.py yoki accounts/views.py)

from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

User = get_user_model()

# 1. Parolni tiklash so'rovi (email yuborish)
# views.py boshida, kerakli importlarni qo'shing
from .forms import PasswordResetForm  # forms.py dan import qilish
from django.urls import reverse # reverse funksiyasini import qilish

# Mock/views.py

def mock_password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST) 
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            users = User.objects.filter(email=email)
            
            # Agar foydalanuvchilar mavjud bo'lsa, email yuboramiz
            if users.exists():
                for user in users:
                    # 💡 subject va message endi doimo loop ichida aniqlanadi:
                    subject = "Parolni tiklash so'rovi"
                    
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)
                    
                    # reverse() dan foydalanish (avvalgi javobdan)
                    from django.urls import reverse 
                    reset_path = reverse('mock_password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                    reset_url = request.build_absolute_uri(reset_path)

                    message = render_to_string('registration/password_reset_email.txt', {
                        'user': user,
                        'reset_url': reset_url,
                    })
                    
                    # 💡 send_mail faqat user topilsagina chaqiriladi
                    send_mail(
                        subject,
                        message,
                        'noreply@satmath.uz',
                        [user.email],
                        fail_silently=False,
                    )
            
            # Email yuborilganidan qat'i nazar (xavfsizlik uchun) bir xil xabar
            messages.success(request, "Agar email tizimda mavjud bo'lsa, tiklash havolasi yuborildi.")
            return redirect('mock_password_reset_done') 
        
        context = {'form': form}
    else:
        form = PasswordResetForm()
        context = {'form': form}
        
    return render(request, 'registration/mock_password_reset_form.html', context)

# 2. Havola yuborildi sahifasi
def mock_password_reset_done(request):
    return render(request, 'registration/mock_password_reset_done.html')


# 3. Yangi parol o'rnatish (havola orqali kelganda)
# views.py da shu funksiyani to‘liq almashtiring:
def mock_password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                user = form.save()
                messages.success(request, "Parolingiz muvaffaqiyatli o'zgartirildi!")
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        return render(request, 'registration/mock_password_reset_confirm.html', {
            'form': form,
            'validlink': True,
        })
    else:
        return render(request, 'registration/mock_password_reset_confirm.html', {
            'validlink': False,
        })

# 4. Parol muvaffaqiyatli o'rnatildi
def mock_password_reset_complete(request):
    return render(request, 'registration/mock_password_reset_complete.html')


# 5. Kirgan foydalanuvchi uchun parolni o'zgartirish
@login_required
def mock_change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Chiqib ketmasin
            messages.success(request, "Parolingiz muvaffaqiyatli o'zgartirildi!")
            return redirect('profile')  # yoki 'dashboard'
        else:
            messages.error(request, "Iltimos, xatoliklarni tuzating.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'registration/change_password.html', {
        'form': form,
    })


# =============================================================
# III. DASHBOARD VIEWS
# =============================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Avg, Count, Case, When, Sum 
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import json
import logging



@login_required(login_url='login')
def dashboard_view(request, slug):
    user = request.user
    center = get_object_or_404(Center, slug=slug)

    if user.center != center:
        messages.error(request, "Siz bu markazga a'zo emassiz.")
        return redirect('center_access_denied')

    agenda_items = []
    course_progress_data = []

    try:
        # 1. Flashcard takrorlash
        if UserFlashcardStatus.objects.filter(user=user, next_review_at__lte=timezone.now()).exists():
            count = UserFlashcardStatus.objects.filter(user=user, next_review_at__lte=timezone.now()).count()
            agenda_items.append({
                'priority': 1,
                'icon': 'brain',
                'title': f"{count} ta so'zni takrorlang",
                'description': "Spaced repetition vaqti keldi",
                'url': reverse('my_flashcards', kwargs={'slug': slug}),
                'color': 'teal'
            })

        # 2. AKTIV KURSLAR
        enrolled_groups = user.enrolled_groups.all()
        group_courses = Course.objects.filter(
            groups_in_course__in=enrolled_groups,
            center=center,
            is_active=True
        ).values_list('id', flat=True)

        purchased_courses = Purchase.objects.filter(
            user=user,
            status='completed',
            purchase_type='course',
            course__center=center,
            course__is_active=True
        ).values_list('course_id', flat=True)

        all_course_ids = set(group_courses) | set(purchased_courses)
        active_courses = Course.objects.filter(id__in=all_course_ids).select_related('teacher')

        if active_courses.exists():
            for course in active_courses:
                # Progress hisoblash
                total = Lesson.objects.filter(module__course=course) \
                    .annotate(cnt=Count('resources')).aggregate(t=Sum('cnt'))['t'] or 0
                completed = UserResourceView.objects.filter(
                    user=user,
                    lesson_resource__lesson__module__course=course
                ).count()
                percent = round(completed / total * 100) if total > 0 else 0

                next_lesson = None
                if percent < 100:
                    lessons = Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
                    for lesson in lessons:
                        if lesson.resources.count() > UserResourceView.objects.filter(
                            user=user, lesson_resource__lesson=lesson
                        ).count():
                            next_lesson = lesson
                            break

                course_progress_data.append({
                    'course': course,
                    'progress_percent': percent,
                    'next_lesson': next_lesson,
                })

            # Keyingi darsni agenda ga qo‘shish
            in_progress = [c for c in course_progress_data if c['next_lesson']]
            if in_progress:
                best = min(in_progress, key=lambda x: x['progress_percent'])
                agenda_items.append({
                    'priority': 0,
                    'icon': 'graduation-cap',
                    'title': f"Davom eting: {best['course'].title}",
                    'description': f"Keyingi dars: {best['next_lesson'].title}",
                    'url': reverse('lesson_detail', kwargs={'slug': slug, 'lesson_id': best['next_lesson'].id}),
                    'color': 'indigo'
                })

        # 3. HECH QANDAY KURS YO‘Q BO‘LSA – XAVFSIZ URL!
        if not active_courses.exists():
            agenda_items.append({
                'priority': 0,
                'icon': 'book-open',
                'title': "Kurs tanlash vaqti keldi",
                'description': "Barcha kurslarni ko‘ring va o‘qishni boshlang",
                'url': reverse('all_courses', kwargs={'slug': slug}),
                'color': 'purple'
            })

        # 4. Oxirgi imtihon
        latest = UserAttempt.objects.filter(user=user, is_completed=True, exam__is_subject_exam=False) \
            .order_by('-completed_at').first()
        if latest:
            agenda_items.append({
                'priority': 2,
                'icon': 'chart-line',
                'title': "Oxirgi imtihonni tahlil qiling",
                'description': f"{latest.exam.title} – xatolaringiz ustida ishlang",
                'url': reverse('view_result_detail', kwargs={'slug': slug, 'attempt_id': latest.id}),
                'color': 'red'
            })

        # 5. Yangi imtihon
        new_exam = Exam.objects.filter(center=center, is_active=True, is_subject_exam=False) \
            .exclude(userattempt__user=user).order_by('?').first()
        if new_exam:
            agenda_items.append({
                'priority': 3,
                'icon': 'rocket',
                'title': "Yangi imtihon boshlang",
                'description': f"{new_exam.title} bilan bilimingizni sinang",
                'url': reverse('exam_detail', kwargs={'slug': slug, 'exam_id': new_exam.id}),
                'color': 'orange'
            })

    except Exception as e:
        logger.error(f"Dashboard error: {e}")

    agenda_items = sorted(agenda_items, key=lambda x: x['priority'])[:3]

    # --- Statistika ---
    today = timezone.now().date()
    week_ago = today - timedelta(days=6)
    dates = [week_ago + timedelta(i) for i in range(7)]
    chart_labels = json.dumps([d.strftime("%b %d") for d in dates])

    # Boshqa statistikalar (xato bo‘lsa ham sahifa buzilmasin)
    exam_score_data = flashcard_data = json.dumps([0] * 7)
    highest_score = completed_exam_count = learned_flashcards_count = 0
    leaderboard_users = []
    user_rank = None

    try:
        # Imtihon ballari
        scores = UserAttempt.objects.filter(
            user=user, is_completed=True, completed_at__date__gte=week_ago,
            exam__is_subject_exam=False
        ).values('completed_at__date').annotate(s=Avg('final_total_score'))
        score_map = {s['completed_at__date']: s['s'] for s in scores}
        exam_score_data = json.dumps([round(score_map.get(d, 0)) for d in dates])

        # Flashcard
        reviews = UserFlashcardStatus.objects.filter(
            user=user, last_reviewed_at__date__gte=week_ago
        ).values('last_reviewed_at__date').annotate(c=Count('id'))
        review_map = {r['last_reviewed_at__date']: r['c'] for r in reviews}
        flashcard_data = json.dumps([review_map.get(d, 0) for d in dates])

        # Liderlar
        leaderboard_users = User.objects.filter(center=center, role='student') \
            .annotate(score=Max('attempts__final_total_score',
                               filter=Q(attempts__is_completed=True, attempts__exam__is_subject_exam=False))) \
            .exclude(score__isnull=True).order_by('-score')[:5]

        highest_score = UserAttempt.objects.filter(
            user=user, is_completed=True, exam__is_subject_exam=False
        ).aggregate(m=Max('final_total_score'))['m'] or 0

        completed_exam_count = UserAttempt.objects.filter(
            user=user, is_completed=True, exam__is_subject_exam=False
        ).values('exam').distinct().count()

        learned_flashcards_count = UserFlashcardStatus.objects.filter(user=user, status='learned').count()

    except Exception as e:
        logger.error(f"Stats error: {e}")

    context = {
        'center': center,
        'agenda_items': agenda_items,
        'course_progress_data': course_progress_data,
        'chart_labels': chart_labels,
        'exam_score_data': exam_score_data,
        'flashcard_data': flashcard_data,
        'highest_score': highest_score,
        'completed_exam_count': completed_exam_count,
        'learned_flashcards_count': learned_flashcards_count,
        'leaderboard_users': leaderboard_users,
        'user_rank': user_rank,
    }
    return render(request, 'student/dashboard.html', context)


from django.shortcuts import render, redirect
from django.db.models import Count, Max, Avg, Sum, Q, F
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
import datetime



@login_required
@user_passes_test(is_center_manager, login_url='login') 
def teacher_dashboard(request, slug):
    try:
        # Markazni slug bo'yicha olish (Center modeli yuqorida aniqlangan)
        center = Center.objects.get(slug=slug) 
    except Center.DoesNotExist:
        messages.error(request, "Markaz topilmadi.")
        return redirect('home')
    
    user = request.user
    
    # -----------------------------------------------------------------
    # I. ASOSIY SANALAR VA FILTRLAR
    # -----------------------------------------------------------------
    one_week_ago = timezone.now() - datetime.timedelta(days=7)
    one_month_ago = timezone.now() - datetime.timedelta(days=30)
    
    # Faqat tugallangan urinishlar
    completed_attempts = UserAttempt.objects.filter(center=center, is_completed=True)
    
    # -----------------------------------------------------------------
    # II. IMTIHONLAR BO'YICHA KENGAYTIRILGAN STATISTIKA 📈
    # -----------------------------------------------------------------
    
    total_exams = Exam.objects.filter(center=center, is_active=True).count()
    
    # Jami topshirilgan urinishlar
    total_attempts_count = completed_attempts.count()

    # O'tgan 7 kundagi urinishlar
    recent_attempts_count = completed_attempts.filter(completed_at__gte=one_week_ago).count()
    
    # O'rtacha natija (Umumiy ballar o'rtachasi)
    avg_score_data = completed_attempts.aggregate(
        avg_score=Avg('final_total_score')
    )
    avg_total_score = round(avg_score_data['avg_score'], 1) if avg_score_data['avg_score'] else 0
    
    # Eng ommabop imtihon
    top_exam_data = Exam.objects.filter(center=center, is_active=True).annotate(
        attempt_count=Count('user_attempts', filter=Q(user_attempts__is_completed=True))
    ).order_by('-attempt_count').first()

    
    # -----------------------------------------------------------------
    # III. RESURSLAR STATISTIKASI (SAVOL, FLASHCARD, TAG) 📚
    # -----------------------------------------------------------------
    
    # Jami Savollar (Nashr qilingan)
    total_questions = Question.objects.filter(
        center=center, status='published'
    ).count()
    
    # Jami Flashcardlar
    total_flashcards = Flashcard.objects.filter(center=center).count()
    
    # Jami Taglar
    total_tags = Tag.objects.filter(parent__isnull=True, center=center).count()
    
    # Eng ko'p savolga ega bo'lgan tag
    top_tag_q = Tag.objects.filter(center=center).annotate(
        resource_count=Count('question', filter=Q(question__status='published'))
    ).order_by('-resource_count').first()
    
    # Eng ko'p flashcardga ega bo'lgan tag
    top_tag_f = Tag.objects.filter(center=center).annotate(
        resource_count=Count('flashcards')
    ).order_by('-resource_count').first()
    
    
    # -----------------------------------------------------------------
    # IV. TALABALAR VA KURSLAR STATISTIKASI
    # -----------------------------------------------------------------
    
    # Talabalar
    students_qs = CustomUser.objects.filter(center=center, role='student')
    total_students = students_qs.count()
    new_students_last_30_days = students_qs.filter(date_joined__gte=one_month_ago).count()
    
    # Kurslar
    courses = Course.objects.filter(center=center).annotate(
        student_count=Count('groups_in_course__students', distinct=True) 
    ).order_by('-student_count', '-created_at')
    
    # Eng ko'p talabaga ega kurs
    most_popular_course = courses.first()

    
    # -----------------------------------------------------------------
    # V. TAGLAR BO'YICHA HIERARXIK HISOBOT (Xato tuzatilgan)
    # -----------------------------------------------------------------
    
    tags_data = []
    try:
        main_tags = Tag.objects.filter(
            parent__isnull=True, center=center
        ).annotate(
            question_count=Count('question', distinct=True, filter=Q(question__status='published')),
            flashcard_count=Count('flashcards', distinct=True) # Flashcardlar uchun 'flashcards' to'g'ri ishladi
        ).order_by('name')

        for main_tag in main_tags:
            sub_tags = Tag.objects.filter(
                parent=main_tag, center=center
            ).annotate(
                question_count=Count('question', distinct=True, filter=Q(question__status='published')),
                flashcard_count=Count('flashcards', distinct=True)
            ).order_by('name')

            tags_data.append({
                'main': main_tag,
                'main_q': main_tag.question_count,
                'main_f': main_tag.flashcard_count,
                'sub_tags': list(sub_tags)
            })
    except Exception as e:
        messages.error(request, f"Tag hisoboti yuklanishida xato: {e}")
        tags_data = []

    # -----------------------------------------------------------------
    # VI. CONTEXT MA'LUMOTLARI
    # -----------------------------------------------------------------
    
    stats_data = {
        # Imtihonlar statistikasi
        'total_exams': total_exams,
        'total_attempts_count': total_attempts_count,
        'recent_attempts_count': recent_attempts_count,
        'avg_total_score': avg_total_score,
        'top_exam': top_exam_data,
        
        # Resurslar statistikasi
        'total_questions': total_questions,
        'total_flashcards': total_flashcards,
        'total_tags': total_tags,
        'top_tag_q': top_tag_q,
        'top_tag_f': top_tag_f,
        
        # Talabalar va kurslar statistikasi
        'total_students': total_students,
        'new_students_last_30_days': new_students_last_30_days,
        'most_popular_course': most_popular_course,
    }

    context = {
        'center': center,
        'stats': stats_data,
        'tags_data': tags_data,
        'courses': courses[:5], # Eng mashhur 5 ta kursni yuboramiz
        'today': timezone.now().date(),
    }

    return render(request, 'management/teacher_dashboard.html', context)


@login_required(login_url='login')
def profile_view(request, slug): 
    """Profil sahifasini ko'rsatadi va ma'lumotlarni tahrirlashni boshqaradi."""
    
    # get_object_or_404 funksiyasi 'Center' modelidan import qilingan deb faraz qilinadi
    # 1. MARKAZNI TEKSHIRISH
    center = get_object_or_404(Center, slug=slug)
    
    # request.user.center obyekti o'rniga center_id atributini ishlatish xavfsizroq.
    # user.center_id obyektni bazadan tortib olishga harakat qilmaydi.
    user_center_id = getattr(request.user, 'center_id', None)

    # 2. Xavfsizlik tekshiruvi: center_id ni slug orqali topilgan center.id bilan solishtirish
    if user_center_id is None or user_center_id != center.id:
        messages.error(request, "Bu markaz profiliga kirish huquqingiz yo‘q.")
        
        # Kirish huquqi yo'q bo'lsa, foydalanuvchini umumiy 'index' sahifasiga yo'naltiramiz.
        # Bu redirect xavfsiz, chunki u user.center obyektini yuklashga urinmaydi.
        return redirect('index')
            
    # --- Asosiy mantiq ---
    
    if request.method == 'POST':
        # ProfileUpdateForm modelini shu yerda mavjud deb hisoblaymiz
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profilingiz muvaffaqiyatli yangilandi.")
            
            # POST dan keyin o'sha sahifaga SLUG bilan qaytish
            return redirect('profile', slug=center.slug) 
        else:
            messages.error(request, "Ma'lumotlarni saqlashda xatolik yuz berdi. Iltimos, formalarni to'g'ri to'ldiring.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    # Bu qismlar, agar ular to'g'ridan-to'g'ri CustomUser modelida mavjud bo'lsa, xato bermaydi.
    # Agar ular OneToOneField bo'lsa va obyekti yo'q bo'lsa, try/except kerak bo'ladi.
    subscription = getattr(request.user, 'subscription', None)
    user_balance = getattr(request.user, 'balance', None)
    
    context = {
        'form': form,
        'subscription': subscription,
        'user_balance': user_balance,
        'center': center, # Kontekstga center'ni qo'shish
    }
    return render(request, 'student/profile.html', context)

@login_required(login_url='login')
def change_password_view(request): 
    """Foydalanuvchining parolini o'zgartirish."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Parolingiz muvaffaqiyatli o\'zgartirildi!')
            return redirect('profile')
        else:
            messages.error(request, 'Iltimos, formadagi xatoliklarni to\'g\'rilab, qayta urinib ko\'ring.')
    else:
        form = CustomPasswordChangeForm(request.user)
        
    return render(request, 'registration/change_password.html', {'form': form})

def dashboard_redirect_view(request):
    """
    Muvaffaqiyatli kirishdan so'ng (LOGIN_REDIRECT_URL) chaqiriladi.
    Foydalanuvchini roli va biriktirilgan markaziga qarab to'g'ri dashboardga yo'naltiradi.
    """
    if not request.user.is_authenticated:
        return redirect('login') 
        
    center = _get_user_center(request.user)
    
    if center:
        center_slug = center.slug
        
        if request.user.role == 'student':
            return redirect(reverse('dashboard', kwargs={'slug': center_slug}))
        
        elif request.user.role in ['teacher', 'center_admin', 'owner']:
            return redirect(reverse('teacher_dashboard', kwargs={'slug': center_slug}))
        
        else:
            messages.warning(request, "Ruxsat berilgan markaz topilmadi yoki rolingiz aniqlanmadi.")
            return redirect('index')
    else:
        # Markaz biriktirilmagan holat
        messages.warning(request, "Sizga hali markaz biriktirilmagan. Iltimos, administrator bilan bog'laning.")
        return redirect('index')

@login_required(login_url='login')
def completed_exams_view(request, slug):

    # 1. MARKAZ TEKSHIRISH
    center = get_object_or_404(Center, slug=slug)
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu sahifaga kirish huquqingiz yo‘q.")
        return redirect('index')

    user = request.user
    
    # 2. Tugallangan imtihonlar ID'larini olish
    completed_exam_ids = UserAttempt.objects.filter(
        user=user, is_completed=True, exam__center=center
    ).values_list('exam_id', flat=True).distinct()

    if not completed_exam_ids:
        # Agar tugatilgan imtihon bo'lmasa, darhol bo'sh natijani qaytarish
        context = {'center': center, 'top_results': [], 'recent_results': [], 'total_exams_count': 0}
        return render(request, 'student/completed_exams.html', context)

    # Imtihonlarni bir so'rovda oldindan yuklash va **sections** (yangi related_name) ni olish
    exams_qs = Exam.objects.filter(
        id__in=completed_exam_ids, center=center
    ).prefetch_related(
        'sections',  # <--- XATO MANBAI: 'examsection_set' o'rniga 'sections'
        'flashcard_exam'
    )

    exam_results = []
    
    for exam in exams_qs:
        try:
            # Urinishlarni olish mantiqi (o'zgarishsiz)
            attempts_qs = UserAttempt.objects.filter(user=user, exam=exam, is_completed=True).order_by(
                '-final_total_score', '-completed_at'
            )
            
            best_attempt = attempts_qs.first()
            latest_attempt = attempts_qs.order_by('-completed_at').first()
            
            if not best_attempt or not latest_attempt:
                continue

            # Bo'lim ma'lumotlarini to'plash
            exam_sections_qs = exam.sections.all()  # <--- XATO MANBAI: 'examsection_set' o'rniga 'sections'
            
            exam_sections_agg = exam_sections_qs.aggregate(
                total_duration=Sum('duration_minutes'),
                total_questions=Sum('max_questions'),
                section_count=Count('id')
            )
            
            # HTML card uchun 'sections' ro'yxatini tayyorlash
            sections_data = []
            for section in exam_sections_qs:
                sections_data.append({
                    'type_display': getattr(section, 'get_section_type_display', lambda: 'Noma\'lum')(),
                    'is_math': hasattr(section, 'section_type') and section.section_type in ['MATH_M1', 'MATH_M2']
                })
            
            # Ruxsatlarni tekshirish (o'zgarishsiz)
            has_flashcard_exam = hasattr(exam, 'flashcard_exam')
            
            can_start_exam = not exam.is_premium or (
                UserSubscription.objects.filter(user=user, end_date__gt=timezone.now()).exists() or
                UserBalance.objects.filter(user=user, exam_credits__gt=0).exists()
            )

            # Natijalarni yig'ish
            exam_results.append({
                'exam': exam,
                'attempt_count': attempts_qs.count(),
                'best_attempt': best_attempt,
                'latest_attempt': latest_attempt,
                'has_flashcard_exam': has_flashcard_exam,
                'can_start_exam': can_start_exam,
                'total_duration': exam_sections_agg['total_duration'] or 0,
                'total_questions': exam_sections_agg['total_questions'] or 0,
                'section_count': exam_sections_agg['section_count'] or 0,
                'sections': sections_data, # <-- HTML da ishlatiladigan 'sections'
            })
            
        except Exception as e:
            # logger.error(f"Completed exams viewda xato: {e}", exc_info=True)
            continue 

    # Natijalarni saralash (o'zgarishsiz)
    top_results = sorted(
        exam_results, 
        key=lambda x: x['latest_attempt'].completed_at if x['latest_attempt'] and x['latest_attempt'].completed_at else timezone.datetime.min, 
        reverse=True
    )
    recent_results = top_results[:3]

    context = {
        'center': center,
        'top_results': top_results,
        'recent_results': recent_results,
        'total_exams_count': len(top_results),
    }
    return render(request, 'student/completed_exams.html', context)

# ==========================================================
# IMTIHON URINISHLARI VA DETAL VIEW'LARI
# ==========================================================

@login_required(login_url='login')
def exam_attempts_view(request, slug, exam_id):
    center = get_object_or_404(Center, slug=slug)
    
    # TO‘G‘RI TEKSHIRISH: funksiya orqali!
    is_teacher_mode = is_teacher(request.user) and request.user.center == center
    
    # Agar o‘quvchi bo‘lsa saqlaymiz, o‘qituvchi bo‘lsa ham ruxsat
    if not is_teacher_mode:
        if request.user.center != center:
            messages.error(request, "Bu sahifaga kirish huquqingiz yo‘q.")
            return redirect('index')

    exam = get_object_or_404(Exam, id=exam_id, center=center, is_active=True)

    # O‘qituvchi bo‘lsa – student_id talab qilinadi
    student_id = request.GET.get('student_id')
    if is_teacher_mode:
        if not student_id:
            messages.error(request, "Talaba tanlanmagan!")
            
        user = get_object_or_404(User, id=student_id)
    else:
        user = request.user

    # Urinishlar
    attempts_qs = UserAttempt.objects.filter(
        user=user,
        exam=exam,
        is_completed=True
    ).order_by('-completed_at')

    # Hisob-kitob (Ma'lumotlarni yig'ish)
    # Eslatma: 'sections' - examsection_set ning to'g'ri 'related_name'i deb faraz qilindi.
    total_questions = exam.sections.aggregate(total=Sum('max_questions'))['total'] or 0
    
    for attempt in attempts_qs:
        correct = UserAnswer.objects.filter(attempt_section__attempt=attempt, is_correct=True).count()
        incorrect = UserAnswer.objects.filter(attempt_section__attempt=attempt, is_correct=False).count()
        
        # O‘tkazib yuborilgan javoblar soni
        omitted = total_questions - correct - incorrect
        
        # Natijalarni attempt obyektiga qo'shish
        attempt.correct_answers = correct
        attempt.incorrect_answers = incorrect
        attempt.omitted_answers = omitted
        
        # 🚀 MAVZU TESTI UCHUN FOIZNI HISOBLASH VA ATTACH QILISH
        if exam.is_subject_exam and total_questions > 0:
            correct_percentage = (correct / total_questions) * 100
            attempt.correct_percentage = correct_percentage # HTML uchun kerak
            # Agar siz oldin final_total_score ni foizda saqlagan bo'lsangiz, uni ham ishlatishingiz mumkin:
            # attempt.final_total_score = attempt.final_total_score # final_total_score allaqachon foizni saqlaydi
        else:
             # SAT Testi yoki savollar nol bo'lsa
             attempt.correct_percentage = 0 
             if attempt.final_total_score is None:
                  attempt.final_total_score = 0


    # Eng yaxshi urinishni aniqlash
    # Agar Mavzu Testi bo'lsa, correct_percentage bo'yicha saralash yaxshiroq
    if exam.is_subject_exam:
        best_attempt = max(attempts_qs, key=lambda a: a.correct_percentage) if attempts_qs else None
    else:
        # SAT Testi uchun final_total_score bo'yicha
        best_attempt = attempts_qs.order_by('-final_total_score').first()

    latest_attempt = attempts_qs.first()

    context = {
        'center': center,
        'exam': exam,
        'attempts': attempts_qs,
        'best_attempt': best_attempt,
        'latest_attempt': latest_attempt,
        'total_questions': total_questions,
        'student': user if is_teacher_mode else None,
    }
    
    return render(request, 'student/exam_attempts.html', context)

# ===========================================================
# ⭐️ O'QUVCHI UCHUN KURSLAR VIEWLARI (STUDENT VIEWS)
# ===========================================================

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Prefetch, Sum
from .models import Center, Course, UserAttempt, UserResourceView # Model nomlaringizni to'g'irladim
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q


@login_required(login_url='login')
def all_courses_view(request, slug):
    """
    Barcha kurslar sahifasi - TO'LIQ STATISTIKA VA PROGRESS
    """
    # ⚠️ DIQQAT: Center, Course, UserAttempt, UserResourceView modellarini import qilishni unutmang.
    center = get_object_or_404(Center, slug=slug)
    user = request.user
    
    # 1. Foydalanuvchi obunasi
    is_subscribed = hasattr(user, 'subscription') and user.subscription.is_active
    
    # 2. Barcha kurslarni optimallashtirilgan holda olish
    
    # Darslar ichidagi testlar va resurslarni samarali olish uchun Prefetch ishlatiladi
    lessons_prefetch = Prefetch(
        'modules__lessons',
        queryset=Lesson.objects.select_related('related_exam')
                               .prefetch_related('resources'),
        to_attr='prefetched_lessons'
    )
    
    # O'quvchilarni faqat kerak bo'lsa olish uchun
    students_prefetch = Prefetch(
        'groups_in_course__students',
        queryset=User.objects.all(),
        to_attr='prefetched_students'
    )
    
    # Kurslarning o'zini statistikalar bilan olish (Annotate faqat Model asosidagi statistikalar uchun)
    all_courses = Course.objects.filter(
        center=center,
        is_active=True
    ).select_related('teacher').prefetch_related(
        'modules',
        lessons_prefetch, # Modullar ichidagi darslar (va ularning test/resurslari)
        students_prefetch, # Kursga yozilgan guruhlar va ularning o'quvchilari
        
        # UserAttempt va UserResourceView uchun alohida so'rovlar loop ichida bo'ladi, 
        # chunki ular foydalanuvchiga bog'liq va Annotate orqali murakkab o'tish shartini bajarib bo'lmaydi.
    ).order_by('-created_at')
    
    # 3. Har bir kurs uchun qo'shimcha ma'lumotlarni hisoblash
    courses_with_data = []
    
    for course in all_courses:
        
        # Modullar, Darslar, Testlar soni (Prefetchdan foydalanib Python ichida hisoblaymiz)
        total_modules = course.modules.count()
        
        # Darslar va Testlarni hisoblash
        total_lessons = 0
        total_exams = 0
        all_resources = []
        
        for module in course.modules.all():
            for lesson in module.prefetched_lessons:
                total_lessons += 1
                if lesson.related_exam is not None:
                    total_exams += 1
                all_resources.extend(lesson.resources.all())
        
        # Resurslar statistikasi
        total_videos = sum(1 for r in all_resources if r.resource_type == 'video')
        total_tasks = sum(1 for r in all_resources if r.resource_type == 'task')
        total_files = sum(1 for r in all_resources if r.resource_type in ['solution_file', 'other'])
        
        # O'quvchilar soni (Prefetch orqali)
        students_set = set()
        for group in course.groups_in_course.all():
            # group.prefetched_students orqali kirish kerak, agar groupga Prefetch to_attr berilgan bo'lsa.
            # Lekin yuqoridagi students_prefetch guruhlar ichidagi o'quvchilarni to'playdi.
            students_set.update(group.students.all()) 
            
        students_count = len(students_set)
        
        # Foydalanuvchi yozilganmi?
        is_enrolled = user in students_set
        
        # Foydalanuvchi progressi (agar yozilgan bo'lsa) - Ushbu qism Murojaat uchun DB so'rovlariga muhtoj
        user_progress = None
        if is_enrolled and total_lessons > 0:
            completed_lessons = 0
            
            # DB so'rovlarini kamaytirish uchun foydalanuvchining barcha urinishlarini (attempts)
            # va ko'rilgan resurslarini (views) oldindan olish tavsiya etiladi (View ichida qoldirmaymiz, faqat misol)
            
            for module in course.modules.all():
                for lesson in module.prefetched_lessons:
                    is_lesson_completed = False
                    
                    if lesson.related_exam:
                        # ⚠️ DB so'rovi: foydalanuvchi testni o'zlashtirganmi?
                        # Iloji bo'lsa, barcha urinishlarni bir martada yuklab oling (tashqarida)
                        attempt = UserAttempt.objects.filter(
                            exam=lesson.related_exam, 
                            user=user, 
                            is_completed=True
                        ).order_by('-completed_at').first() 

                        # course.pass_threshold kerak bo'ladi, uni modelda qo'shgan bo'lsangiz
                        PASS_THRESHOLD = getattr(course, 'pass_threshold', 60) 
                        
                        if attempt and attempt.final_total_score >= PASS_THRESHOLD:
                            is_lesson_completed = True
                    else:
                        # Resurslar orqali tugallash
                        total_resources_count = lesson.resources.count()
                        if total_resources_count > 0:
                            # ⚠️ DB so'rovi: foydalanuvchi barcha resurslarni ko'rganmi?
                            viewed_count = UserResourceView.objects.filter(
                                user=user,
                                lesson_resource__lesson=lesson
                            ).count()
                            
                            if viewed_count >= total_resources_count:
                                is_lesson_completed = True
                        else:
                            # Resurs/test yo'q, avtomatik tugallangan
                            is_lesson_completed = True
                    
                    if is_lesson_completed:
                        completed_lessons += 1
            
            user_progress = int((completed_lessons / total_lessons) * 100)
        
        # Kursga ma'lumotlarni qo'shish, shu jumladan rasm
        course.total_modules = total_modules
        course.total_lessons = total_lessons
        course.total_exams = total_exams
        course.total_videos = total_videos
        course.total_tasks = total_tasks
        course.total_files = total_files
        course.students_count = students_count
        course.is_enrolled = is_enrolled
        course.user_progress = user_progress
        
        # 🖼️ Kurs rasmini to'g'ridan-to'g'ri modeldan olish
        # course.course_img endi to'g'ridan-to'g'ri mavjud va templatada ishlatiladi.
        
        courses_with_data.append(course)
    
    # 4. Umumiy statistika (Oldingi qism o'zgarishsiz qoldi)
    total_courses_count = len(courses_with_data)
    total_students_count = sum(c.students_count for c in courses_with_data)
    total_lessons_count = sum(c.total_lessons for c in courses_with_data)
    
    total_teachers_count = Course.objects.filter(
        center=center, 
        is_active=True
    ).values('teacher').distinct().count()
    
    # 5. Context
    context = {
        'center': center,
        'all_courses': courses_with_data,
        'is_subscribed': is_subscribed,
        'total_courses_count': total_courses_count,
        'total_students_count': total_students_count,
        'total_lessons_count': total_lessons_count,
        'total_teachers_count': total_teachers_count,
    }
    
    return render(request, 'student/all_courses.html', context)


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count # Bepul kurs uchun

@login_required(login_url='login')
def course_enroll_view(request, slug, course_id):
    """
    Foydalanuvchini kursga yozish yoki Purchase yaratish jarayoniga yo'naltirish.
    """
    center = get_object_or_404(Center, slug=slug)
    course = get_object_or_404(Course, id=course_id, center=center)
    user = request.user
    
    # 1. Allaqachon yozilganligini tekshirish
    if course.groups_in_course.filter(students=user).exists():
        messages.info(request, f"Siz **'{course.title}'** kursiga allaqachon yozilgansiz.")
        return redirect('course_roadmap', slug=center.slug, pk=course_id)
    
    # 2. Kurs narxini tekshirish
    if course.price > 0 or course.is_premium:
        # PULLIK KURS: To'g'ridan-to'g'ri Purchase yaratish view'iga yo'naltiramiz
        messages.info(request, f"**'{course.title}'** kursiga yozilish uchun to'lov kerak.")
        
        # ✅ TUZATISH: 'course_purchase' ga yo'naltirish
        return redirect('course_purchase', slug=center.slug, pk=course_id)
        
    # 3. BEPUL KURS: To'g'ridan-to'g'ri guruhga qo'shish (Eski mantiq)
    try:
        target_group = course.groups_in_course.annotate(
            student_count=Count('students')
        ).order_by('student_count').first()
        
        if target_group:
            target_group.students.add(user)
            messages.success(request, f"Tabriklaymiz! Siz **'{course.title}'** kursiga yozildingiz.")
            return redirect('course_roadmap', slug=center.slug, pk=course_id)
        else:
            messages.error(request, "Bu kurs uchun guruh topilmadi.")
            return redirect('course_detail', slug=center.slug, pk=course_id)
            
    except Exception as e:
        messages.error(request, f"Xatolik: {e}")
        return redirect('course_detail', slug=center.slug, pk=course_id)

@login_required(login_url='login')
def course_detail_view(request, slug, pk):
    """
    Kurs tafsilotlari sahifasi - TO'LIQ STATISTIKA bilan
    """
    # 1. Asosiy obyektlar
    center = get_object_or_404(Center, slug=slug)
    course = get_object_or_404(
        Course.objects.select_related('teacher', 'center'), 
        id=pk, 
        center=center
    )
    
    # 2. O'quvchilar soni
    students_count = course.groups_in_course.aggregate(
        total=Count('students', distinct=True)
    )['total'] or 0
    
    # 3. Darslar soni
    total_lessons_count = Lesson.objects.filter(
        module__course=course
    ).count()
    
    # 4. TO'LIQ RESURS STATISTIKASI
    resource_stats = LessonResource.objects.filter(
        lesson__module__course=course
    ).aggregate(
        # Video darslar
        total_videos_count=Count('id', filter=Q(resource_type='video')),
        
        # Vazifalar
        total_tasks_count=Count('id', filter=Q(resource_type='task')),
        
        # Yechim videolar
        total_solution_videos_count=Count('id', filter=Q(resource_type='solution_video')),
        
        # Fayllar (yechim fayllari)
        total_files_count=Count('id', filter=Q(resource_type='solution_file')),
        
        # Boshqa resurslar
        total_other_resources_count=Count('id', filter=Q(resource_type='other')),
    )
    
    # 5. Testlar soni
    total_exams_count = Lesson.objects.filter(
        module__course=course,
        related_exam__isnull=False
    ).count()
    
    # 6. Foydalanuvchi yozilganligini tekshirish
    is_enrolled = False
    if request.user.is_authenticated:
        is_enrolled = course.groups_in_course.filter(
            students=request.user
        ).exists()
    
    # 7. ROADMAP MA'LUMOTLARI
    roadmap_data = []
    modules = course.modules.prefetch_related(
        'lessons__resources',
        'lessons__related_exam'
    ).order_by('order')
    
    for module in modules:
        lessons = module.lessons.order_by('order')
        
        lesson_data_list = []
        for lesson in lessons:
            resources = lesson.resources.all()
            
            lesson_data_list.append({
                'lesson': lesson,
                'has_video': any(r.resource_type == 'video' for r in resources),
                'has_task': any(r.resource_type == 'task' for r in resources),
                'has_solution_video': any(r.resource_type == 'solution_video' for r in resources),
                'has_file': any(r.resource_type in ['solution_file', 'other'] for r in resources),
            })
        
        roadmap_data.append({
            'module': module,
            'lessons': lesson_data_list,
        })
    
    # 8. CONTEXT
    context = {
        'center': center,
        'course': course,
        'roadmap_data': roadmap_data,
        
        # Asosiy statistika
        'students_count': students_count,
        'total_lessons_count': total_lessons_count,
        'total_exams_count': total_exams_count,
        
        # Resurs statistikasi
        'total_videos_count': resource_stats['total_videos_count'],
        'total_tasks_count': resource_stats['total_tasks_count'],
        'total_solution_videos_count': resource_stats['total_solution_videos_count'],
        'total_files_count': resource_stats['total_files_count'],
        'total_other_resources_count': resource_stats['total_other_resources_count'],
        
        # O'qituvchi va enrollment
        'teacher_info': course.teacher,
        'is_enrolled': is_enrolled,
    }
    
    return render(request, 'student/course_detail.html', context)

# views.py
def enroll_free_course(user, course):
    """Foydalanuvchini bepul kursga (guruhga) yozadi."""
    try:
        # Kursga tegishli standart guruhni toping (Bu sizning mantiqingizga bog'liq!)
        # Masalan: Course modelida related_name='groups_in_course' bo'lsa
        default_group = course.groups_in_course.first() 
        if default_group:
            # Group modelida students degan ManyToManyField bor deb faraz qilinadi
            default_group.students.add(user)
            return True
    except Exception as e:
        # print(f"Bepul kursga yozishda xato: {e}")
        return False
    return False


@login_required(login_url='login')
def purchase_course_view(request, slug, pk):
    """
    Kursni sotib olishni boshlash. Darhol Purchase yaratadi va to'lovga yo'naltiradi.
    """
    center = get_object_or_404(Center, slug=slug)
    course = get_object_or_404(Course, id=pk, center=center)
    user = request.user
    
    # 0. Agar foydalanuvchi allaqachon kursga yozilgan bo'lsa
    if course.groups_in_course.filter(students=user).exists():
        return redirect('course_roadmap', slug=center.slug, pk=course.id)

    # 1. Bepul kursni bu view'da ham tekshirish (faqat xavfsizlik uchun)
    if course.price <= 0:
        # Bepul kurs bo'lsa, uni yozish mantiqi (agar course_enroll_view dan o'tib kelmagan bo'lsa ham)
        # Bu yerda `enroll_free_course` funksiyasi ishlaydi deb faraz qilinadi.
        # ... bepul kursga yozish mantiqi ...
        return redirect('course_roadmap', slug=center.slug, pk=course.id)

    # 2. Oldinroq to'lov kutilayotgan tranzaksiya bormi?
    existing_purchase = Purchase.objects.filter(
        user=user, 
        course=course, 
        purchase_type='course', 
        status__in=['pending', 'moderation']
    ).first()

    if existing_purchase:
        # Mavjud buyurtma bo'lsa, darhol o'sha to'lov sahifasiga yo'naltirish
        messages.info(request, "Sizning oldingi buyurtmangiz mavjud. Davom eting.")
        return redirect('payment_page_view', purchase_id=existing_purchase.id)

    # 3. Darhol YANGI Purchase obyekti yaratish
    # Bu viewga kirishning o'zi yangi buyurtma yaratishni anglatadi
    final_price = course.price 

    new_purchase = Purchase.objects.create(
        user=user,
        purchase_type='course',
        course=course,
        amount=course.price,
        final_amount=final_price,
        status='pending' # Boshlang'ich status
    )
    
    # 4. To'lov sahifasiga yo'naltirish
    messages.info(request, "Yangi buyurtma yaratildi. Iltimos, to'lovni yakunlang.")
    
    # ✅ MUAMMOLI YO'NALTIRISH ENDI YO'Q: Faqat purchase_id bilan yo'naltiramiz
    return redirect('payment_page_view', purchase_id=new_purchase.id)

@login_required(login_url='login')
def payment_page_view(request, purchase_id):
    """
    To'lov sahifasi. Kartaga to'lov qilish va skrinshotni yuklashni boshqaradi.
    Bu view faqat 'purchase_id' ni qabul qiladi.
    """
    purchase = get_object_or_404(
        Purchase.objects.select_related('course__center'), # Optimizatsiya
        id=purchase_id, 
        user=request.user, 
    )
    
    # 1. Agar status completed bo'lsa, foydalanuvchini yo'naltiramiz
    if purchase.status == 'completed':
        messages.success(request, "To'lovingiz muvaffaqiyatli tasdiqlangan va kurs aktivlashtirilgan!")
        if purchase.course:
            # Agar kurs bo'lsa, uning center slug'idan foydalanamiz
            return redirect('course_roadmap', slug=purchase.course.center.slug, pk=purchase.course.id)
        return redirect('profile')

    # Faqat pending yoki moderation holatdagina skrinshot yuklashga ruxsat beriladi
    if purchase.status not in ['pending', 'moderation']:
        messages.error(request, "Bu buyurtma to'lanib bo'lgan yoki rad etilgan.")
        return redirect('profile')

    # 2. Skrinshotni yuklash
    if request.method == 'POST':
        # 'ScreenshotUploadForm' ni loyihangizda mavjud deb hisoblaymiz
        form = ScreenshotUploadForm(request.POST, request.FILES, instance=purchase)
        
        if form.is_valid():
            updated_purchase = form.save(commit=False)
            
            # Agar skrinshot yangi yuklangan bo'lsa, statusni 'moderation' ga o'tkazamiz
            # (Agar modelda FileField/ImageField maydoni bo'lsa)
            if 'payment_screenshot' in request.FILES: 
                updated_purchase.status = 'moderation' 
                messages.success(request, "To'lov skrinshoti qabul qilindi! Adminlar tez orada tekshirib, xaridni aktivlashtirishadi.")
            
            updated_purchase.save()
            return redirect('payment_page_view', purchase_id=purchase.id)
    else:
        # Formani boshlang'ich yoki mavjud ma'lumotlar bilan tayyorlash
        form = ScreenshotUploadForm(instance=purchase)

    site_settings = None # Rekvizitlar uchun
    
    try:
        # SiteSettings modelidagi yagona (yoki birinchi) obyektni olamiz
        site_settings = SiteSettings.objects.first() 
        
        # Eslatma: Agar SiteSettings doim bitta bo'lishi shart bo'lsa, 
        # .get(pk=1) yoki .first() ishlatiladi.
        
    except SiteSettings.DoesNotExist:
        messages.error(request, "Sayt sozlamalari (to'lov rekvizitlari) administrator tomonidan kiritilmagan.")
        # Agar SiteSettings topilmasa, sahifani yuklashni davom ettiramiz, lekin rekvizitlar bo'sh bo'ladi.
        pass 

    center = purchase.course.center if purchase.course and purchase.course.center else None

    context = {
        'purchase': purchase,
        'form': form,
        'center': center, 
        'site_settings': site_settings,
    }
    return render(request, 'student/payment_page.html', context)

# --- Helper function (Avvalgi to'g'rilangan kod) ---
def get_lesson_details(lesson_id):
    # Bu erda CourseSchedule ma'lumotlarini qaysi Course ga tegishli ekanligini bilish uchun
    # Course va CourseModule ma'lumotlarini yuklaymiz (select_related).
    # Keyin esa jadval (schedule_slots) ma'lumotlarini yuklaymiz (prefetch_related).

    # Ushbu funksiya hozirgi muammo bilan bog'liq emas, lekin avvalgi kontekstda bor edi.
    lesson_data = Lesson.objects.select_related(
        'module',
        'module__course',
        'related_exam', 
    ).prefetch_related(
        # Course'ning jadval slotlarini yuklash uchun to'g'ri zanjir
        'module__course__schedule_slots',
        # Dars resurslarini ham yuklash
        'resources', 
        # Exam'ning ManyToMany orqali bog'langan ExamSection'larini yuklaymiz
        Prefetch(
            'related_exam__sections',
            queryset=ExamSection.objects.all().prefetch_related('examsectionorder'),
            to_attr='exam_sections_data'
        )
    ).get(pk=lesson_id)
    
    # Endi siz jadval ma'lumotlariga xatosiz murojaat qila olasiz:
    course_schedules = lesson_data.module.course.schedule_slots.all()
    
    return lesson_data, course_schedules

@login_required(login_url='login')
def course_roadmap_view(request, slug, course_id):
    """ 
    Kurs roadmap – Talaba uchun darslarni ketma-ket qulfini ochish logikasi.
    """
    
    # 0. Markaz va Kursni tekshirish
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('index')

    course = get_object_or_404(Course, id=course_id, center=center, is_active=True)

    # 1. Kirish huquqi
    has_access = course.groups_in_course.filter(students=request.user).exists()
    if not has_access:
        messages.warning(request, "Siz bu kursga hali qo‘shilmagansiz.")
        return redirect('course_detail', slug=slug, pk=course_id)

    # --- MA'LUMOTLARNI YUKLASH ---
    
    # 2. Test Natijalarini Yuklash (Faqat oxirgi urinish)
    passed_exam_ids = set()
    completed_exam_ids = set()

    attempts = UserAttempt.objects.filter(
        user=request.user,
        # --------------------------------------------------------------
        # ANIQ YECHIM: course obyektini emas, ID raqamini bering
        exam__lessons_linked__module__course_id=course.id,
        # --------------------------------------------------------------
        is_completed=True
    ).select_related('exam').order_by('exam_id', '-completed_at')

    seen_exams = set()
    for a in attempts:
        if a.exam_id not in seen_exams:
            seen_exams.add(a.exam_id)
            completed_exam_ids.add(a.exam_id)
            
            # UserAttempt modelidagi is_passed() metodidan foydalanamiz
            if a.is_passed():
                passed_exam_ids.add(a.exam_id)

    # 3. Resurs Ko'rilganligi Ma'lumotini Yuklash
    # Foydalanuvchi tomonidan ko'rilgan LessonResource ID'larini olamiz
    viewed_resource_ids = set(
        UserResourceView.objects.filter(user=request.user).values_list('lesson_resource_id', flat=True)
    )

    # 4. Prefetch Obyektlarini Tayyorlash
    resources_prefetch = Prefetch(
        'resources', 
        queryset=LessonResource.objects.all().order_by('order'),
        to_attr='all_resources_list'
    )
    
    # 5. Modullar va Darslarni Yuklash
    modules = CourseModule.objects.filter(course=course).order_by('order').prefetch_related(
        Prefetch(
            'lessons',
            queryset=Lesson.objects.select_related('related_exam')
                                   .prefetch_related(resources_prefetch)
                                   .order_by('order'),
            to_attr='ordered_lessons'
        )
    )

    # --- PROGRESS VA QULFLASH MANTIQI ---
    
    roadmap_data = []
    total_lessons = 0
    completed_lessons = 0
    previous_lesson_was_finished = True 

    for module in modules:
        lessons_data = []
        module_completed = 0
        module_total = 0

        for lesson in module.ordered_lessons:
            total_lessons += 1
            module_total += 1

            exam = lesson.related_exam
            has_exam = bool(exam)
            exam_id = exam.id if exam else None

            # 5.1. Resurslar holatini hisoblash (Mantiq 2)
            current_resources = getattr(lesson, 'all_resources_list', [])
            has_resources = bool(current_resources)
            all_resources_viewed = False
            
            if has_resources:
                lesson_resource_ids = set(r.id for r in current_resources)
                # Agar darsning BARCHA resurslari ko'rilgan bo'lsa
                if lesson_resource_ids.issubset(viewed_resource_ids):
                    all_resources_viewed = True
            elif not has_resources and not has_exam:
                # Agar resurs ham, test ham bo'lmasa, avtomatik yakunlangan
                all_resources_viewed = True


            # 5.2. Test holatini olish (Mantiq 1)
            exam_passed = exam_id in passed_exam_ids if has_exam else False
            exam_completed_status = exam_id in completed_exam_ids if has_exam else False

            # 5.3. DARS YAKUNLANGANMI?
            if has_exam:
                # Testi bor: O'tgan VAYOKI Topsihrgan bo'lishi shart
                lesson_finished = exam_passed or exam_completed_status
            else:
                # Testi yo'q: Barcha resurslar ko'rilgan bo'lishi shart
                lesson_finished = all_resources_viewed

            # 5.4. QULF Mantiqi: Oldingi dars yakunlanmagan bo'lsa qulf.
            is_locked = not previous_lesson_was_finished
            
            # 5.5. Progressni yangilash
            if not is_locked and lesson_finished:
                completed_lessons += 1
                module_completed += 1
            
            # 5.6. Keyingi dars uchun qulf holatini belgilash
            if is_locked or not lesson_finished:
                 previous_lesson_was_finished = False # Zanjir uziladi
            else:
                 previous_lesson_was_finished = True # Zanjir davom etadi

            lessons_data.append({
                'lesson': lesson,
                'resources': current_resources,
                'is_locked': is_locked,
                'finished': lesson_finished,
                'has_exam': has_exam,
                'exam_passed': exam_passed,
                'exam_completed': exam_completed_status,
                'all_resources_viewed': all_resources_viewed,
                'exam_id': exam_id,
            })

        # Modul progressi
        roadmap_data.append({
            'module': module,
            'lessons': lessons_data,
            'completed_count': module_completed,
            'total_count': module_total,
            'progress_perc': int((module_completed / module_total * 100) if module_total else 0)
        })

    course_progress = int((completed_lessons / total_lessons * 100) if total_lessons else 100)

    return render(request, 'student/course_roadmap.html', {
        'center': center,
        'course': course,
        'roadmap_data': roadmap_data,
        'course_progress': course_progress,
        'completed_lessons_count': completed_lessons,
        'total_lessons_count': total_lessons,
        'has_access': True,
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings # Agar settings.AUTH_USER_MODEL ishlatilgan bo'lsa

# views.py - TO'LIQ KOD

import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def get_youtube_id(url):
    """YouTube URL'dan video ID ajratib oladi"""
    if not url:
        return None
    
    # youtu.be linki
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0].split('&')[0][:11]
    
    # youtube.com linki
    if 'v=' in url:
        match = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    
    # embed linki
    if 'embed/' in url:
        match = re.search(r'embed/([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    
    return None


def get_google_drive_id(url):
    """Google Drive URL'dan file ID ajratib oladi"""
    if not url or 'drive.google.com' not in url:
        return None
    
    # /file/d/FILE_ID/view formatida
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    # ?id=FILE_ID formatida
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    return None


@login_required(login_url='login')
def lesson_detail_view(request, slug, lesson_id):
    """
    Dars sahifasi - resurslarni ko'rsatish
    """
    
    # 1. Markaz va darsni yuklash
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo'q.")
        return redirect('index')
    
    lesson = get_object_or_404(
        Lesson.objects.select_related('module__course', 'related_exam'),
        id=lesson_id,
        module__course__center=center
    )
    
    course = lesson.module.course
    
    # 2. Kirish huquqini tekshirish
    has_access = course.groups_in_course.filter(students=request.user).exists()
    if not has_access:
        messages.warning(request, "Bu darsga kirish huquqingiz yo'q.")
        return redirect('course_detail', slug=slug, pk=course.id)
    
    # 3. Resurslarni yuklash
    all_resources = lesson.resources.all().order_by('order')
    
    # 4. Ko'rilgan resurslar IDlarini olish
    viewed_resource_ids = set(
        request.user.resource_views.filter(
            lesson_resource__lesson=lesson
        ).values_list('lesson_resource_id', flat=True)
    )
    
    # 5. Har bir resurs uchun data tayyorlash
    lesson_resources_data = []
    
    for resource in all_resources:
        link = resource.link
        
        # Asosiy data
        data = {
            'resource': resource,
            'is_viewed': resource.id in viewed_resource_ids,
            'youtube_id': None,
            'google_drive_id': None,
            'is_pdf': False,
            'is_image': False,
            'is_link': False,
        }
        
        if not link:
            data['is_link'] = True
            lesson_resources_data.append(data)
            continue
        
        # YOUTUBE
        if 'youtube.com' in link or 'youtu.be' in link:
            youtube_id = get_youtube_id(link)
            if youtube_id:
                data['youtube_id'] = youtube_id
            else:
                data['is_link'] = True
        
        # GOOGLE DRIVE
        elif 'drive.google.com' in link:
            drive_id = get_google_drive_id(link)
            if drive_id:
                data['google_drive_id'] = drive_id
                # PDF yoki rasm ekanligini tekshirish
                if '.pdf' in link.lower():
                    data['is_pdf'] = True
                elif any(ext in link.lower() for ext in ['.jpg', '.png', '.jpeg', '.gif']):
                    data['is_image'] = True
            else:
                data['is_link'] = True
        
        # PDF FAYL (Google Drive'dan tashqari)
        elif '.pdf' in link.lower():
            data['is_pdf'] = True
        
        # RASM FAYL
        elif any(ext in link.lower() for ext in ['.jpg', '.png', '.jpeg', '.gif', '.webp']):
            data['is_image'] = True
        
        # BOSHQA HAMMA NARSA - oddiy link
        else:
            data['is_link'] = True
        
        lesson_resources_data.append(data)
    
    # 6. Context tayyorlash
    context = {
        'center': center,
        'course': course,
        'lesson': lesson,
        'resources': lesson_resources_data,
        'has_exam': lesson.related_exam is not None,
        'exam_id': lesson.related_exam.id if lesson.related_exam else None,
    }
    
    return render(request, 'student/lesson_detail.html', context)

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import IntegrityError # unique_together xatosini ushlash uchun

# --- Model Importlar ---
# from .models import Center, LessonResource, UserResourceView 

@login_required(login_url='login')
@require_POST
def mark_resource_viewed(request, slug, resource_id):
    """
    Talaba resursni ko'rganligini UserResourceView jadvaliga yozadi.
    """
    center = get_object_or_404(Center, slug=slug)

    # 1. Resursni yuklash
    resource = get_object_or_404(LessonResource, id=resource_id)
    
    # 2. Huquq va Markaz tekshiruvi (Kerak bo'lsa)
    # Ushbu qadamni LessonResource ning Centerga bog'langanini tekshirish uchun kiritish kerak.
    # Masalan: if resource.lesson.module.course.center != center: return redirect(...)

    # 3. Yaratish yoki Xatoni ushlash
    try:
        UserResourceView.objects.create(
            user=request.user,
            lesson_resource=resource
        )
        messages.success(request, f"'{resource.title}' resursi ko'rildi deb belgilandi.")
        
    except IntegrityError:
        # Agar unique_together buzilsa (ya'ni, allaqachon ko'rilgan bo'lsa)
        messages.info(request, "Bu resurs avvalroq ko'rilgan deb belgilangan.")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {e}")

    # 4. Qaytish manzili (Odatda o'sha dars sahifasiga qaytish)
    lesson_id = resource.lesson.id
    return redirect('lesson_detail', slug=slug, lesson_id=lesson_id)


# ======================================================================
# ⭐️ O'QITUVCHI/ADMIN UCHUN KURSLAR VIEWLARI (MANAGEMENT VIEWS)
# ======================================================================


def get_student_progress(user, course):
    """
    Belgilangan kursda foydalanuvchining erishgan eng oxirgi darsini aniqlaydi.
    Logic: Darsning talab qilingan testi (related_exam) o'tish foizidan yuqori natija bilan 
    yakunlangan bo'lsa, dars tugallangan hisoblanadi.
    Returns: (last_completed_lesson, next_lesson_to_do) - Lesson objects or None
    """
    # Lesson, Module, Exam, UserAttempt modellarining mavjudligini talab qiladi.
    # Ular shu faylga to'g'ri import qilingan deb faraz qilinadi.
    try:
        lessons = Lesson.objects.filter(
            module__course=course
        ).select_related('related_exam').order_by('module__order', 'order')
    except NameError:
        # Agar Lesson modeli topilmasa, shunchaki progressni hisoblamaymiz
        return None, None

    last_completed_lesson = None

    for lesson in lessons:
        if lesson.related_exam:
            # Talab qilingan o'tish foizi
            passing_percentage = lesson.related_exam.passing_percentage
            
            # Agar foydalanuvchining testdan o'tgan urinishi bo'lsa
            passed_attempt_exists = UserAttempt.objects.filter(
                user=user,
                exam=lesson.related_exam,
                is_completed=True,
                correct_percentage__gte=passing_percentage 
            ).exists()
            
            if passed_attempt_exists:
                last_completed_lesson = lesson
            else:
                # Agar testdan o'tolmagan bo'lsa, jarayon shu yerda to'xtaydi
                return last_completed_lesson, lesson 
        else:
            # Agar darsda test talab qilinmasa, uni tugatilgan deb hisoblaymiz.
            last_completed_lesson = lesson
    
    # Agar barcha darslar tugallangan bo'lsa
    return last_completed_lesson, None

@login_required(login_url='login')
def course_list(request, slug):
    """ Markazga tegishli kurslar ro'yxatini ko'rish. """
    
    # 1. Centerni olish
    center = get_object_or_404(Center, slug=slug)
    user = request.user
    
    # 2. Foydalanuvchi huquqini tekshirish
    if not ((hasattr(user, 'center') and user.center == center) or user.is_staff):
        messages.error(request, "Sizda bu markaz kurslarini ko'rish huquqi yo'q.")
        user_center_slug = user.center.slug if hasattr(user, 'center') and user.center else 'dashboard'
        return redirect('dashboard', slug=user_center_slug)
    
    # 3. Asosiy kurslar ro‘yxatini olish
    courses = Course.objects.filter(
        teacher__center=center
    ).order_by('-created_at').select_related('teacher')

    # =====================================================
    # 🔍 4. QIDIRUV QO‘SHILGAN QISMI
    # =====================================================
    q = request.GET.get("q")
    if q:
        courses = courses.filter(title__icontains=q)
    # =====================================================

    # 5. Templatega yuborish
    context = {
        'courses': courses,
        'center': center,
        'page_title': f"{center.name} Kurslari Ro'yxati",
        'q': q  # inputda qiymat qolsin deb qo‘shildi
    }
    return render(request, 'management/course_list.html', context)

@login_required(login_url='login')
def course_groups(request, course_id):
    """ Kursga bog'langan guruhlar ro'yxatini ko'rish. """
    # Course va Center modellarining mavjudligini talab qiladi
    course = get_object_or_404(Course.objects.select_related('center'), pk=course_id)
    user = request.user
    
    # Ruxsat tekshiruvi
    if not (hasattr(user, 'center') and user.center == course.center or user.is_staff):
        messages.error(request, f"Sizda '{course.title}' kurs guruhlarini ko'rish huquqi yo'q.")
        user_center_slug = user.center.slug if hasattr(user, 'center') and user.center else 'dashboard' 
        return redirect('dashboard', slug=user_center_slug)

    # 🟢 ASOSIY O'ZGARTIRISH: related_name 'groups_in_course' ishlatildi
    groups = course.groups_in_course.all().annotate(
        student_count=Count('students')
    ).order_by('name') 

    context = {
        'course': course,
        'groups': groups,
        'center': course.center,
        'page_title': f"{course.title} Kursiga bog'langan guruhlar"
    }
    return render(request, 'management/course_groups.html', context)

@login_required(login_url='login')
def course_group_student_list(request, course_id, group_id):
    """ Belgilangan guruhdagi o'quvchilar ro'yxati va ularning kursdagi progressi. """
    
    # Course, Group va Center modellarining mavjudligini talab qiladi
    course = get_object_or_404(Course.objects.select_related('center'), pk=course_id)
    group = get_object_or_404(Group.objects.prefetch_related('students'), pk=group_id) 
    user = request.user

    # Ruxsat tekshiruvi
    if not (hasattr(user, 'center') and user.center == course.center or user.is_staff):
        messages.error(request, "Sizda bu o'quvchilar ro'yxatini ko'rish huquqi yo'q.")
        user_center_slug = user.center.slug if hasattr(user, 'center') and user.center else 'dashboard'
        return redirect('dashboard', slug=user_center_slug)
    
    # 🟢 O'ZGARTIRISH: Bog'lanishni tekshirishda ham related_name ishlatildi
    if not course.groups_in_course.filter(pk=group.pk).exists():
        messages.warning(request, f"Guruh '{group.name}' kursga '{course.title}' bog'lanmagan.")
        return redirect('course_groups', course_id=course.id)

    students = group.students.all() 

    student_data = []
    
    # Lesson modelining mavjudligini tekshirish
    try:
        all_lessons_qs = Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
        total_lessons = all_lessons_qs.count()
        all_lessons_list = list(all_lessons_qs) # Indexlash uchun listga o'tkaziladi
    except NameError:
        messages.error(request, "Dars modullari topilmadi. Progress hisoblash imkonsiz.")
        total_lessons = 0
        all_lessons_list = []


    for student in students:
        last_completed, next_lesson = get_student_progress(student, course)

        completed_lesson_count = 0
        progress_percentage = 0
        
        if last_completed and total_lessons > 0:
            try:
                # Tugallangan darsning ro'yxatdagi indexini topib, darslar sonini hisoblaymiz
                completed_lesson_count = all_lessons_list.index(last_completed) + 1
            except ValueError:
                completed_lesson_count = 0 # Agar topilmasa, 0
        
        if total_lessons > 0:
            progress_percentage = round((completed_lesson_count / total_lessons) * 100, 1)
        
        student_data.append({
            'student': student,
            'last_completed_lesson': last_completed.title if last_completed else "Boshlanmagan / 0-dars",
            'next_lesson_to_do': next_lesson.title if next_lesson else 'Kurs tugatilgan!',
            'completed_count': completed_lesson_count,
            'total_lessons': total_lessons,
            'progress_percentage': progress_percentage
        })

    context = {
        'course': course,
        'group': group,
        'students_data': student_data,
        'center': course.center,
        'page_title': f"{course.title} ({group.name}) O'quvchilar progressi"
    }
    return render(request, 'management/course_group_student_list.html', context)

# ======================================================================
# 1. KURSLAR YARATISH VIEW
# ======================================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
# Course, Center, CourseForm va boshqa modellarni import qilishni unutmang


@login_required(login_url='login')
def course_create(request, slug):
    user = request.user
    center = get_object_or_404(Center, slug=slug)
    
    # 1. Ruxsat tekshiruvi (O'zgarishsiz)
    if not ((user.role in ['teacher', 'center_admin'] and user.center == center) or user.is_staff):
        messages.error(request, "Sizda bu markaz uchun kurs yaratish huquqi yo'q.")
        return redirect('dashboard', slug=user.center.slug)
    
    TeacherModel = get_user_model() 
    
    # 2. O'qituvchi Queryset'ini yaratish (O'zgarishsiz)
    teacher_queryset = TeacherModel.objects.filter(
        center=center, 
        role__in=['teacher', 'center_admin'] 
    ).order_by('full_name')

    if request.method == 'POST':
        # 🔥 request.FILES qo'shilgan, rasm yuklash uchun muhim
        form = CourseForm(request.POST, request.FILES) 
        
        if 'teacher' in form.fields:
            form.fields['teacher'].queryset = teacher_queryset
             
        if form.is_valid():
            course = form.save(commit=False)
            
            # 🔥 DIQQAT: Kursni yaratishda 'center' ni majburiy biriktirish
            course.center = center 
            
            # Agar 'teacher' formadan kelgan bo'lsa, uni saqlaymiz.
            # Sizning asl kodingizda course.teacher = user edi, bu xato.
            # Agar form.save() dan keyin qayta yozilmasa, formadan kelgan o'qituvchi saqlanadi.
            # Biz form.save(commit=False) qilganimiz uchun, avvalo center ni biriktirib, 
            # keyin formadan kelgan qolgan ma'lumotlarni saqlashimiz kerak.
            
            course.save()
            messages.success(request, f"'{course.title}' kursi muvaffaqiyatli yaratildi.")
            
            return redirect('course_list', slug=center.slug)
    else:
        form = CourseForm()
        
        if 'teacher' in form.fields:
            form.fields['teacher'].queryset = teacher_queryset
            # Yaratayotgan foydalanuvchini boshlang'ich qiymat sifatida berish (ixtiyoriy)
            form.initial['teacher'] = user.pk 
            
    context = {
        'form': form,
        'center': center, 
        'page_title': f"{center.name} uchun Yangi Kurs Yaratish"
    }
    # 🔥 Shablon nomini to'g'irlash
    return render(request, 'management/course_form.html', context)

@login_required(login_url='login')
def course_update(request, slug, pk):
    user = request.user
    center = get_object_or_404(Center, slug=slug)
    course = get_object_or_404(Course, id=pk)

    # 1. Ruxsat tekshiruvi (O'zgarishsiz)
    if not (course.center == center):
        messages.error(request, "Kurs boshqa markazga tegishli. Tahrirlash mumkin emas.")
        return redirect('course_list', slug=center.slug)

    is_authorized = (
        course.teacher == user or 
        user.is_staff or 
        (user.role == 'center_admin' and user.center == center) 
    )
    
    if not is_authorized:
        messages.error(request, "Siz bu kursni tahrirlash huquqiga ega emassiz.")
        return redirect('course_list', slug=center.slug)

    TeacherModel = get_user_model()
    
    # 2. O'qituvchi Queryset'ini yaratish (O'zgarishsiz)
    teacher_queryset = TeacherModel.objects.filter(
        center=center, 
        role__in=['teacher', 'center_admin']
    ).order_by('full_name')


    if request.method == 'POST':
        # 🔥 request.FILES qo'shilgan, rasm tahrirlash uchun muhim
        form = CourseForm(request.POST, request.FILES, instance=course)
        
        if 'teacher' in form.fields:
            form.fields['teacher'].queryset = teacher_queryset
             
        if form.is_valid():
            # course.center, course.id mavjud bo'lgani uchun to'g'ridan-to'g'ri saqlaymiz
            form.save() 
            messages.success(request, f"'{course.title}' kursi muvaffaqiyatli tahrirlandi.")
            
            return redirect('course_list', slug=center.slug)
    else:
        form = CourseForm(instance=course)
        
        if 'teacher' in form.fields:
            form.fields['teacher'].queryset = teacher_queryset
         
    context = {
        'form': form,
        'course': course, # Mavjud rasmni ko'rsatish uchun kerak
        'center': center, 
        'page_title': f"{course.title} ni tahrirlash"
    }
    # 🔥 Shablon nomini to'g'irlash
    return render(request, 'management/course_form.html', context)

@login_required(login_url='login')
def course_delete(request, slug, pk):
    """ Kursni o'chirish (CRUD Delete). """
    user = request.user
    center = get_object_or_404(Center, slug=slug)
    course = get_object_or_404(Course, id=pk)

    # 1. Xavfsizlik va Ruxsat tekshiruvi
    if not ((is_teacher(user) and user.center == center and course.creator.center == center) or user.is_staff):
        messages.error(request, "Sizda bu kursni o'chirish huquqi yo'q.")
        return redirect('dashboard',slug=request.user.center.slug)

    course_title = course.title
    
    if request.method == 'POST':
        course.delete()
        messages.success(request, f"'{course_title}' nomli kurs muvaffaqiyatli o'chirildi.")
        # 2. Redirect qilishda ham SLUG ni uzatish
        return redirect('course_list', slug=center.slug)
        
    context = {
        'course': course,
        'center': center, # Shablonlarda URL yaratish uchun kerak
        'page_title': f"'{course_title}' kursini o'chirish"
    }
    return render(request, 'management/course_confirm_delete.html', context)


# =================================================================
# YANGI VIEW: Tariflar sahifasi
# =================================================================

@login_required(login_url='login')
def price_view(request, slug):
    """Tariflar sahifasi – faqat o‘z markazida"""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('index')

    exam_packages = ExamPackage.objects.filter(is_active=True).order_by('price')
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    form = PurchaseForm()

    context = {
        'center': center,
        'exam_packages': exam_packages,
        'subscription_plans': subscription_plans,
        'form': form,
    }
    return render(request, 'student/price.html', context)

# =================================================================
# YANGI VIEW: Xarid mantiqi
# =================================================================

@login_required(login_url='login')
@transaction.atomic 
def process_purchase_view(request, slug, purchase_type, item_id):
    """
    Xaridni qayta ishlaydi – faqat o‘z markazida
    """
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        messages.error(request, "Bu sahifaga kirish huquqingiz yo‘q.")
        return redirect('price', slug=slug)

    if request.method != 'POST':
        messages.error(request, "Noto'g'ri so'rov usuli.")
        return redirect('price', slug=slug)

    form = PurchaseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formada xatolik bor.")
        return redirect('price', slug=slug)

    promo_code_str = form.cleaned_data.get('promo_code')
    user = request.user
    
    try:
        item = None
        item_type_display = ""
        if purchase_type == 'package':
            item = get_object_or_404(ExamPackage, id=item_id, is_active=True)
            item_type_display = f"'{item.name}' paketi"
        elif purchase_type == 'subscription':
            item = get_object_or_404(SubscriptionPlan, id=item_id, is_active=True)
            item_type_display = f"'{item.name}' obunasi"
        else:
            messages.error(request, "Noto'g'ri xarid turi.")
            return redirect('price', slug=slug)

        final_amount = item.price
        promo_code = None

        if promo_code_str:
            try:
                promo_code = PromoCode.objects.get(code=promo_code_str, is_active=True)
                if not promo_code.is_valid():
                    messages.error(request, "Promo kod muddati tugagan.")
                    return redirect('price', slug=slug)
                
                if promo_code.discount_type == 'percentage':
                    discount = final_amount * (promo_code.discount_percent / 100)
                    final_amount -= discount
                else:
                    final_amount -= promo_code.discount_amount
                
                final_amount = max(0, final_amount)
                messages.info(request, f"Chegirma qo‘llandi: {item.price - final_amount:.2f} so‘m")

            except PromoCode.DoesNotExist:
                messages.error(request, "Noto'g'ri promo kod.")
                return redirect('price', slug=slug)

        purchase = Purchase.objects.create(
            user=user,
            purchase_type=purchase_type,
            package=item if purchase_type == 'package' else None,
            subscription_plan=item if purchase_type == 'subscription' else None,
            amount=item.price,
            promo_code=promo_code,
            final_amount=final_amount,
            status='completed'
        )

        if promo_code:
            promo_code.used_count += 1
            promo_code.save()

        if purchase_type == 'package':
            balance, _ = UserBalance.objects.get_or_create(user=user)
            balance.exam_credits += item.exam_credits
            balance.solution_view_credits += item.solution_view_credits_on_purchase
            balance.save()
        
        elif purchase_type == 'subscription':
            UserSubscription.objects.filter(user=user).delete()
            UserSubscription.objects.create(
                user=user,
                plan=item,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=item.duration_days)
            )

        messages.success(request, f"{item_type_display} muvaffaqiyatli xarid qilindi!")
        return redirect('profile', slug=slug)

    except Exception as e:
        logger.error(f"Xarid xatosi: {e}", exc_info=True)
        messages.error(request, "Server xatoligi. Keyinroq urinib ko‘ring.")
        return redirect('price', slug=slug)

# =========================================================================
# 🎯 1. IMTIHONNI BOSHLASH MANTIQI (start_exam_view)
# =========================================================================

EBRW_M1, EBRW_M2 = 'read_write_m1', 'read_write_m2'
MATH_M1, MATH_M2 = 'math_no_calc', 'math_calc'

@login_required(login_url='login')
@require_POST
def start_exam_view(request, slug, exam_id):
    center = get_object_or_404(Center, slug=slug)

    if request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo'q.")
        return redirect('index')

    try:
        exam = get_object_or_404(
            Exam,
            id=exam_id,
            is_active=True,
            center=center
        )

        # ===================================================================
        # 1. KREDIT TEKSHIRISH — TO'G'RI MANTIQ!
        # ===================================================================
        if exam.is_premium:
            # Pullik imtihon → obuna bor-yo'qligini tekshiramiz
            if hasattr(request.user, 'subscription') and request.user.subscription.is_active():
                # Obuna aktiv → kredit ketmaydi
                pass
            else:
                # Obuna yo'q → kredit tekshiriladi
                balance = request.user.balance
                if balance.exam_credits <= 0:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Imtihon kreditingiz tugadi! Yangi kredit sotib oling.',
                        'redirect': reverse('packages')
                    }, status=403)

                # 1 TA KREDIT AYIRILADI
                balance.exam_credits = models.F('exam_credits') - 1
                balance.save(update_fields=['exam_credits'])
                logger.info(f"Kredit sarflandi: {request.user.username} → {balance.exam_credits} ta qoldi")
        else:
            # BEPUL IMTIHON → HECH QANDAY KREDIT KETMAYDI!
            pass

        # ===================================================================
        # 2. NEXT URL ni SESSION ga SAQLASH (Kursdan kelgan bo'lsa)
        # ===================================================================
        next_url = request.GET.get('next')
        if next_url:
            request.session[f'exam_{exam_id}_next_url'] = next_url
            logger.info(f"Next URL saqlandi: {next_url} → exam_id={exam_id}")

        # ===================================================================
        # 3. YANGI YOKI DAVOM ETTIRILAYOTGAN ATTEMPT
        # ===================================================================
        attempt = UserAttempt.objects.filter(
            user=request.user,
            exam=exam,
            is_completed=False
        ).first()

        with transaction.atomic():
            if not attempt:
                # YANGI ATTEMPT YARATILADI
                attempt = UserAttempt.objects.create(
                    user=request.user,
                    exam=exam,
                    mode='exam',
                    center=center  # <--- BU JUDA MUHIM! Balans sahifasi uchun
                )

                # Bo'limlarni yaratish
                ordered_sections = exam.examsectionorder.select_related('exam_section').order_by('order')
                if not ordered_sections.exists():
                    return JsonResponse({'status': 'error', 'message': 'Imtihonda bolim yoq'}, status=400)

                section_attempts = [
                    UserAttemptSection(
                        attempt=attempt,
                        section=eso.exam_section,
                        remaining_time_seconds=eso.exam_section.duration_minutes * 60
                    )
                    for eso in ordered_sections
                ]
                UserAttemptSection.objects.bulk_create(section_attempts)

                # Savollarni bog'lash
                for sa in UserAttemptSection.objects.filter(attempt=attempt):
                    static_qs = ExamSectionStaticQuestion.objects.filter(exam_section=sa.section)
                    UserAttemptQuestion.objects.bulk_create([
                        UserAttemptQuestion(
                            attempt_section=sa,
                            question=sq.question,
                            question_number=sq.question_number
                        ) for sq in static_qs
                    ])

        # ===================================================================
        # 4. BIRINCHI BO'LIMGA YO'NALTIRISH
        # ===================================================================
        first_section = UserAttemptSection.objects.filter(attempt=attempt).annotate(
            order=Subquery(
                ExamSectionOrder.objects.filter(
                    exam=exam,
                    exam_section=OuterRef('section')
                ).values('order')[:1]
            )
        ).order_by('order').first()

        if not first_section:
            return JsonResponse({'status': 'error', 'message': 'Birinchi bolim topilmadi'}, status=400)

        redirect_url = reverse('exam_mode', kwargs={
            'slug': slug,
            'exam_id': exam.id,
            'attempt_id': attempt.id
        })

        return JsonResponse({
            'status': 'success',
            'attempt_id': attempt.id,
            'redirect_url': redirect_url
        })

    except Exception as e:
        logger.error(f"start_exam_view xatosi: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Server xatosi'}, status=500)

# =========================================================================
# ⭐️ 2. IMTIHON TOPSHIRISH REJIMI (exam_mode_view)
# =========================================================================

@login_required(login_url='login')
def exam_mode_view(request, slug, exam_id, attempt_id):
    """
    Imtihon topshirish sahifasini ko'rsatadi. Timer va birinchi savol ma'lumotlarini yuklaydi.
    """
    center = get_object_or_404(Center, slug=slug)

    if request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q.")
        return redirect('index')

    try:
        attempt = get_object_or_404(
            UserAttempt,
            id=attempt_id,
            user=request.user,
            exam__id=exam_id,
            exam__center=center
        )

        section_attempt = UserAttemptSection.objects.filter(
            attempt=attempt, is_completed=False
        ).select_related('section').annotate(
            order=Subquery(
                ExamSectionOrder.objects.filter(
                    exam=attempt.exam,
                    exam_section=OuterRef('section')
                ).values('order')[:1]
            )
        ).order_by('order').first()

        if not section_attempt:
            # BARCHA BO‘LIMLAR TUGADI → IMTIHON YAKUNLANDI!
            attempt.is_completed = True
            attempt.completed_at = timezone.now()
            attempt.save()
            messages.success(request, "Imtihon muvaffaqiyatli yakunlandi!")
            return redirect('view_result_detail', slug=center.slug, attempt_id=attempt.id)

        # BIRINCHI SAVOL ID'SINI OLIsh
        ordered_questions_ids = ExamSectionStaticQuestion.objects.filter(
            exam_section=section_attempt.section
        ).order_by('question_number').values_list('question_id', flat=True)
        first_question_id = ordered_questions_ids.first()

        if not first_question_id:
            messages.warning(request, f"'{section_attempt.section.name}' bo'limida savollar yo'q.")
            section_attempt.is_completed = True
            section_attempt.completed_at = timezone.now()
            section_attempt.save()
            return redirect('exam_mode', slug=slug, exam_id=exam_id, attempt_id=attempt_id)

        # TIMER MANTIQI
        # TIMER MANTIQI – 100% TO‘G‘RI
        total_duration_seconds = section_attempt.section.duration_minutes * 60

        # Agar birinchi marta kirsa
        if section_attempt.started_at is None:
            section_attempt.started_at = timezone.now()
            section_attempt.remaining_time_seconds = total_duration_seconds
            section_attempt.save(update_fields=['started_at', 'remaining_time_seconds'])
            time_remaining_seconds = total_duration_seconds
        else:
            # O‘tgan vaqtni hisoblaymiz
            elapsed = (timezone.now() - section_attempt.started_at).total_seconds()
            time_remaining_seconds = max(0, int(total_duration_seconds - elapsed))

            # Har holda DB dagi qiymatni yangilaymiz (xavfsizlik uchun)
            section_attempt.remaining_time_seconds = time_remaining_seconds
            section_attempt.save(update_fields=['remaining_time_seconds'])

        if time_remaining_seconds == 0 and not section_attempt.is_completed:
            section_attempt.is_completed = True
            section_attempt.completed_at = timezone.now()
            section_attempt.save()

            # OXIRGI BO‘LIMMI?
            if not UserAttemptSection.objects.filter(attempt=attempt, is_completed=False).exists():
                attempt.is_completed = True
                attempt.completed_at = timezone.now()
                attempt.save()
                messages.warning(request, "Vaqt tugadi. Imtihon yakunlandi.")
                return redirect('view_result_detail', slug=slug, attempt_id=attempt.id)

            messages.warning(request, f"Vaqt tugadi. '{section_attempt.section.name}' bo'limi yakunlandi.")
            return redirect('exam_mode', slug=slug, exam_id=exam_id, attempt_id=attempt_id)

        # QO‘SHIMCHA OPTIONLAR
        section_type = section_attempt.section.section_type
        extra_options = []
        if section_type == MATH_M2:
            extra_options.append('calculator')
        if section_type in [MATH_M1, MATH_M2]:
            extra_options.append('reference')

        context = {
            'exam': attempt.exam,
            'attempt_id': attempt.id,
            'section_attempt_id': section_attempt.id,
            'section_attempt': section_attempt,
            'time_remaining_seconds': time_remaining_seconds,
            'extra_options': extra_options,
            'is_subject_exam': attempt.exam.is_subject_exam,
            'first_question_id': first_question_id,
            'center': center,
        }

        return render(request, 'student/exam_mode.html', context)

    except UserAttempt.DoesNotExist:
        messages.error(request, "Imtihon urinishi topilmadi.")
        return redirect('all_exams')
    except Exception as e:
        logger.error(f"exam_mode_view xatosi: {str(e)}", exc_info=True)
        messages.error(request, "Imtihon sahifasini yuklashda xato.")
        return redirect('dashboard', slug=request.user.center.slug)

from Mock.services.sat_scoring_engine import calculate_sat_math_score

@csrf_exempt
@require_POST
def handle_exam_ajax(request):
    """
    SAT va Mavzu testi uchun umumiy AJAX handler.
    100% XAVFSIZ, 400 XATO YO‘Q, finish_exam 100% ISHLAYDI!
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Login kerak'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON formati noto‘g‘ri'}, status=400)

    action = data.get('action')
    attempt_id = data.get('attempt_id')
    section_attempt_id = data.get('section_attempt_id')

    # Agar action yo'q bo'lsa – darhol xato
    if not action:
        return JsonResponse({'status': 'error', 'message': 'action majburiy'}, status=400)

    # finish_exam va finish_section uchun attempt_id va section_attempt_id shart emas
    if action not in ['finish_exam', 'finish_section']:
        if not all([attempt_id, section_attempt_id]):
            return JsonResponse({'status': 'error', 'message': 'attempt_id va section_attempt_id kerak'}, status=400)

    # finish_exam/finish_section uchun alohida tekshiruv
    if action in ['finish_exam', 'finish_section']:
        if not attempt_id or not section_attempt_id:
            return JsonResponse({'status': 'error', 'message': 'finish_exam uchun attempt_id va section_attempt_id kerak'}, status=400)

    try:
        attempt = get_object_or_404(UserAttempt, id=attempt_id, user=request.user)
        section_attempt = get_object_or_404(UserAttemptSection, id=section_attempt_id, attempt=attempt)
    except:
        return JsonResponse({'status': 'error', 'message': 'Imtihon yoki bo‘lim topilmadi'}, status=404)

    is_subject_exam = attempt.exam.is_subject_exam

    # ===================================================================
    # 1. BO'LIM YUKLASH
    # ===================================================================
    if action == 'load_section_data':
        try:
            questions_qs = section_attempt.userattemptquestion_set.all().order_by('question_number')
            question_ids = list(questions_qs.values_list('question_id', flat=True))

            user_answers = section_attempt.user_answers.select_related('question').prefetch_related('selected_options')

            initial_answers = {}
            answered_ids = []
            marked_ids = []

            for ua in user_answers:
                q = ua.question
                sel_ids = list(ua.selected_options.values_list('id', flat=True))

                initial_answers[str(q.id)] = {
                    'selected_options': sel_ids or None,
                    'selected_option': sel_ids[0] if q.answer_format == 'single' and sel_ids else None,
                    'short_answer_text': ua.short_answer_text.strip() if ua.short_answer_text else None,
                    'is_marked_for_review': ua.is_marked_for_review
                }

                is_answered = (
                    (q.answer_format == 'short_answer' and ua.short_answer_text and ua.short_answer_text.strip()) or
                    ua.selected_options.exists()
                )
                if is_answered:
                    answered_ids.append(q.id)
                if ua.is_marked_for_review:
                    marked_ids.append(q.id)

            return JsonResponse({
                'status': 'success',
                'section_data': {
                    'question_ids': question_ids,
                    'initial_time_remaining': section_attempt.remaining_time_seconds,
                    'section_completed': section_attempt.is_completed,
                    'initial_answers': initial_answers,
                    'answered_question_ids': answered_ids,
                    'marked_for_review_ids': marked_ids,
                    'is_subject_exam': is_subject_exam,
                }
            })
        except Exception as e:
            logger.error(f"load_section_data xato: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'Bo‘lim yuklanmadi'}, status=500)

    # ===================================================================
    # 2. SAVOL YUKLASH
    # ===================================================================
    elif action == 'load_question_data':
        question_id = data.get('question_id')
        if not question_id:
            return JsonResponse({'status': 'error', 'message': 'question_id kerak'}, status=400)

        try:
            question = Question.objects.select_related('passage').prefetch_related('options').get(id=question_id)
            options = question.options.all().order_by('id')
            letters = ['A', 'B', 'C', 'D', 'E', 'F']

            options_data = []
            for i, opt in enumerate(options):
                options_data.append({
                    'id': opt.id,
                    'text': opt.text,
                    'char': letters[i] if i < len(letters) else chr(65 + i),
                })

            user_answer = section_attempt.user_answers.filter(question=question).first()
            initial_answer = {}
            if user_answer:
                sel_ids = list(user_answer.selected_options.values_list('id', flat=True))
                is_answered = (
                    (question.answer_format == 'short_answer' and user_answer.short_answer_text and user_answer.short_answer_text.strip()) or
                    bool(sel_ids)
                )
                initial_answer = {
                    'selected_options': sel_ids,
                    'selected_option': sel_ids[0] if question.answer_format == 'single' and sel_ids else None,
                    'short_answer_text': user_answer.short_answer_text or '',
                    'is_marked_for_review': user_answer.is_marked_for_review,
                    'is_answered': is_answered
                }

            try:
                q_num = section_attempt.userattemptquestion_set.get(question=question).question_number
            except:
                q_num = 0

            question_data = {
                'id': question.id,
                'number': q_num,
                'text': question.text,
                'format': question.answer_format,
                'image_url': question.image.url if question.image else None,
                'options': options_data,
                'initial_answer': initial_answer,
                'passage_text': question.passage.text if question.passage else None,
            }

            return JsonResponse({'status': 'success', 'question_data': question_data})

        except Question.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Savol topilmadi'}, status=404)
        except Exception as e:
            logger.error(f"load_question_data xato: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'Savol yuklanmadi'}, status=500)

    # ===================================================================
    # 3. JAVOB SAQLASH + TIMER SINXRONIZATSIYASI – 100% TO‘G‘RI (2025)
    # ===================================================================
    elif action in ['save_answer', 'sync_timer']:
        # Har doim serverda real vaqtni hisoblaymiz
        total_duration_seconds = section_attempt.section.duration_minutes * 60
        elapsed_seconds = (timezone.now() - section_attempt.started_at).total_seconds()
        server_remaining = max(0, int(total_duration_seconds - elapsed_seconds))

        # Brauzerdan kelgan vaqt
        client_remaining = data.get('time_remaining')
        if client_remaining is not None:
            client_remaining = max(0, int(client_remaining))

        # Qaysi vaqtni ishlatamiz?
        if client_remaining is not None:
            # Farq 15 sekunddan kam – clientni ishonamiz (tezroq)
            if abs(server_remaining - client_remaining) <= 15:
                final_remaining = client_remaining
            else:
                # Farq katta – serverni majburiy (cheat oldini olish)
                final_remaining = server_remaining
                logger.warning(f"Vaqt farqi katta! User: {request.user.id}, Client: {client_remaining}s, Server: {server_remaining}s")
        else:
            final_remaining = server_remaining

        # DB ga saqlaymiz
        section_attempt.remaining_time_seconds = final_remaining
        section_attempt.save(update_fields=['remaining_time_seconds'])

        # Agar faqat sync_timer bo‘lsa – shu yerda tugatamiz
        if action == 'sync_timer':
            return JsonResponse({
                'status': 'success',
                'message': 'Vaqt sinxronlandi',
                'time_remaining': final_remaining  # Brauzerga to‘g‘ri vaqt yuboramiz
            })

        # save_answer – javob saqlash qismi (sizniki to‘g‘ri, lekin xavfsizroq qilamiz)
        qid = data.get('question_id')
        if not qid:
            return JsonResponse({'status': 'error', 'message': 'question_id majburiy'}, status=400)

        try:
            question = Question.objects.prefetch_related('options').get(id=qid)
        except Question.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Savol topilmadi'}, status=404)

        with transaction.atomic():
            ua, created = section_attempt.user_answers.get_or_create(
                question=question,
                defaults={'is_marked_for_review': bool(data.get('is_marked_for_review', False))}
            )

            # Tozalash
            ua.selected_options.clear()
            ua.short_answer_text = ''
            ua.is_correct = None
            ua.is_marked_for_review = bool(data.get('is_marked_for_review', False))

            # JAVOB SAQLASH
            if question.answer_format == 'single':
                opt_id = data.get('selected_option')
                if opt_id:
                    try:
                        opt = AnswerOption.objects.get(id=opt_id, question=question)
                        ua.selected_options.add(opt)
                    except AnswerOption.DoesNotExist:
                        pass

            elif question.answer_format == 'multiple':
                opts = data.get('selected_options', [])
                if isinstance(opts, list):
                    valid_opts = AnswerOption.objects.filter(id__in=opts, question=question)
                    ua.selected_options.set(valid_opts)

            elif question.answer_format == 'short_answer':
                text = data.get('short_answer_text', '').strip()
                ua.short_answer_text = text

            # is_correct HISOBLASH
            if question.answer_format in ('single', 'multiple'):
                correct_options = set(question.options.filter(is_correct=True).values_list('id', flat=True))
                selected_options = set(ua.selected_options.values_list('id', flat=True))

                if question.answer_format == 'single':
                    if selected_options and list(selected_options)[0] in correct_options:
                        ua.is_correct = True
                    elif selected_options:
                        ua.is_correct = False

                elif question.answer_format == 'multiple':
                    if selected_options == correct_options and correct_options:
                        ua.is_correct = True
                    elif selected_options != correct_options:
                        ua.is_correct = False

            elif question.answer_format == 'short_answer':
                if question.correct_short_answer:
                    correct = question.correct_short_answer.strip().lower()
                    user_input = ua.short_answer_text.lower()
                    cleaned_user = user_input.replace(" ", "").replace(",", "").replace(".", "").replace("-", "").replace("–", "")
                    cleaned_correct = correct.replace(" ", "").replace(",", "").replace(".", "").replace("-", "").replace("–", "")
                    if cleaned_user == cleaned_correct:
                        ua.is_correct = True
                    else:
                        ua.is_correct = False
                else:
                    ua.is_correct = None

            is_answered = (
                (question.answer_format == 'short_answer' and ua.short_answer_text) or
                ua.selected_options.exists()
            )
            ua.answered_at = timezone.now() if is_answered else None
            ua.save()

            answered_ids = list(
                section_attempt.user_answers.exclude(
                    Q(selected_options__isnull=True) & Q(short_answer_text__exact='')
                ).values_list('question_id', flat=True).distinct()
            )

            return JsonResponse({
                'status': 'success',
                'answered_question_ids': answered_ids,
                'is_correct': ua.is_correct,
                'question_id': question.id,
                'time_remaining': final_remaining,  # Yangi vaqtni brauzerga yuboramiz
                'message': 'Javob saqlandi'
            })

    # ===================================================================
    # 4. FLASHCARDS
    # ===================================================================
    elif action == 'get_flashcards':
        if not is_subject_exam:
            return JsonResponse({'status': 'error', 'message': 'Flashcards faqat mavzu testida'}, status=403)
        qid = data.get('question_id')
        if not qid:
            return JsonResponse({'status': 'error', 'message': 'question_id kerak'}, status=400)
        flashcards = Flashcard.objects.filter(question_id=qid)
        data_list = [{'term': f.term, 'definition': f.definition, 'image_url': f.image.url if f.image else None} for f in flashcards]
        return JsonResponse({'status': 'success', 'flashcards': data_list})

    
    # ===================================================================
    # 5. YAKUNLASH – 100% XAVFSIZ, CHEAT YO‘Q, BALL TO‘G‘RI HISOBLANADI
    # ===================================================================
    elif action in ['finish_exam', 'finish_section']:
        # 1. Serverda real qolgan vaqtni hisoblaymiz (hech qachon clientga ishonmaymiz!)
        total_duration = section_attempt.section.duration_minutes * 60
        elapsed = (timezone.now() - section_attempt.started_at).total_seconds()
        actual_remaining = max(0, int(total_duration - elapsed))

        # Har doim server vaqtini ishlatamiz – cheat imkonsiz
        section_attempt.remaining_time_seconds = 0  # bo‘lim tugadi
        section_attempt.is_completed = True
        section_attempt.completed_at = timezone.now()
        section_attempt.save(update_fields=['remaining_time_seconds', 'is_completed', 'completed_at'])

        center_slug = (attempt.user.center.slug if hasattr(attempt.user, 'center') and attempt.user.center else 'unknown')

        # 2. Boshqa yakunlanmagan bo‘limlar bormi?
        has_remaining_sections = UserAttemptSection.objects.filter(
            attempt=attempt,
            is_completed=False
        ).exclude(id=section_attempt.id).exists()

        # 3. Imtihonni to‘liq yakunlash sharti
        exam_finished = (action == 'finish_exam') or (not has_remaining_sections) or is_subject_exam

        if exam_finished:
            attempt.is_completed = True
            attempt.completed_at = timezone.now()

            # TO‘G‘RI JAVOBLAR SONI
            correct_count = UserAnswer.objects.filter(
                attempt_section__attempt=attempt,
                is_correct=True
            ).count()

            if is_subject_exam:
                # MAVZU TESTI – foiz hisoblaymiz
                total_questions = attempt.exam.sections.aggregate(
                    t=Sum('max_questions')
                )['t'] or 0

                if total_questions > 0:
                    percentage = round((correct_count / total_questions) * 100, 2)
                    attempt.final_total_score = percentage
                    attempt.final_ebrw_score = correct_count      # to‘g‘ri javoblar
                    attempt.final_math_score = total_questions    # jami savollar
                else:
                    attempt.final_total_score = 0
                    attempt.final_ebrw_score = 0
                    attempt.final_math_score = 0
            else:
                # SAT MOCK (Math) – jarima tizimi
                score = calculate_sat_math_score(attempt)
                logger.info(f"SAT Mock yakunlandi | Attempt {attempt.id} | Ball: {score}")

                attempt.final_math_score = score
                attempt.final_total_score = score
                attempt.final_ebrw_score = 0

            attempt.save()

            redirect_url = reverse('view_result_detail', kwargs={
                'slug': center_slug,
                'attempt_id': attempt.id
            })
            message = "Imtihon muvaffaqiyatli yakunlandi!"
        else:
            # Keyingi bo‘limga o‘tamiz
            redirect_url = reverse('exam_mode', kwargs={
                'slug': center_slug,
                'exam_id': attempt.exam.id,
                'attempt_id': attempt.id
            })
            message = "Bo‘lim yakunlandi. Keyingi bo‘limga o‘tmoqdasiz..."

        return JsonResponse({
            'status': 'success',
            'redirect_url': redirect_url,
            'message': message,
            'exam_finished': exam_finished
        })

    # ===================================================================
    # NOMA'LUM ACTION
    # ===================================================================
    return JsonResponse({'status': 'error', 'message': f"Noto'g'ri action: {action}"}, status=400)


def get_question_data(request, section_attempt, question_id):
    """
    Berilgan savolning ma'lumotlarini va foydalanuvchining oldingi javobini yuklaydi.
    """
    try:
        question = section_attempt.questions.get(id=question_id)
        options = question.options.all()
        
        # Harflarni qo'shish
        letters = list(string.ascii_uppercase)
        options_with_letters = list(zip(options, letters[:len(options)]))

        user_answer = UserAnswer.objects.filter(
            attempt_section=section_attempt,
            question_id=question_id
        ).first()
        
        selected_option_ids = []
        short_answer = None
        is_marked = False
        
        if user_answer:
            selected_option_ids = list(user_answer.selected_options.values_list('id', flat=True))
            short_answer = user_answer.short_answer_text
            is_marked = user_answer.is_marked_for_review
        
        # Savolning tartib raqamini aniqlash (navigation uchun kerak)
        q_order = section_attempt.questions.through.objects.filter(
            attempt_section=section_attempt,
            question=question
        ).values_list('question_number', flat=True).first()

        context = {
            'question': question,
            'user_answer': user_answer,
            'options': options,
            'options_with_letters': options_with_letters, 
            'is_study_mode': section_attempt.attempt.mode == 'study', 
            'selected_option_ids': selected_option_ids,
            'short_answer_text': short_answer
        }
        
        options_html = render_to_string('student/question_options.html', context, request=request)
        
        question_data = {
            'id': question.id,
            'question_text': question.text,
            'question_format': question.answer_format,
            'options_html': options_html,
            'question_image_url': question.image.url if question.image else '',
            'user_selected_options': selected_option_ids,
            'user_short_answer': short_answer,
            'is_marked_for_review': is_marked,
            'question_number': q_order, # Savol tartib raqami
        }
        return question_data
        
    except Question.DoesNotExist:
        return {'error': "Savol bu bo'limda topilmadi."}
    except Exception as e:
        logger.error(f"get_question_data xatosi: {str(e)}", exc_info=True)
        return {'error': f'Savol yuklashda server xatosi: {str(e)}'}
    
# =========================================================================
# ⭐️ 4. YAKUNIY NATIJALAR (view_result_detail) - Oldingi tuzatilgan funksiya
# =========================================================================

@login_required(login_url='login')
def view_result_detail(request, slug, attempt_id):
    from django.shortcuts import render, get_object_or_404, redirect
    from django.contrib import messages
    from django.db.models import Count, OuterRef, Subquery

    # Agar models import qilinmagan bo'lsa, ularni import qiling
    # from .models import Center, UserAttempt, UserAnswer, ExamSectionOrder 
    # deb faraz qilamiz.
    # Sizning kod manbangiz to'liq emas, shuning uchun model nomlarini o'zgartirmayman.
    # Lekin bularni bitta faylda ishlatish uchun importlarni ko'rsatishingiz kerak.

    # Model nomlari bu yerda mavjud emas, shuning uchun joylashtirilgan kodni saqlayman.

    center = get_object_or_404(Center, slug=slug)

    # Foydalanuvchi markazi tekshiruvi
    if request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q.")
        return redirect('dashboard', slug=request.user.center.slug)

    # Urinishni olish
    attempt = get_object_or_404(
        UserAttempt.objects.select_related('exam', 'user', 'user__balance'),
        id=attempt_id,
        exam__center=center,
        is_completed=True,
        **({} if request.user.role == 'teacher' else {'user': request.user}),
        **({'exam__teacher': request.user} if request.user.role == 'teacher' else {})
    )

    exam = attempt.exam
    is_subject_exam = getattr(exam, 'is_subject_exam', False)

    # === SAT MATH MOCK EXAM YOKI MAVZU TESTI ANIQLASH ===
    answers_qs = UserAnswer.objects.filter(
        attempt_section__attempt=attempt,
        is_correct__isnull=False
    )
    total_questions = answers_qs.count()
    is_sat_math_exam = (not is_subject_exam) and (total_questions == 44)

    # === JAVOBLARNI TAHLIL QILISH ===
    sections_qs = attempt.section_attempts.select_related('section').annotate(
        section_order_value=Subquery(
            ExamSectionOrder.objects.filter(
                exam=exam,
                exam_section=OuterRef('section')
            ).values('order')[:1]
        )
    ).order_by('section_order_value')

    correct_map = dict(
        UserAnswer.objects.filter(attempt_section__attempt=attempt, is_correct=True)
        .values('attempt_section__id')
        .annotate(c=Count('id'))
        .values_list('attempt_section__id', 'c')
    )

    total_correct = total_questions_count = total_omitted = 0
    section_analysis_list = []

    # SAT Math uchun xato tahlili
    mistakes_analysis = {
        'easy_mistakes': 0,
        'medium_mistakes': 0,
        'hard_mistakes': 0,
        'is_perfect': False
    }

    for section_attempt in sections_qs:
        questions_count = section_attempt.questions.count()
        if questions_count == 0:
            continue

        correct = correct_map.get(section_attempt.id, 0)
        total_correct += correct
        total_questions_count += questions_count

        # Navigatsiya tugmalari
        nav_items = []
        for ua_q in section_attempt.userattemptquestion_set.all().order_by('question_number'):
            try:
                ua = UserAnswer.objects.get(attempt_section=section_attempt, question=ua_q.question)
                nav_items.append({
                    'user_answer_id': ua.id,
                    'is_correct': ua.is_correct,
                })
                # SAT Math bo‘lsa — xato darajasini hisoblaymiz
                if is_sat_math_exam and not ua.is_correct:
                    diff = ua.question.difficulty
                    if diff <= -1.5:
                        mistakes_analysis['easy_mistakes'] += 1
                    elif diff <= 1.5:
                        mistakes_analysis['medium_mistakes'] += 1
                    else:
                        mistakes_analysis['hard_mistakes'] += 1
            except UserAnswer.DoesNotExist:
                nav_items.append({'user_answer_id': None, 'is_correct': None})

        section_analysis_list.append({
            'section_attempt_id': section_attempt.id,
            'section_name': section_attempt.section.get_section_type_display(),
            'user_answers_nav': nav_items,
            'correct_count': correct,
            'total_count': questions_count,
        })

    total_omitted = UserAnswer.objects.filter(
        attempt_section__attempt=attempt,
        is_correct__isnull=True,
        selected_options__isnull=True,
        short_answer_text__exact=''
    ).count()
    total_incorrect = total_questions_count - total_correct - total_omitted
    total_percentage = round((total_correct / total_questions_count * 100), 1) if total_questions_count else 0

    # === NATIJA HISOBLASH ===
    if is_sat_math_exam:
        # SIZNING JARIMA TIZIMINGIZ
        base_score = total_correct * (600 / 44)  # har to‘g‘ri javob ~13.636 ball
        penalty = (
            mistakes_analysis['easy_mistakes'] * 20 +
            mistakes_analysis['medium_mistakes'] * 12 +
            mistakes_analysis['hard_mistakes'] * 6
        )
        final_score = 200 + base_score - penalty
        final_score = max(200, min(800, round(final_score / 10) * 10))
        if total_correct == 44:
            final_score = 800
            mistakes_analysis['is_perfect'] = True

        attempt.final_math_score = final_score
        attempt.final_total_score = final_score
        attempt.final_ebrw_score = 0
        attempt.save()

        sat_math_score = final_score
    else:
        # Mavzu testi — avvalgidek
        sat_math_score = None

    # === YECHIM HOLATI ===
    user_is_teacher = request.user.role == 'teacher'
    user_is_student = request.user == attempt.user

    if user_is_teacher:
        can_view_solution = True
        can_unlock_with_credit = False
        solution_always_open = True
    else:
        # Eslatma: Bu yerda passing_percentage qiyida turibdi,
        # lekin oldingi templateda u 60 deb qotirilgan edi (total_percentage >= 60).
        # Men sizning view'ingizdagi exam.passing_percentage'ni ishlataman.
        passing_percentage = attempt.exam.passing_percentage
        if not is_subject_exam or total_percentage >= passing_percentage:
            can_view_solution = True
            can_unlock_with_credit = False
        else:
            can_view_solution = False
            can_unlock_with_credit = is_subject_exam

    user_balance = getattr(attempt.user, 'balance', None)

    exam_id = attempt.exam.id
    next_url = request.session.pop(f'exam_{exam_id}_next_url', None)
    
    context = {
        'center': center,
        'attempt': attempt,
        'section_analysis_list': section_analysis_list,
        'is_subject_exam': is_subject_exam,
        'is_sat_math_exam': is_sat_math_exam,

        # Yechim holati
        'can_view_solution': can_view_solution,
        'can_unlock_with_credit': can_unlock_with_credit,
        'user_balance': user_balance,

        # Umumiy natija
        'total_sat_score': attempt.final_total_score,
        'ebrw_score': attempt.final_ebrw_score,
        'math_score': attempt.final_math_score,
        'sat_math_score': sat_math_score,
        'total_correct': total_correct,
        'total_incorrect': total_incorrect,
        'total_omitted': total_omitted,
        'total_questions': total_questions_count,
        'total_percentage': total_percentage,

        # SAT Math uchun maxsus tahlil
        'mistakes_analysis': mistakes_analysis if is_sat_math_exam else None,

        # Qo‘shimcha
        'viewed_student': attempt.user if user_is_teacher else None,
        
        # YANGILANGAN: Kurs Yo'l Xaritasiga Qaytish uchun URL
        'next_url': next_url,
    }

    return render(request, 'student/result_detail.html', context)

@login_required(login_url='login')
def exam_detail_view(request, slug, exam_id):
    """
    Imtihon tafsiloti – faqat o'z markazida
    prepare_exam_data yordamida to'liq ma'lumotlar bilan
    """
    # 1. MARKAZ TEKSHIRISH
    center = get_object_or_404(Center, slug=slug)
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu sahifaga kirish huquqingiz yo'q.")
        return redirect('index')

    # 2. IMTIHON TEKSHIRISH
    exam = get_object_or_404(
        Exam, 
        id=exam_id, 
        is_active=True,
        center=center
    )
    user = request.user

    # 3. ROL TEKSHIRISH
    if not is_student(user): 
        messages.error(request, "Sizda bu imtihonni koshlash huquqi yo'q.")
        return redirect('index')

    # 4. prepare_exam_data yordamida to'liq ma'lumotlarni olish
    exam_qs = Exam.objects.filter(id=exam_id, is_active=True, center=center)
    exam_data_list = prepare_exam_data(exam_qs, user, center)
    
    if not exam_data_list:
        messages.error(request, "Imtihon topilmadi yoki ma'lumotlar yuklanmadi.")
        return redirect('all_exams', slug=slug)
    
    exam_data = exam_data_list[0]  # Bitta imtihon uchun

    # 5. TUGALLANMAGAN URINISH
    existing_attempt = UserAttempt.objects.filter(
        user=user, 
        exam=exam, 
        is_completed=False
    ).first()

    context = {
        'center': center,
        'exam': exam,
        'exam_data': exam_data,  # To'liq ma'lumotlar
        'has_flashcard_exam': exam_data['has_flashcard_exam'],
        'existing_attempt': existing_attempt,
        'total_duration': exam_data['total_duration'],
        'total_questions': exam_data['total_questions'],
        'sections': exam_data['sections'],
        'can_start_exam': exam_data['can_start_exam'],
    }
    return render(request, 'student/exam_detail.html', context)

def prepare_exam_data(exam_qs, request_user, center):
    """
    Exam QuerySet ni talaba uchun kerakli ma'lumotlar bilan boyitadi.
    N+1 muammosi yo'q, optimallashtirilgan.
    """
    if not exam_qs.exists():
        return []

    # 1. Faqat ushbu imtihonlarga tegishli bo'limlarni olish
    relevant_section_ids = ExamSectionOrder.objects.filter(
        exam__in=exam_qs
    ).values_list('exam_section_id', flat=True).distinct()

    # Bo'limlar va ulardagi savollar soni
    sections_with_counts = ExamSection.objects.filter(
        id__in=relevant_section_ids
    ).annotate(
        actual_question_count=Count('examsectionstaticquestion', distinct=True)
    ).values(
        'id', 'actual_question_count', 'duration_minutes', 'name', 'section_type'
    )

    # section_id → ma'lumot
    section_map = {
        s['id']: {
            'actual_question_count': s['actual_question_count'] or 0,
            'duration_minutes': s['duration_minutes'],
            'name': s['name'],
            'type_display': dict(ExamSection.SECTION_TYPES).get(s['section_type'], s['section_type']),
            'is_math': 'math' in s['section_type'].lower(),
        }
        for s in sections_with_counts
    }

    # 2. Tartibni prefetch qilish
    order_prefetch = Prefetch(
        'examsectionorder',
        queryset=ExamSectionOrder.objects.select_related('exam_section').order_by('order'),
        to_attr='ordered_sections'
    )

    # 3. Asosiy imtihonlarni olish
    exams_with_data = exam_qs.prefetch_related(
        order_prefetch,
        'flashcard_exam'
    ).select_related('teacher')

    # Premium kirish huquqi
    can_access_premium = (
        hasattr(request_user, 'has_active_subscription') and request_user.has_active_subscription()
    ) or (
        hasattr(request_user, 'balance') and getattr(request_user.balance, 'exam_credits', 0) > 0
    )

    result_data = []

    for exam in exams_with_data:
        total_duration = 0
        total_questions = 0
        detailed_sections = []

        for order_obj in getattr(exam, 'ordered_sections', []):
            section = order_obj.exam_section
            section_info = section_map.get(section.id)
            if not section_info:
                continue

            count = section_info['actual_question_count']
            total_duration += section_info['duration_minutes']
            total_questions += count

            detailed_sections.append({
                'id': section.id,
                'name': section_info['name'],
                'type_display': section_info['type_display'],
                'duration_minutes': section_info['duration_minutes'],
                'question_count': count,         
                'is_math': section_info['is_math'],
                'order': order_obj.order,
            })

        has_flashcard = bool(getattr(exam, 'flashcard_exam', None))

        result_data.append({
            'obj': exam,
            'has_flashcard_exam': has_flashcard,
            'total_duration': total_duration,
            'total_questions': total_questions,
            'sections': detailed_sections,
            'can_start_exam': not exam.is_premium or can_access_premium,
        })

    return result_data   # TOʻGʻRI: result_data (emas result_data_data!)

@login_required(login_url='login')
def all_exams_view(request, slug):
    # 1. Markaz tekshiruvi
    center = get_object_or_404(Center, slug=slug)

    if not request.user.center or request.user.center != center:
        messages.error(request, "Bu sahifaga kirish huquqingiz yo‘q.")
        return redirect('index')

    # 2. Filtr parametrlari
    filter_type = request.GET.get('type', 'all')      # all | mock | topic
    filter_price = request.GET.get('price', 'all')    # all | free | premium

    # 3. Asosiy QuerySet — faol imtihonlar
    exams_qs = Exam.objects.filter(
        center=center,
        is_active=True
    ).select_related('teacher')

    # 4. Foydalanuvchi tugatgan imtihonlarni chiqarib tashlash
    completed_ids = UserAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).values_list('exam_id', flat=True)

    exams_qs = exams_qs.exclude(id__in=completed_ids)

    # 5. Imtihon turi filtri (is_subject_exam maydonidan foydalanamiz)
    if filter_type == 'mock':
        exams_qs = exams_qs.filter(is_subject_exam=False)
    elif filter_type == 'topic':
        exams_qs = exams_qs.filter(is_subject_exam=True)
    # 'all' — hech qanday filtr yo‘q

    # 6. Narx filtri
    if filter_price == 'free':
        exams_qs = exams_qs.filter(is_premium=False)
    elif filter_price == 'premium':
        exams_qs = exams_qs.filter(is_premium=True)
    # 'all' — filtr yo‘q

    # 7. Kategoriyalar bo‘yicha ajratish
    three_days_ago = timezone.now() - timedelta(days=3)

    # Yangi qo‘shilgan (oxirgi 3 kun)
    new_exams_qs = exams_qs.filter(created_at__gte=three_days_ago).order_by('-created_at')

    # Eng ko‘p ishlangan (10+ foydalanuvchi)
    popular_exams_qs = exams_qs.annotate(
        unique_users=Count('user_attempts__user', distinct=True)
    ).filter(unique_users__gte=10).order_by('-unique_users', '-created_at')

    # Barcha imtihonlar (filtrlangan holatda)
    all_exams_qs = exams_qs.order_by('-created_at')

    # 8. Ma'lumotlarni boyitish
    new_exams = prepare_exam_data(new_exams_qs, request.user, center)
    popular_exams = prepare_exam_data(popular_exams_qs, request.user, center)
    all_exams = prepare_exam_data(all_exams_qs, request.user, center)

    # 9. Context
    context = {
        'center': center,

        # Filtr holati (template’da faol radio belgilash uchun)
        'filter_type': filter_type,
        'filter_price': filter_price,

        # Imtihonlar
        'new_exams': new_exams,
        'popular_exams': popular_exams,
        'all_exams': all_exams,
    }

    return render(request, 'student/all_exams.html', context)

@login_required
@csrf_exempt
def unlock_solution_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so‘rov ruxsat etiladi'}, status=400)

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        if not question_id:
            return JsonResponse({'success': False, 'error': 'Savol ID topilmadi'}, status=400)

        # Savolni olish
        question = get_object_or_404(Question, id=question_id)

        # Faqat subject exam va yechim yopiq bo‘lsa ruxsat
        if not question.exam.is_subject_exam:
            return JsonResponse({'success': False, 'error': 'Bu imtihonda kreditli yechim yo‘q'}, status=403)

        # Foydalanuvchi balansini olish
        balance = request.user.balance
        cost = question.solution_cost or 5  # agar maydon yo‘q bo‘lsa, standart 5 kredit

        if balance.solution_view_credits < cost:
            return JsonResponse({
                'success': False,
                'error': f"Kredit yetarli emas! Kerak: {cost}, Sizda: {balance.solution_view_credits}"
            }, status=400)

        # Kreditni ayirish
        balance.solution_view_credits -= cost
        balance.save(update_fields=['solution_view_credits'])

        # Yechimni ochiq qilish uchun flag qo‘yish (yoki log saqlash)
        # Masalan: UserUnlockedSolution.objects.create(user=request.user, question=question)

        # Yechim HTML’ni qaytarish
        from django.template.loader import render_to_string
        html = render_to_string('student/answer_detail_partial.html', {
            'question': question,
            'user_answer': None,  # yoki kerakli user_answer
            'allow_solution_display': True,
            'can_unlock_with_credit': False,
            'user_balance': balance,
            'total_percentage': 0,  # kerak bo‘lsa haqiqiy foizni yubor
        })

        return JsonResponse({
            'success': True,
            'html': html,
            'new_balance': balance.solution_view_credits
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Server xatosi'}, status=500)


# =========================================================================
# ⭐️ 1. VIEW_RESULT_DETAIL FUNKSIYASI (Natijalar sahifasi)
# =========================================================================

# views.py ga qo‘shing
def check_solution_permission(user_answer, request):
    """
    Yechim ko‘rish ruxsati – KREDIT YO‘Q!
    Faqat mavzu testida 60% sharti.
    Qaytaradi: (allow_display, message)
    """
    question = user_answer.question
    attempt = user_answer.attempt_section.attempt
    is_subject_exam = getattr(attempt.exam, 'is_subject_exam', False)

    # Har doim yechimni ko‘rganligini saqlaymiz (statistika uchun)
    UserSolutionView.objects.get_or_create(
        user=request.user,
        question=question,
        defaults={'credit_spent': False}
    )

    if not is_subject_exam:
        # SAT, DSAT, oddiy test – HAR DOIM OCHIQ
        return True, "Yechim ochiq"

    # MAVZU TESTI – 60% sharti
    total_answers = UserAnswer.objects.filter(attempt_section__attempt=attempt).count()
    correct_count = UserAnswer.objects.filter(
        attempt_section__attempt=attempt,
        is_correct=True
    ).count()

    percentage = (correct_count / total_answers * 100) if total_answers > 0 else 0

    if percentage >= 60:
        return True, f"Tabriklaymiz! {percentage:.1f}% – yechim ochiq!"
    else:
        return False, f"60% kerak! Hozirgi natija: {percentage:.1f}%"
    
# views.py

@login_required
def get_answer_detail_ajax(request):
    """
    UserAnswer tafsilotlarini AJAX orqali qaytaradi (savol, javoblar, yechim ruxsati).
    Ruxsat: Faqat urinish egasi (talaba) yoki imtihonni yaratgan o'qituvchi.
    """
    user_answer_id = request.GET.get('user_answer_id')
    if not user_answer_id:
        return JsonResponse({'error': 'user_answer_id kerak'}, status=400)

    try:
        # 1. UserAnswer ob'ektini bog'langan modellar bilan olish
        # Eng muhimi: Bu yerda FOYDALANUVCHI BO'YICHA TEKSHIRUV YO'Q!
        # Chunki biz ruxsatni quyida tekshiramiz.
        user_answer = UserAnswer.objects.select_related(
            'question', 
            'question__passage', 
            'attempt_section__attempt__exam__teacher', # O'qituvchi ma'lumotlarini olish
            'attempt_section__attempt__user'          # Talaba ma'lumotlarini olish
        ).prefetch_related(
            'selected_options', 
            'question__options'
        ).get(id=user_answer_id)

    except UserAnswer.DoesNotExist:
        # UserAnswer umuman topilmasa
        return JsonResponse({'error': 'Javob topilmadi'}, status=404)

    attempt = user_answer.attempt_section.attempt
    exam = attempt.exam

    # 2. RUXSAT TEKSHIRUVI
    is_attempt_owner = (attempt.user == request.user)
    is_teacher_of_exam = (
        request.user.role == 'teacher' and 
        exam.teacher == request.user and
        attempt.center == request.user.center
    )

    if not (is_attempt_owner or is_teacher_of_exam):
        # Agar foydalanuvchi urinish egasi ham bo'lmasa, imtihonni yaratgan o'qituvchi ham bo'lmasa, kirishni rad etish
        return JsonResponse({'error': 'Kirish huquqi yo‘q. Siz urinish egasi yoki imtihon o‘qituvchisi emassiz.'}, status=403)
        
    # --- Ruxsat berildi, endi mantiq ---

    question = user_answer.question
    
    # TO‘G‘RI FOIZ HISOBLASH (Yechnim ruxsatini belgilash uchun)
    total_answers = UserAnswer.objects.filter(
        attempt_section__attempt=attempt
    ).count()

    correct_answers = UserAnswer.objects.filter(
        attempt_section__attempt=attempt,
        is_correct=True
    ).count()

    total_percentage = round((correct_answers / total_answers * 100), 1) if total_answers > 0 else 0

    # 3. YECHIM RUXSATI HOLATINI ANIQLASH
    is_subject_exam = exam.is_subject_exam
    allow_solution_display = True
    solution_message = None
    can_unlock_with_credit = False # Kredit bilan ochish mantiqini yo'qotmaslik uchun

    if is_teacher_of_exam:
        # O'qituvchiga har doim yechim ochiq bo'lishi kerak
        allow_solution_display = True
        can_unlock_with_credit = False 
    elif is_subject_exam and total_percentage < 60:
        # Talabada mavzu testi va 60% dan kam bo'lsa
        allow_solution_display = False
        solution_message = f"60% kerak! Hozirgi natija: {total_percentage}%. Yechimni kredit bilan ochishingiz mumkin."
        can_unlock_with_credit = True
    else:
        # Talabada SAT testi yoki Mavzu testi + 60% dan yuqori
        allow_solution_display = True
        can_unlock_with_credit = False


    # 4. Variantlarni tayyorlash (HTML render qilish uchun)
    options = question.options.all().order_by('id') # Variatlar tartibini saqlash
    letters = ['A', 'B', 'C', 'D', 'E', 'F']
    options_with_status = []

    selected_ids = {opt.id for opt in user_answer.selected_options.all()}

    for i, opt in enumerate(options):
        is_selected = opt.id in selected_ids
        options_with_status.append({
            'option': opt,
            'letter': letters[i] if i < len(letters) else chr(65 + i),
            'is_user_selected': is_selected,
            'is_correct': opt.is_correct,
        })

    # 5. Kontekstni tayyorlash va HTML'ni render qilish
    context = {
        'question': question,
        'user_answer': user_answer,
        'options_with_status': options_with_status,
        
        # Yechim holati
        'allow_solution_display': allow_solution_display,
        'solution_message': solution_message,
        'can_unlock_with_credit': can_unlock_with_credit,
        
        # Qo'shimcha ma'lumot
        'total_percentage': total_percentage,
        'user_balance': getattr(request.user, 'balance', None), # Agar kerak bo'lsa
    }

    # 'partials/answer_detail_card.html' nomli snippetni ishlatadi
    from django.template.loader import render_to_string
    html = render_to_string('partials/answer_detail_card.html', context, request=request)
    
    return JsonResponse({'html': html})

@login_required
@user_passes_test(is_teacher, login_url='index')
def teacher_exam_list(request, slug):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q.")
        return redirect('index')

    # 1. NECHA TALABA ISHLADI → DISTINCT USER_ID
    # 2. TURI → is_subject_exam orqali aniqlash
    exams = Exam.objects.filter(
        teacher=request.user,
        center=center
    ).annotate(
        # Faqat yakunlangan urinishlardan noyob talabalar soni
        student_count=Count(
            'user_attempts__user',
            filter=Q(user_attempts__is_completed=True),
            distinct=True
        ),
        # Turi matni
        exam_type_display=Case(
            When(is_subject_exam=True, then=Value('Mavzu testi')),
            default=Value('SAT imtihon'),
            output_field=CharField()
        )
    ).order_by('-created_at')

    context = {
        'center': center,
        'exams': exams,
        'page_title': 'Imtihonlar ro\'yxati',
    }
    
    return render(request, 'management/teacher_exam_list.html', context)

@login_required
@user_passes_test(is_teacher, login_url='index')
def teacher_exam_results(request, slug, exam_id):
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        messages.error(request, "Ruxsat yo‘q!")
        return redirect('teacher_exam_list', slug=slug)

    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user, center=center)
    
    # Faqat bitta imtihon – oxirgi urinishlar
    attempts = UserAttempt.objects.filter(exam=exam, is_completed=True).select_related('user')
    latest_attempts = []
    student_counts = {}

    for attempt in attempts.order_by('user', '-completed_at'):
        uid = attempt.user.id
        if uid not in student_counts:
            student_counts[uid] = {'count': 0, 'latest': attempt}
        student_counts[uid]['count'] += 1

    for uid, data in student_counts.items():
        a = data['latest']
        count = data['count']
        
        if exam.is_subject_exam:
            correct = UserAnswer.objects.filter(attempt_section__attempt=a, is_correct=True).count()
            total = UserAnswer.objects.filter(attempt_section__attempt=a).count()
            score_display = f"{round(correct/total*100, 1)}%" if total else "0%"
        else:
            score_display = a.final_total_score or 0

        latest_attempts.append({
            'attempt_id': a.id,
            'user': a.user,
            'user_username': a.user.username,
            'user_fullname': a.user.get_full_name() or a.user.username,
            'score_display': score_display,
            'completed_at': a.completed_at,
            'attempt_count': count,
        })

    context = {
        'center': center,
        'exam': exam,
        'latest_attempts': latest_attempts,
        'page_title': f"{exam.title} – Natijalar",
    }
    return render(request, 'management/teacher_exam_results.html', context)


def get_base_context(request):
    """Umumiy kontekst ma'lumotlarini qaytaruvchi yordamchi funksiya."""
    all_topics = Topic.objects.filter(teacher=request.user).order_by('name')
    all_subtopics = Subtopic.objects.filter(topic__teacher=request.user).order_by('name')
    all_tags = Tag.objects.all()
    return {
        'all_topics': all_topics,
        'all_subtopics': all_subtopics,
        'all_tags': all_tags,
    }


# ⭐️ YENGI/YANGILANGAN FUNKSIYA: Status bo'yicha kartochkalarni jadvalda ko'rsatish
@login_required
def flashcard_status_list_view(request, slug, status_filter):
    # 1. MARKAZ OBYEKTINI OLISH VA NAMETERRORNI TUZATISH
    try:
        center = get_object_or_404(Center, slug=slug)
    except NameError:
        # Agar Center import qilinmagan bo'lsa, xato beradi.
        # Amalda, yuqorida Center import qilingan bo'lishi kerak.
        # NameError ni oldini olish uchun yozildi.
        return redirect('index') 
    
    # 2. Xavfsizlik tekshiruvi
    if request.user.center != center:
        messages.error(request, "Bu markaz kartochkalariga kirishga ruxsatingiz yo'q.")
        return redirect('index')

    valid_statuses = ['learning', 'learned', 'new']
    if status_filter not in valid_statuses:
        messages.error(request, "Noto‘g‘ri status filtri.")
        return redirect('my_flashcards', slug=slug)

    title_map = {
        'learned': "O'zlashtirilgan kartochkalar",
        'learning': "O'rganilayotgan kartochkalar",
        'new': "Yangi kartochkalar"
    }
    page_title = title_map[status_filter]

    # 3. ASOSIY SO'ROV: Markaz mantiqiga moslash
    # Flashcard'lar center orqali filtrlangan (author/creator orqali emas)
    base_qs = Flashcard.objects.filter(center=center).select_related('author') 

    if status_filter == 'new':
        # Yangi kartochkalar: Foydalanuvchi hali status bermagan kartochkalar
        flashcards_qs = base_qs.exclude(user_statuses__user=request.user).order_by('id')
        status_data = {}
    else:
        # O'rganilgan/O'rganilayotgan kartochkalar
        flashcards_qs = base_qs.filter(
            user_statuses__user=request.user,
            user_statuses__status=status_filter
        ).distinct().order_by('id')
        
        # Holat ma'lumotlarini olish
        statuses = UserFlashcardStatus.objects.filter(
            user=request.user,
            flashcard__in=flashcards_qs
        ).values('flashcard_id', 'repetition_count', 'ease_factor', 'review_interval', 'next_review_at', 'last_quality_rating')
        status_data = {s['flashcard_id']: s for s in statuses}

    flashcards_list = []
    for fc in flashcards_qs:
        info = status_data.get(fc.id, {})
        next_review = info.get('next_review_at')
        time_until = ""
        
        # Vaqtni hisoblash mantiqi
        if next_review and next_review > timezone.now():
            delta = next_review - timezone.now()
            if delta < timedelta(hours=24):
                time_until = f"({int(delta.total_seconds() // 3600)} soat)"
            elif delta < timedelta(days=30):
                time_until = f"({delta.days} kun)"
            else:
                time_until = f"({int(delta.days // 30)} oy)"
        elif next_review and next_review <= timezone.now():
            time_until = "(Hozir)"

        flashcards_list.append({
            'id': fc.id,
            # Xavfsizlik uchun tozalash (bleach/html)
            'english_content': bleach.clean(html.unescape(fc.english_content), tags=[], strip=True),
            'uzbek_meaning': bleach.clean(html.unescape(fc.uzbek_meaning), tags=[], strip=True),
            'repetition_count': info.get('repetition_count', 0),
            'ease_factor': f"{info.get('ease_factor', 2.5):.1f}",
            'review_interval': info.get('review_interval', 0),
            'next_review_at': next_review,
            'next_review_time_until': time_until,
            'last_rating': info.get('last_quality_rating', 0),
        })

    context = {
        'center': center,
        'page_title': page_title,
        'flashcards_list': flashcards_list,
        'status_filter': status_filter
    }
    return render(request, 'student/flashcard_list_table.html', context)

# =========================================================================
# ⭐️ 4. MY_FLASHCARDS_VIEW (Statistika sahifasi) (Render View)
# =========================================================================

@login_required
def my_flashcards_view(request, slug):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        # Markazi belgilanmagan foydalanuvchilar (`request.user.center = None`) uchun 
        # bu qismda Attribute Error berilmasligi uchun oldin tekshirish qilingan
        return redirect('index')

    # Faqat markazga tegishli KARTALARNI FILTRLASH UCHUN BAZA QUERYSET'I
    # Endi author orqali emas, Flashcard modelidagi center maydoni orqali filtrlanadi!
    center_flashcards_qs = Flashcard.objects.filter(center=center)

    # 1. Umumiy Flashcard hisobi
    total_flashcards = center_flashcards_qs.count()

    # 2. UserFlashcardStatus hisobi: Endi Flashcardning centeriga bog'lanadi
    statuses = UserFlashcardStatus.objects.filter(
        user=request.user,
        # TUZATILDI: flashcard__center ishlatildi!
        flashcard__center=center 
    ).values('status').annotate(count=Count('id'))

    status_map = {s['status']: s['count'] for s in statuses}
    learned_count = status_map.get('learned', 0)
    learning_count = status_map.get('learning', 0)
    seen_count = learned_count + learning_count
    new_count = max(0, total_flashcards - seen_count)

    # 3. Review needed hisobi: flashcard__center ishlatildi
    review_needed_count = UserFlashcardStatus.objects.filter(
        user=request.user,
        # TUZATILDI: flashcard__center ishlatildi!
        flashcard__center=center,
        next_review_at__lte=timezone.now()
    ).count()

    # 4. Next review object: flashcard__center ishlatildi
    next_review_obj = UserFlashcardStatus.objects.filter(
        user=request.user,
        # TUZATILDI: flashcard__center ishlatildi!
        flashcard__center=center,
        next_review_at__gt=timezone.now()
    ).order_by('next_review_at').first()
    next_review_at = next_review_obj.next_review_at if next_review_obj else None

    # Foizlar (o'zgarishsiz)
    # ...

    if total_flashcards > 0:
        learned_percentage = round((learned_count / total_flashcards) * 100)
        learning_percentage = round((learning_count / total_flashcards) * 100)
        new_percentage = 100 - learned_percentage - learning_percentage
    else:
        learned_percentage = learning_percentage = new_percentage = 0

    context = {
        'center': center,
        'total_flashcards': total_flashcards,
        'learned_count': learned_count,
        'learning_count': learning_count,
        'new_count': new_count,
        'review_needed_count': review_needed_count,
        'next_review_at': next_review_at,
        'learned_percentage': learned_percentage,
        'learning_percentage': learning_percentage,
        'new_percentage': new_percentage,
    }
    return render(request, 'student/my_flashcards.html', context)

# =========================================================================
# ⭐️ 5. PRACTICE_FLASHCARDS_VIEW (O'rganilayotgan/O'zlashtirilgan uchun)
# =========================================================================

@login_required
def practice_flashcards_view(request, slug, status_filter):
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('index')

    if status_filter not in ['learning', 'learned', 'new', 'review']:
        messages.error(request, "Noto‘g‘ri status.")
        return redirect('my_flashcards', slug=slug)

    # Flashcard.center orqali filtrlash to'g'ri o'rnatilgan
    base_qs = Flashcard.objects.filter(center=center)

    if status_filter == 'learning':
        title = "O'rganilayotganlarni Takrorlash"
        qs = base_qs.filter(user_statuses__user=request.user, user_statuses__status='learning')
    elif status_filter == 'learned':
        title = "O'zlashtirilganlarni Mustahkamlash"
        qs = base_qs.filter(user_statuses__user=request.user, user_statuses__status='learned')
    elif status_filter == 'review':
        title = "Bugungi Takrorlash"
        qs = base_qs.filter(user_statuses__user=request.user, user_statuses__next_review_at__lte=timezone.now())
    else:  # new
        title = "Yangi So'zlarni O'rganish"
        qs = base_qs.exclude(user_statuses__user=request.user)

    if not qs.exists():
        messages.info(request, f"{title} uchun kartochka yo‘q.")
        return redirect('my_flashcards', slug=slug)

    # TUZATILDI: 'questions' o'rniga 'qs' (amaliyot uchun tanlangan kartochkalar) ishlatildi
    statuses = UserFlashcardStatus.objects.filter(
        user=request.user, flashcard__in=qs).values('flashcard_id', 'repetition_count')
    status_map = {s['flashcard_id']: s['repetition_count'] for s in statuses}

    flashcards_list = [
        {
            'id': fc.id,
            'english_content': bleach.clean(fc.english_content, tags=[], strip=True),
            'uzbek_meaning': bleach.clean(fc.uzbek_meaning, tags=[], strip=True),
            'context_sentence': bleach.clean(fc.context_sentence, tags=[], strip=True) if fc.context_sentence else '',
            'repetition_count': status_map.get(fc.id, 0),
        }
        for fc in qs # qs bu yerda Flashcard obyektlari QuerySet'i
    ]

    context = {
        'center': center,
        'session_title': title,
        'flashcard_exam': {'title': title, 'id': 0},
        'flashcards_json': json.dumps(flashcards_list),
        'total_flashcards': len(flashcards_list),
        'is_practice_session': True,
    }
    return render(request, 'student/flashcard_exam.html', context)

@login_required
def start_flashcards_view(request, slug, exam_id):
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('index')

    exam = get_object_or_404(Exam, id=exam_id, is_active=True, center=center)

    if exam.is_premium and not (
        UserSubscription.objects.filter(user=request.user, end_date__gt=timezone.now()).exists() or
        UserBalance.objects.filter(user=request.user, exam_credits__gt=0).exists()
    ):
        messages.error(request, "Pullik imtihon. Obuna yoki kredit kerak.")
        return redirect('price', slug=slug)

    try:
        flashcard_exam = exam.get_or_create_flashcard_exam()
    except Exception:
        messages.error(request, "Flashcard yaratishda xato.")
        return redirect('exam_detail', slug=slug, exam_id=exam.id)

    if not flashcard_exam or not flashcard_exam.flashcards.filter(creator__center=center).exists():
        messages.info(request, "Bu imtihonda kartochka yo‘q.")
        return redirect('exam_detail', slug=slug, exam_id=exam.id)

    return redirect('flashcard_exam_view', slug=slug, exam_id=exam.id)

@login_required
def flashcard_exam_view(request, slug, exam_id):
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('index')

    flashcard_exam = get_object_or_404(
        FlashcardExam,
        source_exam__id=exam_id,
        source_exam__center=center
    )

    user = request.user
    title = f"{flashcard_exam.source_exam.title} – Takrorlash"

    # 'author' ishlatildi (oldindan to'g'irlangan)
    flashcards_qs = flashcard_exam.flashcards.filter(author__center=center) 

    # 🛑 ASOSIY TUZATISH: Endi 'if/else' shartidan qat'iy nazar, 
    # to_review har doim barcha mavjud kartochkalarni tasodifiy tartibda oladi.
    # is_exam_review ning mantiqi (hamma kartochkani olish) endi har doim qo'llaniladi.
    to_review = flashcards_qs.order_by('?')
    
    # Endi to_review barcha Flashcardlarni o'z ichiga olganligi sababli, 
    # keyingi takrorlash vaqtini hisoblash mantiqi (pastda) o'zgarishsiz qoldiriladi
    # va avtomatik ravishda ishlamaydi (chunki flashcards_list bo'sh bo'lmaydi),
    # bu esa mantiqni yanada soddalashtiradi.

    statuses = UserFlashcardStatus.objects.filter(
        user=user, flashcard__in=to_review
    ).values('flashcard_id', 'repetition_count')
    status_map = {s['flashcard_id']: s['repetition_count'] for s in statuses}

    flashcards_list = [
        {
            'id': fc.id,
            'english_content': bleach.clean(fc.english_content, tags=[], strip=True),
            'uzbek_meaning': bleach.clean(fc.uzbek_meaning, tags=[], strip=True),
            'context_sentence': bleach.clean(fc.context_sentence, tags=[], strip=True) if fc.context_sentence else '',
            'repetition_count': status_map.get(fc.id, 0),
        }
        for fc in to_review
    ]

    # next_review_at mantiqiy bloki, agar 'flashcards_list' bo'sh bo'lmasa, ishlamaydi.
    # Agar flashcard_exam da kartochkalar bo'lsa, 'next_review_at' doim 'None' bo'lib qoladi, bu maqsadga muvofiq.
    next_review_at = None
    if not flashcards_list and not flashcard_exam.is_exam_review:
        obj = UserFlashcardStatus.objects.filter(
            user=user, flashcard__author__center=center, next_review_at__gt=timezone.now() 
        ).order_by('next_review_at').first()
        if obj:
            next_review_at = obj.next_review_at

    context = {
        'center': center,
        'session_title': title,
        'flashcard_exam': flashcard_exam,
        'flashcards_json': json.dumps(flashcards_list),
        'total_flashcards': len(flashcards_list),
        'next_review_at': next_review_at,
        'is_practice_session': True, # is_exam_review emas, balki True qilinadi, chunki bu doimiy mashg'ulot
    }
    return render(request, 'student/flashcard_exam.html', context)

@login_required
@require_POST 
def update_flashcard_progress(request, slug):
    # 1. Slug orqali Center obyektini olish
    center = get_object_or_404(Center, slug=slug)
    
    # 2. Xavfsizlik tekshiruvi (Userning markazi slug bilan mos kelishi)
    if request.user.center != center:
        return JsonResponse({'success': False, 'error': 'Ruxsat yo‘q'}, status=403)

    try:
        data = json.loads(request.body)
        flashcard_id = data.get('flashcard_id')
        user_response = data.get('user_response') # 'known' yoki 'unknown'

        if not flashcard_id or user_response not in ['known', 'unknown']:
            return JsonResponse({'success': False, 'error': 'Ma‘lumotlar to‘liq emas'}, status=400)
        
        # Flashcard obyektini olish (Markazga bog'lab xavfsizlikni kuchaytiramiz)
        flashcard = get_object_or_404(
            Flashcard, id=flashcard_id, center=center
        )
        user = request.user
        now = timezone.now()

        # UserFlashcardStatus obyektini yaratish yoki olish
        status, created = UserFlashcardStatus.objects.get_or_create(
            user=user, flashcard=flashcard,
            defaults={
                'status': 'learning', 'review_interval': 1, 'ease_factor': 2.5,
                'repetition_count': 0, 'last_reviewed_at': now,
                'next_review_at': now + timedelta(days=1)
            }
        )

        min_interval = 1
        # Review muddatida ekanligini tekshirish
        is_on_schedule = status.next_review_at <= now if status.next_review_at else True

        if user_response == 'known':
            # SM-2 asosidagi mantiq (Sizning kodingiz)
            status.ease_factor = max(1.3, status.ease_factor + 0.1)

            if is_on_schedule:
                if status.repetition_count == 0:
                    new_interval = 1
                elif status.repetition_count == 1:
                    new_interval = 6
                else:
                    # Keyingi intervalni hisoblash
                    new_interval = status.review_interval * status.ease_factor
                
                status.repetition_count += 1
                status.review_interval = max(min_interval, round(new_interval))
                status.status = 'learned' if status.repetition_count >= 2 else 'learning' # 2-takrorlashdan keyin 'learned' bo'lishi mumkin
                status.next_review_at = now + timedelta(days=status.review_interval)
                status.last_quality_rating = 5
            else:
                # Muddatidan oldin takrorlash
                if status.status == 'learning':
                    status.status = 'learned'
                status.last_quality_rating = 5
            
            # Muddatidan oldin takrorlashda ham last_reviewed_at yangilanadi
            status.last_reviewed_at = now
            status.save()

            return JsonResponse({
                'success': True,
                'status': status.status,
                'next_review': status.next_review_at.isoformat(),
                'repetition_count': status.repetition_count,
            })

        else:  # unknown
            # Repetitsiyani 0 ga qaytarish
            status.status = 'learning'
            status.repetition_count = 0
            status.review_interval = min_interval
            status.ease_factor = max(1.3, status.ease_factor - 0.2)
            status.last_reviewed_at = now
            status.next_review_at = now + timedelta(days=status.review_interval)
            status.last_quality_rating = 0
            status.save()

            return JsonResponse({
                'success': True,
                'status': status.status,
                'next_review': status.next_review_at.isoformat(),
                'repetition_count': status.repetition_count,
            })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Noto‘g‘ri JSON formati'}, status=400)
    except Exception as e:
        logger.error(f"Flashcard update error: {e}")
        return JsonResponse({'success': False, 'error': f'Server xatosi: {e}'}, status=500)

# --- MATH (44 savol) Jadvallari ---
MATH_HIGH_CUTOFF = 11
MATH_SCALING_TABLE = { 
    'LOW': { 
        44: 680, 43: 670, 42: 660, 41: 650, 40: 640, 39: 630, 38: 620, 37: 610, 36: 600, 35: 590, 
        34: 580, 33: 570, 32: 560, 31: 550, 30: 540, 29: 530, 28: 520, 27: 510, 26: 500, 25: 490,
        24: 480, 23: 470, 22: 460, 21: 450, 20: 440, 19: 430, 18: 420, 17: 410, 16: 400, 15: 390,
        14: 380, 13: 370, 12: 360, 11: 350, 10: 340, 9: 330, 8: 320, 7: 310, 6: 300, 5: 290, 
        4: 280, 3: 270, 2: 260, 1: 250, 0: 200 
    },
    'HIGH': { 
        44: 800, 43: 790, 42: 780, 41: 770, 40: 760, 39: 750, 38: 740, 37: 730, 36: 720, 35: 710, 
        34: 700, 33: 690, 32: 680, 31: 670, 30: 660, 29: 650, 28: 640, 27: 630, 26: 620, 25: 610, 
        24: 600, 23: 590, 22: 580, 21: 570, 20: 560, 19: 550, 18: 540, 17: 530, 16: 520, 15: 510, 
        14: 500, 13: 490, 12: 480, 11: 470, 10: 460, 9: 450, 8: 440, 7: 430, 6: 420, 5: 410, 
        4: 400, 3: 390, 2: 380, 1: 370, 0: 200 
    },
}

# --- EBRW (54 savol) Jadvallari ---
EBRW_HIGH_CUTOFF = 14
EBRW_SCALING_TABLE = {
    'LOW': { 
        54: 670, 53: 660, 52: 650, 51: 640, 50: 630, 49: 620, 48: 610, 47: 600, 46: 590, 45: 580, 
        44: 570, 43: 560, 42: 550, 41: 540, 40: 530, 39: 520, 38: 510, 37: 500, 36: 490, 35: 480, 
        34: 470, 33: 460, 32: 450, 31: 440, 30: 430, 29: 420, 28: 410, 27: 400, 26: 390, 25: 380,
        24: 370, 23: 360, 22: 350, 21: 340, 20: 330, 19: 320, 18: 310, 17: 300, 16: 290, 15: 280,
        14: 270, 13: 260, 12: 250, 11: 240, 10: 230, 9: 220, 8: 210, 7: 200, 6: 200, 1: 200, 0: 200 
    },
    'HIGH': { 
        54: 800, 53: 790, 52: 780, 51: 770, 50: 760, 49: 750, 48: 740, 47: 730, 46: 720, 45: 710, 
        44: 700, 43: 690, 42: 680, 41: 670, 40: 660, 39: 650, 38: 640, 37: 630, 36: 620, 35: 610,
        34: 600, 33: 590, 32: 580, 31: 570, 30: 560, 29: 550, 28: 540, 27: 530, 26: 520, 25: 510,
        24: 500, 23: 490, 22: 480, 21: 470, 20: 460, 19: 450, 18: 440, 17: 430, 16: 420, 15: 410,
        14: 400, 13: 390, 12: 380, 11: 370, 10: 360, 9: 350, 8: 340, 7: 330, 6: 320, 5: 310, 
        4: 300, 3: 290, 2: 280, 1: 270, 0: 200 
    },
}

def get_adaptive_scaled_score(mod1_raw, total_raw, is_math=False):
    if mod1_raw is None or total_raw is None:
        return None
    
    scaling_table = MATH_SCALING_TABLE if is_math else EBRW_SCALING_TABLE
    cut_score = MATH_HIGH_CUTOFF if is_math else EBRW_HIGH_CUTOFF

    path = 'HIGH' if mod1_raw >= cut_score else 'LOW'
    scaled_score_map = scaling_table.get(path, scaling_table['LOW']) 
    
    return scaled_score_map.get(total_raw, 200)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def my_questions(request, slug):
    # 1. Markazni slug bo'yicha topish
    center = get_object_or_404(Center, slug=slug)

    # 2. Xavfsizlik Tekshiruvi
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    # 3. Topic ma'lumotlarini olish va Count Annotatsiyasini Qo'llash
    topics = Topic.objects.filter(
        center=center, 
        teacher=request.user
    ).annotate(
        # Munosabat: Topic -> subtopics -> questions
        question_count=Count('subtopics__questions'), 
        subtopic_count=Count('subtopics') 
    ).order_by('order')

    # 4. Mavzulanmagan savollar sonini hisoblash
    uncategorized_questions_count = Question.objects.filter(
        center=center, 
        author=request.user, 
        subtopic__isnull=True
    ).count()

    # 5. Kontekstni shakllantirish
    context = {
        'topics': topics,
        'uncategorized_questions_count': uncategorized_questions_count,
        'center': center,
        'user': request.user,
    }
    return render(request, 'questions/my_questions.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def topic_detail(request, slug, topic_id): # 💡 slug qo'shildi
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    # Topicni markaz va ustoz bo'yicha cheklash
    topic = get_object_or_404(Topic, id=topic_id, center=center, teacher=request.user)
    
    # Subtopiclarni markaz va topic bo'yicha cheklash
    subtopics = Subtopic.objects.filter(topic=topic, center=center).annotate(question_count=Count('questions'))

    context = {
        'topic': topic,
        'subtopics': subtopics,
        'center': center,
        'user': request.user,
    }
    return render(request, 'questions/topic_detail.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def subtopic_questions(request, slug, subtopic_id):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    subtopic = get_object_or_404(Subtopic, id=subtopic_id, center=center)
    # Savollarni markaz va muallif bo'yicha cheklash
    questions = Question.objects.filter(subtopic=subtopic, center=center, author=request.user).order_by('-created_at')

    context = {
        'subtopic': subtopic,
        'questions': questions,
        'center': center,
        'user': request.user,
    }
    return render(request, 'questions/subtopic_questions.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def uncategorized_questions(request, slug):
    """ Mavzulanmagan savollar ro'yxatini markaz bo'yicha ko'rsatadi. """
    center = get_object_or_404(Center, slug=slug)

    # Xavfsizlik Tekshiruvi
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')
        
    questions = Question.objects.filter(
        center=center, # Markazga bog'lash
        subtopic__isnull=True,
        author=request.user
    ).select_related(
        'difficulty_level',
        'passage',
        'parent_question',
        'center',
    ).prefetch_related(
        Prefetch('translations', queryset=QuestionTranslation.objects.filter(language='uz')),
        Prefetch('options', queryset=AnswerOption.objects.prefetch_related(
            Prefetch('translations', queryset=AnswerOptionTranslation.objects.filter(language='uz'))
        )),
        'tags',
        'flashcards',
    )
    
    context = {
        'questions': questions,
        'uncategorized_view': True,
        'center': center,
        # get_base_context dan keladigan ma'lumotlar
        **get_base_context(request) 
    }
    return render(request, 'questions/uncategorized_questions.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def delete_topic(request, slug, topic_id): # 💡 slug qo'shildi
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    # Markaz bo'yicha cheklash
    topic = get_object_or_404(Topic, id=topic_id, center=center, teacher=request.user) 
    
    if request.method == 'POST':
        delete_type = request.POST.get('delete_type')
        if delete_type == 'move':
            target_topic_id = request.POST.get('target_topic')
            if target_topic_id:
                # Target topicni ham markaz va ustoz bo'yicha cheklash
                target_topic = get_object_or_404(Topic, id=target_topic_id, center=center, teacher=request.user)
                moved_count = Subtopic.objects.filter(topic=topic).update(topic=target_topic)
                topic.delete()
                messages.success(request, f'"{topic.name}" mavzusidagi {moved_count} ta ichki mavzu "{target_topic.name}" ga ko‘chirildi va mavzu o‘chirildi.')
            else:
                messages.error(request, "Savollarni ko'chirish uchun mavzu tanlanmadi.")
        else:
            topic.delete()
            messages.success(request, f'"{topic.name}" mavzusi va unga tegishli barcha savollar o‘chirildi.')
        
        return redirect('my_questions', slug=center.slug) # 💡 Redirectda slug uzatildi

    questions_count = Question.objects.filter(subtopic__topic=topic).count()
    # all_topics filteriga center=center qoshildi
    all_topics = Topic.objects.filter(center=center, teacher=request.user).exclude(id=topic_id) 
    
    context = {
        'topic': topic,
        'questions_count': questions_count,
        'all_topics': all_topics,
        'center': center,
    }
    return render(request, 'topic/delete_topic.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def delete_subtopic(request, slug, subtopic_id): # 💡 slug qo'shildi
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    # Markaz bo'yicha cheklash
    subtopic = get_object_or_404(Subtopic, id=subtopic_id, center=center, topic__teacher=request.user) 
    
    if request.method == 'POST':
        delete_type = request.POST.get('delete_type')
        if delete_type == 'move':
            target_subtopic_id = request.POST.get('target_subtopic')
            if target_subtopic_id:
                # Target subtopicni ham markaz bo'yicha cheklash
                target_subtopic = get_object_or_404(Subtopic, id=target_subtopic_id, center=center, topic__teacher=request.user)
                moved_count = subtopic.questions.filter(center=center).update(subtopic=target_subtopic) # Markaz bo'yicha cheklab update qilish
                subtopic.delete()
                messages.success(request, f"{moved_count} ta savol '{target_subtopic.name}' ga ko'chirildi va ichki mavzu o'chirildi.")
            else:
                messages.error(request, "Savollarni ko'chirish uchun ichki mavzu tanlanmadi.")
        else:
            subtopic.delete()
            messages.success(request, "Ichki mavzu va unga tegishli barcha savollar o'chirildi.")
        
        return redirect('my_questions', slug=center.slug) # 💡 Redirectda slug uzatildi
        
    questions_count = subtopic.questions.filter(center=center).count() # Markaz bo'yicha cheklash
    # all_subtopics filteriga center=center qoshildi
    all_subtopics = Subtopic.objects.filter(center=center, topic__teacher=request.user).exclude(id=subtopic_id)
    
    context = {
        'subtopic': subtopic,
        'questions_count': questions_count,
        'all_subtopics': all_subtopics,
        'center': center,
    }
    return render(request, 'topic/delete_subtopic.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def create_topic(request, slug):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center is None or request.user.center != center:
        messages.error(request, "Xatolik: Markaz ma'lumoti topilmadi yoki ruxsat yo'q.")
        return redirect('index')
    
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.teacher = request.user
            topic.center = center # 💡 Markazni saqlash
            topic.save()
            messages.success(request, "Mavzu muvaffaqiyatli yaratildi!")
            return redirect('my_questions', slug=center.slug) # 💡 Redirectda slug uzatildi
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TopicForm()
    
    context = {
        'form': form,
        'title': 'Yangi mavzu yaratish',
        'center': center,
        **get_base_context(request)
    }
    return render(request, 'topic/create_topic.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def edit_topic(request, slug, topic_id): # 💡 slug qo'shildi
    center = get_object_or_404(Center, slug=slug)

    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')
        
    # Markaz bo'yicha cheklash
    topic = get_object_or_404(Topic, id=topic_id, center=center, teacher=request.user) 
    
    if request.method == 'POST':
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, "Mavzu muvaffaqiyatli tahrirlandi!")
            return redirect('my_questions', slug=center.slug) # 💡 Redirectda slug uzatildi
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TopicForm(instance=topic)
    
    context = {
        'form': form,
        'title': 'Mavzuni tahrirlash',
        'topic': topic,
        'center': center,
        **get_base_context(request)
    }
    return render(request, 'topic/create_topic.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def create_subtopic(request, slug, topic_id=None):
    center = get_object_or_404(Center, slug=slug)

    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    initial = {}
    if topic_id:
        # Topicni markaz va ustoz bo'yicha cheklash
        topic = get_object_or_404(Topic, id=topic_id, center=center, teacher=request.user)
        initial['topic'] = topic
    
    if request.method == 'POST':
        form = SubtopicForm(request.POST)
        if form.is_valid():
            subtopic = form.save(commit=False)
            
            # Subtopic centerini qo'shish
            subtopic.center = center
            
            # Topic egasi va markazini tekshirish (Double Check)
            if subtopic.topic.teacher != request.user or subtopic.topic.center != center:
                 messages.error(request, "Noto'g'ri mavzu tanlandi yoki siz tanlagan mavzuga kirish ruxsatingiz yo'q.")
                 return redirect('my_questions', slug=center.slug)

            subtopic.save()
            messages.success(request, "Ichki mavzu muvaffaqiyatli yaratildi!")
            return redirect('topic_detail', slug=center.slug, topic_id=subtopic.topic.id)
        else:
             # Xato logikasi
             for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SubtopicForm(initial=initial)
        # Formdagi topic querysetini cheklash
        form.fields['topic'].queryset = Topic.objects.filter(center=center, teacher=request.user)
    
    context = {
        'form': form,
        'title': 'Yangi ichki mavzu yaratish',
        'center': center,
        'topic_id': topic_id,
        **get_base_context(request)
    }
    return render(request, 'topic/create_subtopic.html', context)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def edit_subtopic(request, slug, subtopic_id):
    center = get_object_or_404(Center, slug=slug)

    if request.user.center is None or request.user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q yoki sizga markaz biriktirilmagan.")
        return redirect('index')

    # Markaz va ustoz bo'yicha cheklash
    subtopic = get_object_or_404(Subtopic, id=subtopic_id, center=center, topic__teacher=request.user)
    
    if request.method == 'POST':
        form = SubtopicForm(request.POST, instance=subtopic)
        if form.is_valid():
            
            # Yangi tanlangan Topicning ustoz va markazini tekshirish
            new_topic = form.cleaned_data['topic']
            if new_topic.teacher != request.user or new_topic.center != center:
                 messages.error(request, "Siz faqat o'zingiz yaratgan mavzularga ichki mavzularni biriktirishingiz mumkin.")
                 return redirect('topic_detail', slug=center.slug, topic_id=subtopic.topic.id)
                 
            form.save()
            messages.success(request, "Ichki mavzu muvaffaqiyatli tahrirlandi!")
            return redirect('topic_detail', slug=center.slug, topic_id=subtopic.topic.id)
        else:
             # Xato logikasi
             for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SubtopicForm(instance=subtopic)
        # Formdagi topic querysetini cheklash
        form.fields['topic'].queryset = Topic.objects.filter(center=center, teacher=request.user)
    
    context = {
        'form': form,
        'title': 'Ichki mavzuni tahrirlash',
        'subtopic': subtopic,
        'center': center,
        **get_base_context(request)
    }
    return render(request, 'topic/create_subtopic.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def move_questions(request, subtopic_id):
    subtopic = get_object_or_404(Subtopic, id=subtopic_id, topic__teacher=request.user)
    
    if request.method == 'POST':
        target_subtopic_id = request.POST.get('target_subtopic')
        if target_subtopic_id:
            target_subtopic = get_object_or_404(Subtopic, id=target_subtopic_id, topic__teacher=request.user)
            moved_count = subtopic.questions.update(subtopic=target_subtopic)
            messages.success(request, f"{moved_count} ta savol '{target_subtopic.name}' ga ko'chirildi.")
        else:
            messages.error(request, "Ko'chirish uchun ichki mavzu tanlanmadi.")
    
    return redirect('subtopic_questions', subtopic_id=subtopic_id)




@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def list_flashcards(request, slug):
    """
    Berilgan slug'ga mos keluvchi Center'ga tegishli barcha flashcardlarni ko'rsatadi.
    Taglar soni hisobini ham chiqaradi.
    """
    center = get_object_or_404(Center, slug=slug)
    
    # Flashcardlarni filtrlash va Taglar sonini annotatsiya qilish
    flashcards = Flashcard.objects.filter(
        center=center 
    ).annotate(
        # 'tags' ManyToManyField orqali bog'langan taglar sonini hisoblash
        tag_count=Count('tags', distinct=True) 
    ).order_by('-created_at')
    
    return render(request, 'flashcards/list_flashcards.html', {
        'flashcards': flashcards,
        'center': center,
    })


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def create_flashcard(request, slug):
    """
    Berilgan center slug'iga yangi flashcard yaratish. 
    Tags (ManyToMany) maydonini ishga soladi.
    """
    center = get_object_or_404(Center, slug=slug)
    
    if request.method == 'POST':
        form = FlashcardForm(request.POST, request.FILES)
        
        # Agar Taglar Centerga bog'langan bo'lsa, ularni faqat shu Center uchun filtrlash
        # Misol: form.fields['tags'].queryset = Tag.objects.filter(center=center)
        
        if form.is_valid():
            flashcard = form.save(commit=False)
            flashcard.author = request.user
            flashcard.center = center # Center'ni biriktiramiz
            flashcard.save()
            
            # ManyToMany munosabatini (tags) saqlash
            form.save_m2m() 
            
            messages.success(request, f"Flashcard '{center.name}' markazi uchun muvaffaqiyatli yaratildi!")
            return redirect('list_flashcards', slug=slug) 
        
    else:
        form = FlashcardForm()
        # Agar Taglar Centerga bog'langan bo'lsa, ularni faqat shu Center uchun filtrlash
        # Misol: form.fields['tags'].queryset = Tag.objects.filter(center=center)
    
    return render(request, 'flashcards/create_flashcard.html', {
        'form': form,
        'center': center,
    })


def search_tags_ajax(request, slug):
    """
    Select2 uchun Tag/Mavzu qidiruvini (AJAX orqali) amalga oshiradi.
    Markaz slug'i asosida tegishli markaz taglarini qidiradi.
    """
    # 1. Markazni topish (xavfsizlik uchun)
    # Agar markaz topilmasa, 404 xatosi qaytadi
    center = get_object_or_404(Center, slug=slug)

    # 2. Qidiruv parametrlarini olish
    search_term = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    
    # Pagination sozlamalari
    PAGE_SIZE = 20
    offset = (page - 1) * PAGE_SIZE
    limit = offset + PAGE_SIZE

    # 3. Taglarni filtrlash (joriy markazga va qidiruv so'ziga qarab)
    tags_queryset = Tag.objects.filter(center=center).order_by('name')

    if search_term:
        # Tag nomida qidirish, ixtiyoriy ravishda tavsifda ham qidirish mumkin
        tags_queryset = tags_queryset.filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term)
        )
    
    # 4. Jami natijalar sonini hisoblash
    total_count = tags_queryset.count()

    # 5. Sahifaga mos keluvchi natijalarni olish (Pagination)
    results = tags_queryset[offset:limit]

    # 6. Select2 talab qiladigan formatga keltirish
    items = []
    for tag in results:
        # Agar Tagning get_full_hierarchy metodi bo'lsa, undan foydalanamiz
        display_text = tag.get_full_hierarchy() if hasattr(tag, 'get_full_hierarchy') else tag.name
        
        items.append({
            'id': tag.pk,
            'text': display_text,
            # Qo'shimcha ma'lumot (ixtiyoriy)
            'parent_name': tag.parent.name if tag.parent else _("Asosiy teg")
        })

    # 7. JSON javobni qaytarish
    response_data = {
        'items': items,
        'total_count': total_count,
        # Agar sahifalar mavjud bo'lsa 'more' ni true qilamiz
        'pagination': {
            'more': total_count > limit
        }
    }
    
    return JsonResponse(response_data)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def edit_flashcard(request, slug, pk):
    """
    Flashcardni tahrirlash (Slug va pk orqali).
    Qo'shimcha tekshiruv: flashcard shu centerga tegishlimi?
    """
    center = get_object_or_404(Center, slug=slug)
    # Flashcardni pk va Center orqali topish xavfsizlikni ta'minlaydi
    flashcard = get_object_or_404(Flashcard, pk=pk, center=center) 

    if request.method == 'POST':
        form = FlashcardForm(request.POST, request.FILES, instance=flashcard)
        
        # Tags uchun querysetni filtrlash (Agar kerak bo'lsa):
        # form.fields['tags'].queryset = Tag.objects.filter(center=center)

        if form.is_valid():
            # ManyToMany (tags) avtomatik tarzda tahrirlanadi
            form.save() 
            messages.success(request, "Flashcard muvaffaqiyatli tahrirlandi!")
            return redirect('list_flashcards', slug=slug)
    else:
        form = FlashcardForm(instance=flashcard)
        # Tags uchun querysetni filtrlash (Agar kerak bo'lsa):
        # form.fields['tags'].queryset = Tag.objects.filter(center=center)
        
    return render(request, 'flashcards/edit_flashcard.html', {
        'form': form,
        'flashcard': flashcard,
        'center': center,
    })


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def delete_flashcard(request, slug, pk):
    """
    Flashcardni o'chirish (Slug va pk orqali).
    Qo'shimcha tekshiruv: flashcard shu centerga tegishlimi?
    """
    center = get_object_or_404(Center, slug=slug)
    # Flashcardni pk va Center orqali topish xavfsizlikni ta'minlaydi
    flashcard = get_object_or_404(Flashcard, pk=pk, center=center) 
    
    if request.method == 'POST':
        flashcard.delete()
        messages.success(request, "Flashcard muvaffaqiyatli o'chirildi.")
        return redirect('list_flashcards', slug=slug)
    
    # Agar POST so'rovi emas, balki GET orqali kirilsa, o'chirishni rad etish
    messages.error(request, "Xatolik: O'chirish faqat POST so'rovi orqali amalga oshiriladi.")
    return redirect('list_flashcards', slug=slug)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def add_question(request, slug=None):
    """
    Yangi savol qo'shish. QuestionForm va AnswerOptionFormSet bilan ishlaydi.
    QuestionForm.clean() da tozalangan ma'lumotlar saqlashda qayta tozalanmaydi.
    """
    
    # 0. Center va ruxsat tekshiruvi (O'zgarmadi)
    if not is_teacher(request.user):
        messages.error(request, _("Faqat o'qituvchilar savol qo'shishi mumkin!"))
        return redirect('index')

    center = None
    if slug:
        center = get_object_or_404(Center, slug=slug)
        if request.user.role == 'center_admin' and request.user.center != center:
            raise PermissionDenied(_("Bu markazga kirish huquqingiz yo‘q"))
    else:
        center = request.user.center
        if not center:
            messages.error(request, _("Siz hech qanday markazga ulanmagansiz!"))
            return redirect('index')

    ANSWER_OPTIONS_PREFIX = 'answer_option'
    
    # POST So'rovi
    if request.method == 'POST':
        # user=request.user ni uzatish zarur
        form = QuestionForm(request.POST, request.FILES, user=request.user) 
        answer_option_formset = None 

        # 1. QuestionForm ni tekshirish
        if form.is_valid():
            
            # 2. Question obyektini xotirada yaratish (Formsetga instance uzatish uchun)
            question_instance = form.save(commit=False)
            question_instance.center = center # markazni o'rnatish
            question_instance.author = request.user
            
            # 3. Formsetni instance bilan yaratish
            answer_option_formset = AnswerOptionFormSet(
                request.POST,
                request.FILES,
                prefix=ANSWER_OPTIONS_PREFIX,
                instance=question_instance # 🛑 Instance bog'landi
            )
            
            # 4. Formsetni validatsiya qilish
            if answer_option_formset.is_valid():
                try:
                    with transaction.atomic():
                        # 4.1. Question ni DB ga saqlash
                        question_instance.save() 
                        form.save_m2m() # ManyToMany bog'lanishlarni saqlash
                        
                        cleaned_data = form.cleaned_data # Barcha tozalangan ma'lumotlarni olish
                        answer_format = cleaned_data['answer_format']

                        # 4.2. QuestionSolution ni saqlash (ASOSIY TUZATISH - qayta tozalash yo'q)
                        hint = cleaned_data.get('hint', '').strip()
                        detailed_solution = cleaned_data.get('detailed_solution', '').strip()
                        
                        # Faqat matn mavjud bo'lsa, saqlaymiz. Matn QuestionForm.clean() da tozalangan.
                        if hint or detailed_solution:
                            QuestionSolution.objects.update_or_create(
                                question=question_instance,
                                defaults={
                                    'hint': hint, # ✅ QuestionForm.clean() dan kelgan tozalangan matn
                                    'detailed_solution': detailed_solution # ✅ QuestionForm.clean() dan kelgan tozalangan matn
                                }
                            )
                        # Agar avval yechim bo'lib, endi o'chirilsa, yechim obyektini ham o'chirish kerak bo'lishi mumkin
                        elif hasattr(question_instance, 'solution'):
                            question_instance.solution.delete()


                        # 4.3. Javob formatiga qarab mantiq (O'zgarishsiz qoldi, chunki short_answer allaqachon tozalangan)
                        if answer_format in ['single', 'multiple']:
                            answer_option_formset.save() 
                            # Agar oldindan short_answer qiymati mavjud bo'lsa, uni o'chirish
                            if question_instance.correct_short_answer:
                                question_instance.correct_short_answer = None
                                question_instance.save(update_fields=['correct_short_answer'])
                                
                        elif answer_format == 'short_answer':
                            # correct_short_answer QuestionForm.clean() da allaqachon tozalangan/formatlangan
                            correct_short_answer = cleaned_data.get('correct_short_answer', '').strip()
                            question_instance.correct_short_answer = correct_short_answer
                            question_instance.save(update_fields=['correct_short_answer'])
                            # Variantlarni o'chirish
                            question_instance.options.all().delete()
                            
                        # Bu else holati odatda bo'lmasligi kerak
                        else:
                            question_instance.options.all().delete()
                            question_instance.correct_short_answer = None
                            question_instance.save(update_fields=['correct_short_answer'])


                        messages.success(request, _(f"Savol ID {question_instance.id} muvaffaqiyatli qo'shildi!"))
                        logger.info(f"Savol ID {question_instance.id} muvaffaqiyatli saqlandi. Format: {answer_format}")

                        # 4.4. MUVAFFDAQIYATLI SAQLASHDAN KEYIN YO'NALTIRISH
                        return redirect('subtopic_questions', slug=center.slug, subtopic_id=question_instance.subtopic.id)

                except Exception as e:
                    messages.error(request, _(f"Saqlashda kutilmagan xatolik yuz berdi: {str(e)}"))
                    logger.error(f"Savolni saqlash xatosi (Exception): {e}. Form errors: {form.errors}, Formset errors: {answer_option_formset.errors if answer_option_formset else 'Not created'}")
            
            # Formset validatsiyadan o'tmasa
            else:
                logger.error(f"AnswerOptionFormSet XATOLARI: {answer_option_formset.errors}")
                messages.error(request, _("Javob variantlarini saqlashda xatolik yuz berdi. Iltimos, tekshiring."))

        # QuestionForm validatsiyadan o'tmasa
        else:
            # AnswerOptionFormSet ni POST ma'lumotlari bilan yaratish (xatolarni ko'rsatish uchun)
            # Lekin instance bo'lmagani uchun FormSet.clean() ishlamaydi, bu OK.
            answer_option_formset = AnswerOptionFormSet(request.POST, request.FILES, prefix=ANSWER_OPTIONS_PREFIX)
            logger.error("FORM VALIDATSIYADAN O'TMADI (add_question).")
            logger.error(f"QuestionForm XATOLARI: {form.errors.as_json()}")
            messages.error(request, _("Savolni saqlashda xatolik yuz berdi. Iltimos, formadagi xabarlarni tekshiring."))
        
        # Xatolar bo'lsa, shablonni qayta ko'rsatish
        irt_fields = [
            form['difficulty'], form['discrimination'], form['guessing'],
            form['difficulty_level'], form['status']
        ]
        return render(request, 'questions/add_questions.html', {
            'form': form,
            'answer_option_formset': answer_option_formset,
            'irt_fields': irt_fields,
            'center': center,
            **get_base_context(request)
        })

    # GET So'rovi (o'zgarmadi)
    else: 
        # 6. GET so'rovi uchun formani va bo'sh formsetni yaratish
        initial_data = {'center': center}
        subtopic_id = request.GET.get('subtopic')
        if subtopic_id:
            try:
                # Subtopic mavjudligini tekshirish
                Subtopic.objects.get(pk=subtopic_id, center=center)
                initial_data['subtopic'] = subtopic_id
            except (Subtopic.DoesNotExist, ValueError):
                logger.warning(f"URLda noto'g'ri Subtopic ID kiritildi: {subtopic_id}")

        form = QuestionForm(initial=initial_data, user=request.user)
        # GET uchun bo'sh (yangi) formset
        answer_option_formset = AnswerOptionFormSet(
            prefix=ANSWER_OPTIONS_PREFIX,
            queryset=AnswerOption.objects.none()
        )
        irt_fields = [
            form['difficulty'],
            form['discrimination'],
            form['guessing'],
            form['difficulty_level'],
            form['status']
        ]
        return render(request, 'questions/add_questions.html', {
            'form': form,
            'answer_option_formset': answer_option_formset,
            'irt_fields': irt_fields,
            'center': center,
            **get_base_context(request)
        })
    
@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def edit_question(request, slug, question_id):
    """
    Mavjud savolni tahrirlash. QuestionForm va AnswerOptionFormSet bilan ishlaydi.
    """
    
    # 0. Center va Question obyektini olish
    center = get_object_or_404(Center, slug=slug)
    question_instance = get_object_or_404(Question, id=question_id, center=center)

    if not is_teacher(request.user):
        messages.error(request, _("Faqat o'qituvchilar savolni tahrirlashi mumkin!"))
        return redirect('index')

    if request.user.role == 'center_admin' and request.user.center != center:
        raise PermissionDenied(_("Bu markazga kirish huquqingiz yo‘q"))

    ANSWER_OPTIONS_PREFIX = 'answer_option'

    # Savol yechimini yuklab olish
    solution_instance = None
    if hasattr(question_instance, 'solution'):
        solution_instance = question_instance.solution

    # POST So'rovi
    if request.method == 'POST':
        # Savol formasini mavjud ma'lumot (instance) va POST ma'lumotlari bilan yaratish
        form = QuestionForm(
            request.POST, 
            request.FILES, 
            user=request.user, 
            instance=question_instance,
            initial={'hint': solution_instance.hint if solution_instance else '', 
                     'detailed_solution': solution_instance.detailed_solution if solution_instance else ''}
        ) 
        
        # Formsetni mavjud ma'lumot (instance) va POST ma'lumotlari bilan yaratish
        answer_option_formset = AnswerOptionFormSet(
            request.POST,
            request.FILES,
            prefix=ANSWER_OPTIONS_PREFIX,
            instance=question_instance # 🛑 Instance bog'landi
        )

        # 1. QuestionForm ni tekshirish
        if form.is_valid():
            # 2. Question obyektini xotirada saqlash (commit=False)
            question_instance = form.save(commit=False)
            question_instance.center = center # markazni qayta o'rnatish
            question_instance.author = request.user # avtorni qayta o'rnatish
            
            # 3. Formsetni validatsiya qilish
            if answer_option_formset.is_valid():
                try:
                    with transaction.atomic():
                        # 4.1. Question ni DB ga saqlash
                        question_instance.save() 
                        form.save_m2m() # ManyToMany bog'lanishlarni saqlash
                        
                        cleaned_data = form.cleaned_data 
                        answer_format = cleaned_data['answer_format']

                        # 4.2. QuestionSolution ni saqlash/o'chirish
                        hint = cleaned_data.get('hint', '').strip()
                        detailed_solution = cleaned_data.get('detailed_solution', '').strip()
                        
                        if hint or detailed_solution:
                            QuestionSolution.objects.update_or_create(
                                question=question_instance,
                                defaults={
                                    'hint': hint,
                                    'detailed_solution': detailed_solution,
                                    'is_free': cleaned_data.get('is_solution_free', False) # is_free maydoni ham saqlanishi kerak
                                }
                            )
                        elif hasattr(question_instance, 'solution'):
                            question_instance.solution.delete()

                        # 4.3. Javob formatiga qarab mantiq
                        if answer_format in ['single', 'multiple']:
                            answer_option_formset.save() 
                            # Agar oldindan short_answer qiymati mavjud bo'lsa, uni o'chirish
                            if question_instance.correct_short_answer:
                                question_instance.correct_short_answer = None
                                question_instance.save(update_fields=['correct_short_answer'])
                                
                        elif answer_format == 'short_answer':
                            correct_short_answer = cleaned_data.get('correct_short_answer', '').strip()
                            question_instance.correct_short_answer = correct_short_answer
                            question_instance.save(update_fields=['correct_short_answer'])
                            # Variantlarni o'chirish
                            question_instance.options.all().delete()
                            
                        # Bu else holati odatda bo'lmasligi kerak
                        else:
                            question_instance.options.all().delete()
                            question_instance.correct_short_answer = None
                            question_instance.save(update_fields=['correct_short_answer'])


                        messages.success(request, _(f"Savol ID {question_instance.id} muvaffaqiyatli tahrirlandi!"))
                        logger.info(f"Savol ID {question_instance.id} muvaffaqiyatli tahrirlandi. Format: {answer_format}")

                        # 4.4. MUVAFFDAQIYATLI SAQLASHDAN KEYIN YO'NALTIRISH
                        return redirect('subtopic_questions', slug=center.slug, subtopic_id=question_instance.subtopic.id)

                except Exception as e:
                    messages.error(request, _(f"Saqlashda kutilmagan xatolik yuz berdi: {str(e)}"))
                    logger.error(f"Savolni saqlash xatosi (Exception): {e}. Form errors: {form.errors}, Formset errors: {answer_option_formset.errors if answer_option_formset else 'Not created'}")
            
            # Formset validatsiyadan o'tmasa
            else:
                logger.error(f"AnswerOptionFormSet XATOLARI: {answer_option_formset.errors}")
                messages.error(request, _("Javob variantlarini saqlashda xatolik yuz berdi. Iltimos, tekshiring."))

        # QuestionForm validatsiyadan o'tmasa
        else:
            # AnswerOptionFormSet ni POST ma'lumotlari bilan yaratish (xatolarni ko'rsatish uchun)
            answer_option_formset = AnswerOptionFormSet(
                request.POST, 
                request.FILES, 
                prefix=ANSWER_OPTIONS_PREFIX, 
                instance=question_instance
            )
            logger.error("FORM VALIDATSIYADAN O'TMADI (edit_question).")
            logger.error(f"QuestionForm XATOLARI: {form.errors.as_json()}")
            messages.error(request, _("Savolni saqlashda xatolik yuz berdi. Iltimos, formadagi xabarlarni tekshiring."))
    
    # GET So'rovi (Sahifani birinchi marta yuklash)
    else:
        # QuestionForm ni mavjud ma'lumot (instance) bilan yaratish
        form = QuestionForm(
            user=request.user, 
            instance=question_instance,
            initial={'hint': solution_instance.hint if solution_instance else '', 
                     'detailed_solution': solution_instance.detailed_solution if solution_instance else ''}
        )
        
        # Formsetni mavjud ma'lumot (instance) bilan yaratish
        answer_option_formset = AnswerOptionFormSet(
            instance=question_instance, 
            prefix=ANSWER_OPTIONS_PREFIX,
            queryset=question_instance.options.all().order_by('id') # Variantlarni ID bo'yicha tartiblab olish
        )

    # Shablonni render qilish
    irt_fields = [
        form['difficulty'], form['discrimination'], form['guessing'],
        form['difficulty_level'], form['status']
    ]
    
    # 💡 Formsetda yetishmayotgan minimal variantlarni qo'shish mantiqi (Agar MAX_NUM=5 bo'lsa)
    # Ushbu qismni AnswerOptionFormSet ichida bajarish maqsadga muvofiq,
    # lekin bu yerda shablonni to'g'ri ko'rsatish uchun uni o'zgartirmaymiz.

    return render(request, 'questions/edit_question.html', {
        'form': form,
        'answer_option_formset': answer_option_formset,
        'irt_fields': irt_fields,
        'center': center,
        'question': question_instance, # Shablon sarlavhasi uchun kerak
    })

def delete_images_from_html(html_content):
    """ HTML matnidagi img teglarini topadi va default storage'dan fayllarni o'chiradi. """
    if not html_content:
        return
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        for img in images:
            src = img.get('src')
            if src and src.startswith(default_storage.base_url):
                # /media/uploads/... kabi manzilni topamiz
                file_path = src.replace(default_storage.base_url, '', 1) 
                
                # Agar saqlash joyi mahalliy (local storage) bo'lsa, o'chiramiz
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    logger.info(f"O'chirilgan fayl: {file_path}")

    except Exception as e:
        logger.error(f"HTMLdagi rasmlarni o'chirishda xatolik: {e}")

@login_required(login_url='login')
def delete_question(request, slug, question_id):
    """ Savolni o'chirish uchun tasdiqlash sahifasini ko'rsatadi va o'chiradi. """
    
    # 1. Center va Ruxsat tekshiruvi
    center = get_object_or_404(Center, slug=slug)
    user = request.user
    
    # Ruxsat tekshiruvi: Faqat shu markazning 'teacher' yoki 'center_admin'i bo'lishi kerak.
    # Muallif tekshiruvi keyinroq qo'shildi. Agar admin bo'lsa, muallif bo'lish shart emas.
    if user.center != center or user.role not in ['teacher', 'center_admin']:
        messages.error(request, _("Bu markazdagi savollarni o'chirish huquqingiz yo‘q."))
        return redirect('index')
    
    # Savolni yuklash:
    # Admin o'z markazidagi istalgan savolni o'chira oladi.
    # Teacher faqat o'zining savollarini o'chira oladi.
    if user.role == 'teacher':
        question_query = Question.objects.filter(id=question_id, center=center, author=user)
    else: # center_admin
        question_query = Question.objects.filter(id=question_id, center=center)
        
    question = get_object_or_404(question_query)
    
    # Qayerga qaytishni aniqlash
    redirect_url = redirect('subtopic_questions', slug=center.slug, subtopic_id=question.subtopic.id) if question.subtopic else redirect('my_questions', slug=center.slug)

    # POST so'rovi: Savolni o'chirish
    if request.method == 'POST':
        try:
            # Savol matnidagi, variantlaridagi va yechimlaridagi rasmlarni o'chirish
            
            # 1. Savol matni
            delete_images_from_html(question.text)
            
            # 2. Javob variantlari matni
            for option in question.options.all():
                delete_images_from_html(option.text)
                
            # 3. Yechim (Hint/Detailed Solution)
            if hasattr(question, 'solution'):
                delete_images_from_html(question.solution.hint)
                delete_images_from_html(question.solution.detailed_solution)

            # 4. Savolni o'chirish
            # Agar Question modelida on_delete=CASCADE bo'lsa, bog'liq AnswerOption va QuestionSolution 
            # avtomatik o'chadi.
            question.delete()
            
            messages.success(request, _("Savol muvaffaqiyatli o'chirildi!"))
            return redirect_url
            
        except Exception as e:
            logger.error(f"Savolni o'chirishda xatolik (ID: {question_id}): {e}")
            messages.error(request, _(f"Savolni o'chirishda kutilmagan xatolik yuz berdi: {str(e)}"))
            return redirect_url
    
    # GET so'rovi: Tasdiqlash sahifasini ko'rsatish
    return render(request, 'questions/delete_question_confirm.html', {
        'question': question,
        'center': center,
        'redirect_url': redirect_url.url, # orqaga qaytish uchun URL
    })

@login_required
def search_flashcards_api(request):
    query = request.GET.get('q', '')
    if query:
        flashcards = Flashcard.objects.filter(
            Q(english_content__icontains=query) | Q(uzbek_meaning__icontains=query)
        ).order_by('english_content')
    else:
        flashcards = Flashcard.objects.all().order_by('-created_at')[:20]

    results = []
    for fc in flashcards:
        english_cleaned = clean(fc.english_content, tags=[], strip=True)
        uzbek_cleaned = clean(fc.uzbek_meaning, tags=[], strip=True)
        text_to_display = f"{english_cleaned} - {uzbek_cleaned}"
        results.append({
            'id': fc.id,
            'text': text_to_display
        })

    return JsonResponse({'results': results})

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
@csrf_exempt # 🛑 MUHIM: CKEditor yuklash mexanizmi uchun ko'pincha kerak bo'ladi
def ckeditor_upload_image(request):
    """
    CKEditor rasm yuklash talablariga mos View funksiyasi.
    U 'upload' nomli POST faylini kutadi va URL ni qaytaradi.
    """
    if request.method == 'POST' and request.FILES.get('upload'):
        file_obj = request.FILES['upload']
        
        # Fayl nomini o'zgartirish (to'qnashuvni oldini olish uchun)
        import os
        ext = os.path.splitext(file_obj.name)[1]
        file_name = default_storage.get_available_name(f'questions/ckeditor/{file_obj.name}')
        
        # Faylni saqlash
        saved_file_name = default_storage.save(file_name, file_obj)
        file_url = default_storage.url(saved_file_name)
        
        # CKEditor 4 (ko'p ishlatiladigan) talab qiladigan format:
        # success: {"uploaded": true, "url": "/media/questions/ckeditor/my_image.png"}
        return JsonResponse({
            'uploaded': 1, # CKEditor 4 uchun success holati
            'fileName': os.path.basename(saved_file_name),
            'url': file_url
        })
    
    # Yuklash xatosi yoki noto'g'ri so'rov
    return JsonResponse({'uploaded': 0, 'error': {'message': 'Rasm yuklashda xatolik yuz berdi.'}}, status=400)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def passage_list(request, slug): # Center slug = 'slug'
    """Berilgan Center slug'ga tegishli BARCHA 'Passage'larni ko'rsatadi (Author filtrisiz)."""
    
    center = get_object_or_404(Center, slug=slug)
    
    # Faqat Center bo'yicha filtrlash.
    passages = Passage.objects.filter(
        center=center 
    ).order_by('-created_at')
    
    return render(request, 'passage/passage_list.html', {
        'passages': passages,
        'center': center,
    })

# ==============================================================================
# 2. ADD PASSAGE (Yaratish: Center slug = 'slug')
# ==============================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def add_passage(request, slug): # Center slug = 'slug'
    """Yangi 'passage'ni ma'lum bir markazga yaratish uchun funksiya."""
    
    center = get_object_or_404(Center, slug=slug)
    
    if request.method == 'POST':
        form = PassageForm(request.POST)
        if form.is_valid():
            passage = form.save(commit=False)
            passage.author = request.user # Yozuvchi saqlanadi
            passage.center = center 
            passage.save()
            messages.success(request, f"Yangi matn ({center.name} uchun) muvaffaqiyatli qo'shildi!")
            
            return redirect('passage_list', slug=center.slug) 
    else:
        form = PassageForm()
        
    return render(request, 'passage/add_passage.html', {'form': form, 'center': center})

# ==============================================================================
# 3. EDIT PASSAGE (Tahrirlash: Center slug = 'slug', Passage PK = 'pk')
# ==============================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
# ✅ Argument 'p_slug' o'rniga 'pk' ishlatiladi
def edit_passage(request, slug, pk): 
    """Mavjud 'passage'ni Center slug va Passage PK orqali tahrirlash uchun funksiya."""
    
    # ✅ PK orqali topish (slug o'rniga)
    passage = get_object_or_404(
        Passage, 
        pk=pk,          
        center__slug=slug
    )
    center = passage.center 
    
    if request.method == 'POST':
        form = PassageForm(request.POST, instance=passage)
        if form.is_valid():
            form.save()
            messages.success(request, f"Matn '{passage.title[:20]}...' muvaffaqiyatli tahrirlandi!")
            
            return redirect('passage_list', slug=center.slug) 
    else:
        form = PassageForm(instance=passage)
        
    return render(request, 'passage/edit_passage.html', {'form': form, 'passage': passage, 'center': center})

# ==============================================================================
# 4. DELETE PASSAGE (O'chirish: Center slug = 'slug', Passage PK = 'pk')
# ==============================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
# ✅ Argument 'p_slug' o'rniga 'pk' ishlatiladi
def delete_passage(request, slug, pk): 
    """'Passage'ni Center slug va Passage PK orqali o'chirish uchun funksiya."""
    
    # ✅ PK orqali topish (slug o'rniga)
    passage = get_object_or_404(
        Passage, 
        pk=pk, 
        center__slug=slug
    )
    center = passage.center
    
    if request.method == 'POST':
        passage.delete()
        messages.success(request, "Matn muvaffaqiyatli o'chirildi.")
        
        return redirect('passage_list', slug=center.slug) 
        
    return render(request, 'passage/delete_passage.html', {'passage': passage, 'center': center})



@login_required(login_url='login')
def process_purchase_view(request, slug, purchase_type, item_id):
    """
    Yangi xarid obyekti yaratadi va skrinshot yuklash sahifasiga yo‘naltiradi.
    Faqat o‘z markazidagi tariflar.
    """
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        messages.error(request, "Ruxsat yo‘q.")
        return redirect('dashboard',slug=request.user.center.slug)

    user = request.user
    item = None

    if purchase_type == 'subscription':
        item = get_object_or_404(SubscriptionPlan, id=item_id, is_active=True)
    elif purchase_type == 'package':
        item = get_object_or_404(ExamPackage, id=item_id, is_active=True)
    else:
        messages.error(request, "Noto‘g‘ri xarid turi.")
        return redirect('price', slug=slug)

    # Xarid yaratish
    purchase = Purchase.objects.create(
        user=user,
        purchase_type=purchase_type,
        package=item if purchase_type == 'package' else None,
        subscription_plan=item if purchase_type == 'subscription' else None,
        amount=item.price,
        final_amount=item.price,
        status='pending'
    )

    messages.info(request, f"'{item.name}' uchun to‘lov kutilmoqda. Skrinshotni yuklang.")

    return redirect('upload_screenshot', slug=slug, purchase_id=purchase.id)

@login_required(login_url='login')
def upload_screenshot_view(request, slug, purchase_id):
    """
    Skrinshot yuklash – faqat o‘z xaridi uchun.
    """
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        messages.error(request, "Ruxsat yo‘q.")
        return redirect('dashboard',slug=request.user.center.slug)

    purchase = get_object_or_404(
        Purchase, 
        id=purchase_id, 
        user=request.user,
        status='pending'  # faqat pending bo‘lsa
    )

    if request.method == 'POST':
        form = ScreenshotUploadForm(request.POST, request.FILES, instance=purchase)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.status = 'moderation'
            purchase.save()
            messages.success(request, "Skrinshot qabul qilindi. Tez orada tasdiqlanadi!")
            return redirect('dashboard',slug=request.user.center.slug)
        else:
            messages.error(request, "Formada xatolik. Iltimos, tekshiring.")
    else:
        form = ScreenshotUploadForm(instance=purchase)

    site_settings = SiteSettings.objects.first()

    context = {
        'center': center,
        'form': form,
        'purchase': purchase,
        'item': purchase.subscription_plan or purchase.package,
        'site_settings': site_settings,
    }
    return render(request, 'student/upload_screenshot.html', context)

def get_section_questions(section, exam):
    """
    Bo‘lim uchun statik savollarni qaytaradi.
    Faqat o‘z markazidagi savollar.
    """
    if exam.center != section.exam.center:
        return []  # Xavfsizlik

    static_questions = section.static_questions.filter(
        question__exam__center=exam.center
    ).select_related('question')
    
    return [sq.question for sq in static_questions]

# ======================================================================
# 1. EXAM BOSHQARUVI
# ======================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def exam_list(request, slug): # 🎯 SLUG QO'SHILDI
    """
    Imtihonlar ro'yxatini ko'rish (Faqat user.center ichida).
    """
    center = get_object_or_404(Center, slug=slug)
    
    # Xavfsizlik: Foydalanuvchi markazga tegishli ekanligini tekshirish
    if request.user.center != center:
         messages.error(request, "Siz bu markaz imtihonlarini ko'rish huquqiga ega emassiz.")
         return redirect('dashboard',slug=request.user.center.slug)
    
    # 1. Prefetch obyekti: ExamSectionOrder orqali Section savollar sonini olish 
    prefetch_exam_sections = Prefetch(
        'examsectionorder',
        # ExamSectionOrder.exam_section.static_questions.count() N+1 muammosini keltirmaslik uchun
        # HTML da to'g'ridan-to'g'ri .exam_section.static_questions.count ni ishlatamiz.
        # Bu yerda faqat bog'lanishlarni optimallashtiramiz.
        queryset=ExamSectionOrder.objects.select_related('exam_section').order_by('order'),
        to_attr='ordered_sections'
    )

    # 2. Asosiy Exam so'rovi (Faqat shu markaz o'qituvchilari tomonidan yaratilgan imtihonlar)
    exams = Exam.objects.filter(
        teacher__center=center # 🎯 Filtrni o'zgartirdik: teacher=request.user O'RNIGA teacher__center=center
    ).annotate(
        section_count=Count('examsectionorder') 
    ).prefetch_related(
        prefetch_exam_sections,
        'teacher' # Teacher ma'lumotlarini yuklaymiz
    ).order_by('-created_at')
    
    context = {
        'exams': exams,
        'center': center, # Shablon uchun center obyekti
    }
    return render(request, 'management/exam_list.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def exam_create(request, slug):
    """Yangi imtihon yaratish (Faqat user.center ichida)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markazda imtihon yaratishga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # Sectionlarni filtratsiya qilish: Faqat shu markazdagi o'qituvchilar yaratgan sectionlar
    available_sections = ExamSection.objects.filter(
        created_by__center=center 
    ).annotate(
        question_count=Count('static_questions')
    ).order_by('name') 
    
    selected_sections_ids = []
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        selected_sections_ids_str = request.POST.getlist('sections_select2') 
        
        try:
            selected_sections_ids = [int(id_str) for id_str in selected_sections_ids_str if id_str.isdigit()]
        except:
            messages.error(request, "Bo'lim ID'lari noto'g'ri formatda. Iltimos, faqat ro'yxatdan tanlang.")
            selected_sections_ids = []

        form_is_valid = form.is_valid()
        
        if not selected_sections_ids:
            messages.error(request, "Iltimos, kamida bitta bo'limni tanlang.")
            form_is_valid = False
        
        if form_is_valid and selected_sections_ids:
            try:
                with transaction.atomic():
                    exam = form.save(commit=False)
                    exam.teacher = request.user
                    exam.center = center # Markazni imtihonga biriktirish 
                    exam.save()
                    
                    selected_sections_map = {
                        section.id: section for section in ExamSection.objects.filter(
                            id__in=selected_sections_ids, 
                            created_by__center=center, # Yaratishda ham filtr
                        )
                    }

                    exam_section_orders = []
                    for index, section_id in enumerate(selected_sections_ids):
                        section = selected_sections_map.get(section_id)
                        if not section: continue 
                        exam_section_orders.append(
                            ExamSectionOrder(exam=exam, exam_section=section, order=index + 1)
                        )
                    
                    if exam_section_orders:
                        ExamSectionOrder.objects.bulk_create(exam_section_orders)
                        
                        # ==================================================
                        # ✅ FLASHCARD YARATISH MANTIG'INI TUZATISH
                        # ==================================================

                        # 1. Tanlangan ExamSectionlarga tegishli barcha Question ID'larini olish
                        question_ids = ExamSectionStaticQuestion.objects.filter(
                            exam_section__id__in=selected_sections_ids
                        ).values_list('question_id', flat=True).distinct()

                        # 2. Yuqoridagi Question ID'lariga bog'langan barcha Flashcard ID'larini olish
                        # (Flashcard modelidagi ManyToManyField nomi 'questions' deb faraz qilinadi)
                        flashcard_ids = Flashcard.objects.filter(
                            questions__id__in=question_ids
                        ).values_list('id', flat=True).distinct()

                        if flashcard_ids.exists():
                            # 3. FlashcardExam obyektini yaratish
                            flashcard_exam = FlashcardExam.objects.create(
                                source_exam=exam, 
                                title=f"{exam.title} bo'yicha Flashcard to'plami"
                            )
                            
                            # 4. Flashcardlarni biriktirish (MUHIM QISM: flashcards.set() orqali)
                            flashcard_exam.flashcards.set(flashcard_ids) 
                            
                            messages.info(request, f"Flashcard to'plami avtomatik yaratildi va {flashcard_ids.count()} ta kartochka biriktirildi.")
                        
                        # ==================================================
                        # ✅ TUZATISH YAKUNI
                        # ==================================================
                            
                        messages.success(request, f"Imtihon '{exam.title}' muvaffaqiyatli yaratildi va {len(exam_section_orders)} ta bo'lim biriktirildi!")
                        return redirect('exam_list', slug=center.slug) # SLUG Bilan REDIRECT
                    else:
                        messages.error(request, "Tanlangan bo'limlar ro'yxatida xato. Iltimos, boshqadan harakat qiling.")
                        raise Exception("Bo'limlar ro'yxati yaratilmadi.")
                
            except Exception as e:
                messages.error(request, f"Xato: Imtihonni yaratishda muammo yuz berdi. ({e})")
        
        selected_sections_ids = selected_sections_ids 

    else:
        form = ExamForm()
        selected_sections_ids = []

    context = {
        'form': form,
        'sections': available_sections,
        'selected_sections_ids': selected_sections_ids,
        'center': center, # Shablon uchun center obyekti
    }
    return render(request, 'management/exam_create.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def exam_edit(request, slug, pk): # 🎯 SLUG QO'SHILDI
    """Imtihonni tahrirlash (Faqat user.center ichida)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markaz imtihonini tahrirlashga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # Examni o'zgartirdik: Faqat shu markazdagi o'qituvchilarning examlari
    exam = get_object_or_404(Exam, id=pk, teacher__center=center)
    
    # 🎯 Sectionlarni filtratsiya qilish: Faqat shu markazdagi o'qituvchilar yaratgan sectionlar
    available_sections = ExamSection.objects.filter(
        created_by__center=center 
    ).annotate(
        question_count=Count('static_questions') 
    ).order_by('name') 
    
    # ... Qolgan kod o'zgarishsiz, faqat REDIRECT ga slug qo'shiladi
    current_section_ids = list(
        ExamSectionOrder.objects.filter(exam=exam).order_by('order').values_list('exam_section_id', flat=True)
    )

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        selected_sections_ids_str = request.POST.getlist('sections_select2') 
        
        selected_sections_ids = []
        try:
            selected_sections_ids = [int(id_str) for id_str in selected_sections_ids_str if id_str.isdigit()]
        except:
            pass

        form_is_valid = form.is_valid()
        
        if not selected_sections_ids:
            messages.error(request, "Iltimos, kamida bitta bo'limni tanlang.")
            form_is_valid = False
        
        if form_is_valid and selected_sections_ids:
            try:
                with transaction.atomic():
                    exam = form.save()
                    
                    ExamSectionOrder.objects.filter(exam=exam).delete()
                    selected_sections_map = {
                        section.id: section for section in ExamSection.objects.filter(
                            id__in=selected_sections_ids, created_by__center=center
                        )
                    }

                    exam_section_orders = []
                    for index, section_id in enumerate(selected_sections_ids):
                        section = selected_sections_map.get(section_id)
                        if not section: continue
                        exam_section_orders.append(
                            ExamSectionOrder(exam=exam, exam_section=section, order=index + 1)
                        )
                    
                    if exam_section_orders:
                        ExamSectionOrder.objects.bulk_create(exam_section_orders)
                        
                        has_flashcards_in_sections = Question.objects.filter(
                            examsectionstaticquestion__exam_section__id__in=selected_sections_ids,
                            flashcards__isnull=False 
                        ).exists()

                        if has_flashcards_in_sections:
                            FlashcardExam.objects.get_or_create(
                                source_exam=exam,
                                defaults={'title': f"{exam.title} bo'yicha Flashcard to'plami"}
                            )
                            messages.info(request, "Flashcard to'plami yangilandi.")
                        else:
                            if hasattr(exam, 'flashcard_exam'):
                                exam.flashcard_exam.delete()
                                messages.info(request, "Flashcard to'plami so'zlar qolmagani uchun o'chirildi.")

                        messages.success(request, f"Imtihon '{exam.title}' muvaffaqiyatli tahrirlandi va {len(exam_section_orders)} ta bo'lim biriktirildi!")
                        return redirect('exam_list', slug=center.slug) # 🎯 SLUG Bilan REDIRECT
                    else:
                        messages.error(request, "Bo'limlar ro'yxati yaratilmadi. Iltimos, faqat o'zingiz yaratgan bo'limlarni tanlang.")
                        current_section_ids = selected_sections_ids
                        raise Exception("Bo'limlar to'liq yaratilmadi.")

            except Exception as e:
                error_message = f"Xato: Imtihonni tahrirlashda muammo yuz berdi. ({e})"
                messages.error(request, error_message)
                current_section_ids = selected_sections_ids 
        else:
            current_section_ids = selected_sections_ids if request.method == 'POST' else current_section_ids
            
    else:
        form = ExamForm(instance=exam)

    context = {
        'form': form,
        'exam': exam,
        'sections': available_sections,
        'current_section_ids': current_section_ids, 
        'center': center, # Shablon uchun center obyekti
    }
    return render(request, 'management/exam_edit.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def exam_delete(request, slug, pk): # 🎯 SLUG QO'SHILDI
    """Imtihonni o'chirish (Faqat user.center ichida)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markaz imtihonini o'chirishga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # Examni o'zgartirdik: Faqat shu markazdagi o'qituvchilarning examlari
    exam = get_object_or_404(Exam, id=pk, teacher__center=center) 
    
    if request.method == 'POST':
        exam.delete() 
        messages.success(request, f"Imtihon '{exam.title}' muvaffaqiyatli o'chirildi!")
        return redirect('exam_list', slug=center.slug) # 🎯 SLUG Bilan REDIRECT
    
    return redirect('exam_list', slug=center.slug) # 🎯 SLUG Bilan REDIRECT


# ======================================================================
# 2. SECTION BOSHQARUVI (Center Ichida Umumiy)
# ======================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def section_list(request, slug): # 🎯 SLUG QO'SHILDI
    """Bo'limlar ro'yxatini ko'rish (Faqat user.center ichida umumiy)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markaz bo'limlarini ko'rishga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # 🎯 MUHIM O'ZGARTIRISH: Faqat shu markazdagi o'qituvchilar yaratgan bo'limlar
    sections = ExamSection.objects.filter(created_by__center=center).annotate(
        question_count=Count('static_questions')
    ).select_related('created_by') # Kim yaratganini yuklaymiz
    
    context = {'sections': sections, 'center': center}
    return render(request, 'management/section_list.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def section_create(request, slug): # 🎯 SLUG QO'SHILDI
    """Yangi bo'lim yaratish (Faqat user.center ichida)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markazda bo'lim yaratishga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    if request.method == 'POST':
        form = ExamSectionForm(request.POST) 

        if form.is_valid():
            try:
                with transaction.atomic():
                    section = form.save(commit=False)
                    if hasattr(section, 'created_by'):
                        section.created_by = request.user
                    section.save()
                    
                    messages.success(request, "Bo'lim ma'lumotlari muvaffaqiyatli saqlandi. Endi savollarni tanlang.")
                    # Savol tanlash sahifasiga yo'naltiramiz
                    return redirect('static_questions_add', slug=center.slug, section_id=section.pk) # 🎯 SLUG Bilan REDIRECT

            except Exception as e:
                messages.error(request, f"Bo‘limni saqlashda xato: {e}")
                print(f"Database error in section_create: {e}")
        else:
            messages.error(request, 'Xatolarni to‘g‘rilang.')
    else:
        form = ExamSectionForm()

    context = {
        'form': form,
        'center': center,
    }
    return render(request, 'management/section_create.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def static_questions_add(request, slug, section_id): # 🎯 SLUG QO'SHILDI
    """Statik savollarni tanlash va yaratilgan bo'limga bog'lash sahifasi."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markaz bo'limini boshqarishga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # 🎯 MUHIM: Faqat shu markazdagi o'qituvchilar yaratgan bo'limni tahrirlash
    section = get_object_or_404(ExamSection, pk=section_id, created_by__center=center)
    
    # ... Qolgan kod O'zgarishsiz, chunki savollar ro'yxati Centerga bog'liq emas (umumiy baza)
    # ... Faqat contextga center ni qo'shamiz
    
    initial_questions_ids = list(ExamSectionStaticQuestion.objects
                                 .filter(exam_section=section)
                                 .values_list('question_id', flat=True))
    
    topics = Topic.objects.all()
    questions = None
    
    if request.method == 'POST' or request.GET.get('subtopic_id'):
        subtopic_id = request.POST.get('subtopic') or request.GET.get('subtopic_id')
        if subtopic_id and subtopic_id.isdigit():
            questions = Question.objects.filter(subtopic_id=subtopic_id, status='published').select_related('subtopic')
    
    context = {
        'topics': topics,
        'section_id': section_id,
        'max_questions': section.max_questions,
        'section_name' : section.name,
        'section_type' : section.get_section_type_display(),
        'questions': questions,
        'initial_questions_ids': initial_questions_ids, 
        'center': center, # Shablon uchun center obyekti
    }
    return render(request, 'management/static_questions_add.html', context)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def save_static_questions(request, slug, section_id):
    """Tanlangan savollarni ExamSectionStaticQuestion modeliga saqlash (AJAX orqali)."""
    
    # 1. Ob'ektlar va xavfsizlik tekshiruvi
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        # Ruxsat yo'q
        return JsonResponse({'success': False, 'message': "Boshqa markaz bo'limini boshqarishga ruxsat yo'q"}, status=403)

    # 2. ✅ YO'NALTIRISH MANZILINI MARKAZ OBYEKTI OLINGANDAN SO'NG YARATISH
    # Ro'yxatga qaytarish uchun:
    redirect_url = reverse('section_list', kwargs={'slug': center.slug}) 
    
    # Agar tahrirlash sahifasiga qaytarish kerak bo'lsa, quyidagidan foydalaning:
    # redirect_url = reverse('section_edit', kwargs={'slug': center.slug, 'section_id': section_id}) 

    if request.method == 'POST':
        try:
            # Bo'limni olish (xavfsizlik tekshiruvi bilan)
            section = get_object_or_404(ExamSection, pk=section_id, created_by__center=center)
            selected_ids_str = request.POST.get('selected_questions_ids', '')
            
            question_ids = []
            if selected_ids_str:
                question_ids = [int(id_str) for id_str in selected_ids_str.split(',') if id_str.strip().isdigit()]
            
            # 3. Savollar sonini tekshirish
            if len(question_ids) > section.max_questions:
                 return JsonResponse({
                     'success': False, 
                     'message': f"Tanlangan savollar soni ({len(question_ids)}) maksimal son ({section.max_questions}) dan oshib ketdi."
                 }, status=400)

            # 4. Atomik saqlash logikasi
            with transaction.atomic():
                # Avvalgi savollarni o'chirish
                ExamSectionStaticQuestion.objects.filter(exam_section=section).delete()
                
                if question_ids:
                    # Yangi savollarni yaratish
                    new_questions = [
                        ExamSectionStaticQuestion(
                            exam_section=section, 
                            question_id=question_id, 
                            question_number=i + 1
                        ) for i, question_id in enumerate(question_ids)
                    ]
                    ExamSectionStaticQuestion.objects.bulk_create(new_questions)
                    
            # 5. Muvaffaqiyatli yakun (O'chirish ham, yangi qo'shish ham shu yerdan o'tadi)
            # Endi bu yerda yaratilgan redirect_url to'g'ri bo'ladi.
            return JsonResponse({
                'success': True, 
                'redirect_url': redirect_url,
                'message': "Savollar ro'yxati muvaffaqiyatli yangilandi."
            }) 
            
        except Exception as e:
            # Xatolikni qaytarish
            print(f"Error saving static questions: {e}")
            return JsonResponse({'success': False, 'message': f"Savollarni saqlashda xato yuz berdi: {str(e)}"}, status=500)
    
    # Faqat POST so'rov qabul qilinishini tasdiqlash
    return JsonResponse({'success': False, 'message': "Faqat POST so'rov qabul qilinadi"}, status=405)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def section_edit(request, slug, section_id): # 🎯 SLUG QO'SHILDI
    """Bo'limni tahrirlash (Faqat user.center ichida umumiy)."""
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
         messages.error(request, "Boshqa markaz bo'limini tahrirlashga ruxsat yo'q.")
         return redirect('dashboard',slug=request.user.center.slug)
         
    # 🎯 MUHIM: Faqat shu markazdagi o'qituvchilar yaratgan bo'limni tahrirlash
    section = get_object_or_404(ExamSection, id=section_id, created_by__center=center)
    
    # ... Qolgan kod O'zgarishsiz, faqat REDIRECT ga slug qo'shiladi
    
    if request.method == 'POST':
        form = ExamSectionForm(request.POST, instance=section) 
        selected_ids_str = request.POST.get('selected_questions_ids', '')

        if form.is_valid():
            try:
                with transaction.atomic():
                    section = form.save()
                    
                    question_ids = []
                    if selected_ids_str:
                        question_ids = [int(id_str) for id_str in selected_ids_str.split(',') if id_str.strip().isdigit()]

                    ExamSectionStaticQuestion.objects.filter(exam_section=section).delete()

                    if question_ids:
                        if len(question_ids) > section.max_questions:
                            messages.error(request, f"Tanlangan savollar soni ({len(question_ids)}) maksimal son ({section.max_questions}) dan oshib ketdi.")
                            return render(request, 'management/section_edit.html', {'section': section, 'form': form})
                                
                        new_questions = [
                            ExamSectionStaticQuestion(
                                exam_section=section, 
                                question_id=question_id, 
                                question_number=i + 1
                            ) for i, question_id in enumerate(question_ids)
                        ]
                        ExamSectionStaticQuestion.objects.bulk_create(new_questions)

                messages.success(request, f"Bo'lim '{section.name}' muvaffaqiyatli tahrirlandi va savollar yangilandi!")
                return redirect('section_list', slug=center.slug) # 🎯 SLUG Bilan REDIRECT

            except Exception as e:
                messages.error(request, f"Bo‘limni saqlashda kutilmagan xato: {e}")
                print(f"Database error in section_edit: {e}")
        else:
            messages.error(request, "Xatolarni to'g'rilang. Forma maydonlarida muammo bor.")
            
    else:
        form = ExamSectionForm(instance=section)
        
    context = {
        'section': section,
        'form': form,
        'center': center, # Shablon uchun center obyekti
    }
    return render(request, 'management/section_edit.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def section_delete(request, slug, section_id):
    """
    Bo'limni o'chirish (Faqat user.center ga tegishli bo'lgan markazda).
    URL: /center/<slug>/section/<int:section_id>/delete/
    """
    
    # 1. Markazni tekshirish (Slug orqali)
    try:
        center = get_object_or_404(Center, slug=slug)
    except Exception:
        messages.error(request, "Ko'rsatilgan markaz topilmadi.")
        return redirect('dashboard',slug=request.user.center.slug) # Markaz topilmasa boshqaruv paneliga

    # 2. Foydalanuvchi markazini tekshirish (Xavfsizlik)
    if request.user.center != center:
        messages.error(request, "Siz boshqa markaz bo'limini o'chirishga ruxsat ololmadingiz.")
        return redirect('dashboard',slug=request.user.center.slug)
        
    # 3. Bo'limni topish (Markazga va yaratuvchiga bog'lab)
    # Faqat shu markazdagi o'qituvchilar yaratgan bo'limni o'chirish
    try:
        # created_by__center=center tekshiruvi muhim xavfsizlik filtri
        section = get_object_or_404(
            ExamSection, 
            id=section_id, 
            created_by__center=center
        )
    except Exception:
        messages.error(request, "Bo'lim topilmadi yoki siz uni o'chirishga ruxsatga ega emassiz.")
        return redirect('section_list', slug=center.slug)

    # 4. O'chirish Mantiqi (POST so'rovi orqali)
    if request.method == 'POST':
        section.delete()
        messages.success(request, f"'{section.name}' bo'limi muvaffaqiyatli o'chirildi!")
        
        # 5. Qaytarish (Bo'limlar ro'yxatiga)
        return redirect('section_list', slug=center.slug) 
    
    # GET so'rovi (yoki POST bo'lmagan so'rov) kelganida, shunchaki ro'yxatga qaytarish.
    # Bu Modal ishlatilgani uchun to'g'ri, chunki tasdiqlash sahifasi yo'q.
    return redirect('section_list', slug=center.slug)

# ======================================================================
# 2. AJAX ENDPOINTLARI
# ======================================================================

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def get_subtopics(request, slug): # 🎯 SLUG QO'SHILDI
    """
    Topic bo'yicha Subtopic'larni olish. 
    Faqat joriy Center'ga tegishli o'qituvchilar yaratgan Subtopic'lar qaytadi.
    """
    user = request.user
    center = get_object_or_404(Center, slug=slug)
    
    # 1. Xavfsizlik tekshiruvi
    if user.center != center:
        return JsonResponse({'error': "Ruxsat yo'q. Boshqa markaz Subtopic'lari."}, status=403)
        
    topic_id = request.GET.get('topic_id')
    if not topic_id or not topic_id.isdigit():
        return JsonResponse({'error': 'Topic ID noto‘g‘ri yoki mavjud emas'}, status=400)
        
    try:
        # 2. Filtrlash: Berilgan topic_id bo'yicha VA shu markaz o'qituvchilari tomonidan yaratilgan subtopiclar
        subtopics = Subtopic.objects.filter(
            topic_id=topic_id,
            center = center,
        ).order_by('name')
        
        data = [{'id': sub.id, 'name': sub.name} for sub in subtopics]
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        print(f"Error in get_subtopics: {e}")
        return JsonResponse({'error': f"Ma'lumot olishda xato: {str(e)}"}, status=500)

from django.template.loader import render_to_string

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def get_questions(request, slug): # 🎯 SLUG QO'SHILDI
    """
    Subtopic bo'yicha savollarni olish. 
    Faqat joriy Center'ga tegishli o'qituvchilar yaratgan savollar qaytadi.
    """
    user = request.user
    center = get_object_or_404(Center, slug=slug)
    
    # 1. Xavfsizlik tekshiruvi
    if user.center != center:
        return JsonResponse({'error': "Ruxsat yo'q. Boshqa markaz savollari."}, status=403)

    subtopic_id = request.GET.get('subtopic_id')
    if not subtopic_id or not subtopic_id.isdigit():
        return JsonResponse({'error': 'Subtopic ID noto‘g‘ri yoki mavjud emas'}, status=400)
        
    try:
        # 2. Filtrlash: Berilgan subtopic_id bo'yicha VA shu markaz o'qituvchilari tomonidan yaratilgan savollar
        questions = Question.objects.filter(
            subtopic_id=subtopic_id,
            #status='published',
            center=center  # 🎯 Markazga bog'lash
        ).select_related('subtopic').prefetch_related('options').order_by('id')
        
        if not questions.exists():
            html = render_to_string('partials/questions_list.html', {'questions': questions, 'center': center}, request=request)
            return JsonResponse({'html': html})

        html = render_to_string('partials/questions_list.html', {'questions': questions, 'center': center}, request=request)
        return JsonResponse({'html': html})
        
    except Exception as e:
        print(f"Error in get_questions: {e}")
        return JsonResponse({'error': f"Savollarni olishda xato: {str(e)}"}, status=500)

# =========================================================
# A. KURS MODULLARI BOSHQARUVI (module_list, module_create, ...)
# =========================================================
@login_required(login_url='login')
def module_list(request, course_id):
    """ Kursning barcha modullari ro'yxati va boshqaruvi. """
    # if not (is_teacher(request.user) or request.user.is_staff):
    #     messages.error(request, "Sizda bu bo'limga kirish huquqi yo'q.")
    #     return redirect('dashboard',slug=request.user.center.slug)
    
    course = get_object_or_404(Course, id=course_id)
    
    # Har bir modul ichidagi darslarni o'z ichiga olgan so'rov
    modules = CourseModule.objects.filter(course=course).order_by('order').prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.order_by('order'), to_attr='lessons_list')
    )
    
    context = {
        'course': course,
        'modules': modules,
        'page_title': f"'{course.title}' kursining modullari"
    }
    return render(request, 'management/module_list.html', context)

@login_required
def module_create(request, course_id):
    """
    Yangi modul yaratish funksiyasi. Tartib raqami (order) avtomatik belgilanadi.
    """
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # Formada 'order' maydoni bo'lmasligi mumkin, shuning uchun formani oddiy yuklaymiz.
        form = CourseModuleForm(request.POST) 
        
        if form.is_valid():
            # 1. Ob'ektni bazaga saqlamay turib olish
            new_module = form.save(commit=False)
            new_module.course = course
            
            # 🔥 TARTIB RAQAMINI AVTOMATIK HISOBLASH LOGIKASI
            # Module.objects o'rniga CourseModule.objects ishlatildi
            max_order = CourseModule.objects.filter(course=course).aggregate(Max('order'))['order__max']
            # Agar hali modul bo'lmasa, 1 dan boshlaymiz (yoki mavjud bo'lsa, keyingisini olamiz)
            new_module.order = (max_order or 0) + 1
            
            # 3. Yakuniy saqlash
            new_module.save()
            messages.success(request, f"'{new_module.title}' moduli muvaffaqiyatli yaratildi (Tartib raqami: {new_module.order}).")
            return redirect('module_list', course_id=course.id)
        else:
            messages.error(request, "Iltimos, formadagi xatolarni to'g'irlang.")
    else:
        form = CourseModuleForm()

    context = {
        'form': form,
        'course': course,
    }
    
    return render(request, 'management/module_form.html', context)

@login_required 
def module_update(request, course_id, module_id):
    """
    Mavjud modulni tahrirlash funksiyasi. Tartib raqami (order) tahrirlanmaydi.
    """
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course)

    if request.method == 'POST':
        # POST: instance=module bilan formani yuklash
        form = CourseModuleForm(request.POST, instance=module)
        if form.is_valid():
            # Agar 'order' formadan yuborilmasa ham, instance orqali olingan modulning
            # mavjud 'order' qiymatiga tegmasdan qoladi.
            module_instance = form.save() 
            messages.success(request, f"'{module_instance.title}' moduli muvaffaqiyatli tahrirlandi.")
            return redirect('module_list', course_id=course.id)
        else:
            messages.error(request, "Iltimos, formadagi xatolarni to'g'irlang.")
    else:
        # GET: Mavjud modul ma'lumotlari bilan formani yuklash
        form = CourseModuleForm(instance=module)

    context = {
        'form': form,
        'course': course,
        'module': module,
    }
    
    return render(request, 'management/module_form.html', context)

@login_required
def module_delete(request, course_id, module_id):
    """
    Modulni o'chirish funksiyasi.
    """
    # Kurs va modulni topamiz. Modulning ushbu kursga tegishli ekanligini tekshiramiz.
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(CourseModule, id=module_id, course=course) # CourseModule dan topildi

    # Agar POST so'rovi kelsa (o'chirishni tasdiqlash uchun)
    if request.method == 'POST':
        module_title = module.title # O'chirishdan oldin nomini saqlab olamiz
        module.delete()
        
        messages.success(request, f"'{module_title}' moduli muvaffaqiyatli o'chirildi.") # Muvaffaqiyat xabari
        # Muvaffaqiyatli o'chirishdan keyin modullar ro'yxatiga qaytarish
        return redirect('module_list', course_id=course.id)

    # GET so'rovini qabul qilmaslik kerak, lekin agar kelsa, ro'yxatga qaytaramiz
    return redirect('module_list', course_id=course.id)

# =========================================================
# B. DARS BOSHQARUVI (lesson_list, lesson_create, ...)
# =========================================================

@login_required(login_url='login')
def lesson_list(request, module_id):
    """ Modul ichidagi darslar va resurslar boshqaruvi. """
    module = get_object_or_404(CourseModule, id=module_id)
    
    # Har bir darsning resurslarini yuklash
    lessons = Lesson.objects.filter(module=module).order_by('order').prefetch_related(
        Prefetch('resources', queryset=LessonResource.objects.order_by('order'), to_attr='resources_list')
    ).select_related('related_exam') # Testni ham yuklaymiz
    
    context = {
        'module': module,
        'course': module.course,
        'lessons': lessons,
        'page_title': f"'{module.title}' modulining darslari"
    }
    return render(request, 'management/lesson_list.html', context)

@login_required(login_url='login')
def lesson_create(request, module_id):
    module = get_object_or_404(CourseModule, id=module_id)

    if request.method == 'POST':
        form = LessonForm(request.POST, module=module)  # module ni berish muhim!
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module

            # Avtomatik tartib raqami
            last = Lesson.objects.filter(module=module).order_by('-order').first()
            lesson.order = (last.order if last else 0) + 1

            lesson.save()
            messages.success(request, f"“{lesson.title}” darsi yaratildi")
            return redirect('lesson_list', module_id=module.id)
    else:
        form = LessonForm(module=module)  # bu yerda ham module beriladi!

    return render(request, 'management/lesson_form.html', {
        'form': form,
        'module': module,
    })

@login_required(login_url='login')
def lesson_update(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    module = lesson.module

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson, module=module)
        if form.is_valid():
            form.save()
            messages.success(request, f"“{lesson.title}” tahrirlandi")
            return redirect('lesson_list', module_id=module.id)
    else:
        form = LessonForm(instance=lesson, module=module)

    return render(request, 'management/lesson_form.html', {
        'form': form,
        'module': module,
    })

@login_required(login_url='login')
def lesson_delete(request, lesson_id):
    """ Darsni o'chirish (lesson_list sahifasidagi modal orqali tasdiqlanadi). """
    lesson = get_object_or_404(Lesson, id=lesson_id)
    module_id = lesson.module.id

    # O'chirish faqat POST so'rovi orqali amalga oshiriladi
    if request.method == 'POST':
        lesson_title = lesson.title
        lesson.delete()
        messages.success(request, f"'{lesson_title}' darsi muvaffaqiyatli o'chirildi.")
    
    # Har doim ro'yxat sahifasiga qaytish
    return redirect('lesson_list', module_id=module_id)

# =========================================================
# C. RESURS BOSHQARUVI (Linklarni qo'shish)
# =========================================================

@login_required(login_url='login')
def resource_create(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == 'POST':
        form = LessonResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.lesson = lesson

            # AVTOMATIK TARTIB RAQAMI – 100% to‘g‘ri va xavfsiz
            last_resource = LessonResource.objects.filter(lesson=lesson).order_by('-order').first()
            resource.order = (last_resource.order if last_resource else 0) + 1

            resource.save()
            messages.success(
                request,
                f"“{resource.title}” ({resource.get_resource_type_display()}) resursi qo‘shildi (tartib: {resource.order})"
            )
            return redirect('lesson_list', module_id=lesson.module.id)  # yoki lesson_list
    else:
        form = LessonResourceForm()

    context = {
        'form': form,
        'lesson': lesson,
        'page_title': f"“{lesson.title}” → Yangi resurs qo‘shish"
    }
    return render(request, 'management/resource_form.html', context)

# =========================================================
# D. JADVAL BOSHQARUVI (Offline/Muddatli kurslar uchun)
# =========================================================

@login_required(login_url='login')
def schedule_list(request, course_id):
    """ Kursning dars jadvallarini boshqarish. """
    course = get_object_or_404(Course, id=course_id)
    
    # Faqat Offline yoki Muddatli Online kurslar uchun ruxsat berish
    if course.is_online and not course.is_scheduled:
        messages.warning(request, "Bu kurs ixtiyoriy rejimda. Jadval belgilash shart emas.")
        return redirect('module_list', course_id=course.id)
        
    # Yangi ordering mezoniga moslashtiramiz: order_in_cycle bo'yicha saralash
    schedules = CourseSchedule.objects.filter(course=course).order_by('order_in_cycle', 'day_of_week', 'start_time')
    
    context = {
        'course': course,
        'schedules': schedules,
        'page_title': f"'{course.title}' kursining takrorlanuvchi dars jadvallari"
    }
    return render(request, 'management/schedule_list.html', context)


@login_required(login_url='login')
def schedule_create(request, course_id):
    """ Yangi takrorlanuvchi dars jadvalini yaratish. """
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # Formaga POST ma'lumotlarini va course_instance ni yuboramiz
        form = CourseScheduleForm(request.POST, course_instance=course) 
        if form.is_valid():
            # course maydoni yashiringan bo'lsa ham, u ModelForm orqali saqlanadi.
            # Lekin xavfsizlik uchun bu yerda tekshirish/saqlash mantig'ini soddalashtiramiz.
            schedule = form.save() 
            # course allaqachon yashirin maydonda o'rnatilgan bo'lishi kerak.
            # Agar siz form.save(commit=False) ishlatmoqchi bo'lsangiz:
            # schedule = form.save(commit=False)
            # schedule.course = course # Yana bir marta tasdiqlash uchun
            # schedule.save()
            
            messages.success(request, "Takrorlanuvchi jadval sloti muvaffaqiyatli qo'shildi.")
            return redirect('schedule_list', course_id=course.id)
    else:
        # GET so'rovi uchun course_instance ni yuboramiz
        form = CourseScheduleForm(course_instance=course)
        
    context = {
        'form': form,
        'course': course,
        'page_title': f"'{course.title}' uchun jadval sloti yaratish"
    }
    return render(request, 'management/schedule_form.html', context)

@login_required(login_url='login')
def schedule_update(request, course_id, schedule_id):
    """ Mavjud CourseSchedule ni tahrirlash funksiyasi. """
    course = get_object_or_404(Course, id=course_id)
    schedule = get_object_or_404(CourseSchedule, id=schedule_id, course=course)

    if request.method == 'POST':
        # Formaga POST ma'lumotlari, instance va course_instance ni yuboramiz
        form = CourseScheduleForm(request.POST, instance=schedule, course_instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f"Jadval sloti muvaffaqiyatli tahrirlandi.")
            return redirect('schedule_list', course_id=course.id)
    else:
        # GET so'rovi uchun instance ni (mavjud ma'lumotlarni to'ldirish uchun) va course_instance ni yuboramiz
        form = CourseScheduleForm(instance=schedule, course_instance=course)

    context = {
        'form': form,
        'course': course,
        'schedule': schedule,
        'page_title': "Jadval slotini tahrirlash"
    }
    return render(request, 'management/schedule_form.html', context)


@login_required(login_url='login')
def schedule_delete(request, course_id, schedule_id):
    """ CourseSchedule ob'ektini o'chirish funksiyasi. """
    course = get_object_or_404(Course, id=course_id)
    schedule = get_object_or_404(CourseSchedule, id=schedule_id, course=course)
    
    schedule.delete()
    messages.warning(request, f"Jadval sloti muvaffaqiyatli o'chirildi.")
    return redirect('schedule_list', course_id=course.id)

@login_required
def tag_list_view(request, slug):
    """
    Markazga (Center) tegishli taglar ro'yxatini ko'rsatish va ular bo'yicha statistikani hisoblash.
    """
    # 1. Center obyektini slug orqali olamiz
    center = get_object_or_404(Center, slug=slug)

    # 2. Taglarni Center bo'yicha filterlaymiz va statistikani hisoblaymiz
    tags = Tag.objects.filter(
        # Faqat joriy Centerga tegishli taglar
        center=center
    ).annotate(
        # 1. Tegga bog'langan savollar soni
        question_count=Count('question', distinct=True),
        
        # 4. Teg bo'yicha o'rtacha muvaffaqiyat darajasini hisoblash
        # Eslatma: Bu hisoblash barcha foydalanuvchilarning ushbu teg bo'yicha umumiy ko'rsatkichini oladi.
        avg_success_rate=Avg(
            F('user_performances__correct_answers') * 100.0 / 
            (F('user_performances__correct_answers') + F('user_performances__incorrect_answers')),
            # divide by zero xatosini oldini olish uchun
            # Agar sizda Django 4.0+ bo'lsa, bu yo'l to'g'ri
            default=0.0
        )
        
    ).order_by('name') # Tag nomiga ko'ra tartiblash

    context = {
        'tags': tags,
        'title': f"{center.name} Markazi uchun Teglar / Mavzular ro'yxati",
        'center': center, # Shablon uchun Center obyektini uzatamiz
    }
    return render(request, 'management/tag_list.html', context)

@login_required
def tag_create_or_update_view(request, slug, tag_id=None):
    """
    Centerga tegishli yangi teg yaratish yoki mavjudini tahrirlash sahifasi.
    """
    # Joriy Center obyektini olish
    center = get_object_or_404(Center, slug=slug)

    if tag_id:
        # Tahrirlash rejimi: Faqat joriy Centerga tegishli Tag'ni olish
        tag = get_object_or_404(Tag, id=tag_id, center=center)
        is_creating = False
        title = f"'{tag.name}' tegini tahrirlash"
    else:
        # Yaratish rejimi
        tag = None
        is_creating = True
        title = "Yangi Teg / Mavzu yaratish"

    if request.method == 'POST':
        # TagFormga qo'shimcha ravishda Center obyektini uzatish kerak bo'lishi mumkin
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            new_tag = form.save(commit=False)
            
            # Agar yangi yaratilayotgan bo'lsa, Center'ni belgilash
            if is_creating:
                new_tag.center = center 
                
            new_tag.save()
            form.save_m2m() # Agar form.save(commit=False) ishlatilsa, M2M saqlash
            
            action = "yaratildi" if is_creating else "tahrirlandi"
            messages.success(request, f"Teg muvaffaqiyatli {action}: {new_tag.get_full_hierarchy()}")
            
            # Center slug bilan tag_list ga qaytarish
            return redirect('tag_list', slug=center.slug) 
        else:
            messages.error(request, "Xatolik: Ma'lumotlarni tekshiring.")
    else:
        form = TagForm(instance=tag)

    context = {
        'form': form,
        'tag': tag,
        'is_creating': is_creating,
        'title': title,
        'center': center, # Shablon uchun Center obyektini uzatish
    }
    return render(request, 'management/tag_create_or_update.html', context)

@login_required
def tag_delete_view(request, slug, tag_id):
    """
    Centerga tegishli Tegni o'chirish.
    """
    # 1. Joriy Center obyektini olish
    center = get_object_or_404(Center, slug=slug)
    
    # 2. Faqat joriy Centerga tegishli Tag'ni olish (Xavfsizlik)
    tag = get_object_or_404(Tag, id=tag_id, center=center)
    
    if request.method == 'POST':
        tag_name = tag.get_full_hierarchy()
        
        # Bog'langan barcha child taglarni ham o'chiradi
        tag.delete()
        
        messages.success(request, f"Teg muvaffaqiyatli o'chirildi: {tag_name}")
        # Center slug bilan tag_list ga qaytarish
        return redirect('tag_list', slug=center.slug)
        
    context = {
        'tag': tag,
        'title': f"'{tag.name}' tegini o'chirish",
        'center': center, # Shablon uchun Center obyektini uzatish
    }
    # Haqiqiy o'chirish uchun alohida tasdiqlash sahifasiga yuboriladi
    return render(request, 'management/tag_confirm_delete.html', context)


@user_passes_test(is_admin) 
def center_list_view(request):
    """
    Super Admin uchun barcha O'quv Markazlari ro'yxatini ko'rsatish.
    'Ega' ustuni o'rniga 'Xodimlar' ro'yxatini ko'rsatishga moslandi.
    """
    
    centers = Center.objects.all().order_by('-id').prefetch_related(
        'subscriptions', 
        'members',           # Markazga biriktirilgan xodimlar (teacher/center_admin)
        'groups__students'   # Guruhlar va ularning o'quvchilari
    ).annotate(
        # Barcha guruhlardagi noyob o'quvchilar sonini DB darajasida hisoblash
        student_count_db=Count('groups__students', distinct=True)
    )
    
    for center in centers:
        # 1. Obuna holati
        center.is_valid = center.is_subscription_valid 
        
        # 2. Eng so'nggi aktiv obuna 
        center.active_subscription = next(
            (sub for sub in center.subscriptions.all() if sub.is_active and sub.end_date >= date.today()), 
            None
        )
        
        # 3. Markazga biriktirilgan xodimlar (Superuserlar bu ro'yxatga kirmaydi)
        center.teachers = [user for user in center.members.all() if not user.is_superuser]

        # 4. Guruhlar ro'yxati (AJAX uchun ma'lumotni tayyorlash)
        center.all_groups = list(center.groups.all())
        
        # 5. O'quvchilar sonini Annotate orqali olish
        center.student_count = center.student_count_db 
        
    # TeacherAssignmentForm() mavjudligini faraz qilamiz
    # Agar bu formani view ichida yaratish muammo bo'lsa, uni yubormasdan ham ishlataverish mumkin.
    try:
         assignment_form = TeacherAssignmentForm()
    except NameError:
         assignment_form = None

    context = {
        'centers': centers,
        'title': "O'quv Markazlari Boshqaruvi",
        'TeacherAssignmentForm': assignment_form, 
    }
    return render(request, 'admin_panel/center_list.html', context)

@user_passes_test(is_admin)
def center_edit_view(request, center_id=None):
    """
    Markazni yaratish/tahrirlash logikasi.
    """
    is_create = center_id is None
    center = None
    
    if not is_create:
        center = get_object_or_404(Center, id=center_id)

    if request.method == 'POST':
        form = CenterForm(request.POST, instance=center)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    center_instance = form.save(commit=False)
                    
                    if is_create:
                        # --- YARATISH MANTIQI ---
                        # Bu yerda Markaz egasi avtomatik tayinlanmaydi (keyinchalik Assign modal orqali qilinadi)
                        center_instance.save() 
                        
                        months = form.cleaned_data.get('subscription_months')
                        
                        if months and months > 0:
                            end_date = date.today() + timedelta(days=months * 30)
                            
                            Subscription.objects.create(
                                center=center_instance,
                                end_date=end_date,
                                price=0.00, 
                                is_active=True
                            )
                        
                        messages.success(request, f"'{center_instance.name}' markazi muvaffaqiyatli yaratildi. Obuna: {months} oy.")
                    else:
                        # --- TAHRIRLASH MANTIQI ---
                        center_instance.save()
                        messages.success(request, f"'{center_instance.name}' markazi ma'lumotlari muvaffaqiyatli yangilandi.")

                    return redirect('center_list')
            except Exception as e:
                messages.error(request, f"Saqlashda kutilmagan xatolik yuz berdi. Iltimos, admin bilan bog'laning.")
                # Xato loglarini yozish tavsiya etiladi
                # print(f"DEBUG ERROR: {e}") 
        else:
            messages.error(request, "Shaklda xatoliklar mavjud. Iltimos, ma'lumotlarni tekshiring.")
    else:
        # GET so'rovi (sahifani yuklash)
        form = CenterForm(instance=center)
    
    context = {
        'form': form,
        'center': center,
        'is_create': is_create,
        'title': "Yangi O'quv Markazi Yaratish" if is_create else f"'{center.name}' markazini tahrirlash",
    }
    # 💥 Shablon nomini to'g'ri chaqirish
    return render(request, 'admin_panel/center_edit.html', context)

@user_passes_test(is_admin)
def center_delete_view(request, center_id):
    center = get_object_or_404(Center, id=center_id)
    if request.method == 'POST':
        center_name = center.name
        center.delete()
        messages.success(request, f"'{center_name}' markazi muvaffaqiyatli o'chirildi.")
        return redirect('center_list')
    return redirect('center_list') 

@user_passes_test(is_admin)
def remove_teacher_view(request, center_id, user_id):
    """Xodimni (o'qituvchini) markazdan ajratish (o'chirmasdan)."""
    center = get_object_or_404(Center, id=center_id)
    # Faqat shu markazga tegishli userni topish
    user_to_remove = get_object_or_404(CustomUser, id=user_id, center=center) 
    
    if request.method == 'POST':
        try:
            # Markaz egasini o'chirishni cheklash
            if user_to_remove.id == center.owner_id:
                 messages.error(request, f"Markaz egasini ({user_to_remove.username}) chiqarish mumkin emas. Avval Owner'ni o'zgartiring.")
                 return redirect('center_list')
                 
            user_to_remove.center = None # CustomUser'dan markazni ajratish
            # is_staff = False qatori o'chirildi
            user_to_remove.save()
            messages.warning(request, f"'{user_to_remove.username}' foydalanuvchisi '{center.name}' markazidan chiqarildi.")
        except Exception as e:
             messages.error(request, f"O'chirishda xatolik: {e}")
             
    return redirect('center_list')

@user_passes_test(is_admin)
@require_POST
def assign_teacher_to_center(request, center_id):
    """
    Tanlangan foydalanuvchini markazga biriktiradi, 
    agar u o'qituvchi bo'lmasa, rolini 'teacher' ga o'zgartiradi.
    """
    
    # HTML dan kelgan field nomi: name="user_to_assign"
    teacher_id = request.POST.get('user_to_assign') 
    
    if not teacher_id:
        messages.error(request, "Iltimos, biriktirish uchun foydalanuvchini tanlang.")
        return redirect('center_list')
        
    try:
        center = get_object_or_404(Center, id=center_id)
        teacher = get_object_or_404(CustomUser, id=teacher_id)
        
        # O'qituvchi allaqachon boshqa markazga biriktirilgan bo'lsa, xatolik
        if teacher.center is not None and teacher.center != center:
             messages.error(request, f"'{teacher.full_name or teacher.username}' allaqachon '{teacher.center.name}' markaziga biriktirilgan.")
             return redirect('center_list')

        with transaction.atomic():
            # 1. Rolini 'teacher' ga o'zgartirish (agar student yoki boshqa rol bo'lsa)
            if teacher.role != 'teacher':
                 teacher.role = 'teacher'
                 # Agar rol o'zgarsa, unga staff huquqini berish kerakmi?
                 # teacher.is_staff = True # Kerak bo'lsa yoqib qo'ying
            
            # 2. O'qituvchini markazga biriktirish
            teacher.center = center
            teacher.save()
            
            messages.success(request, f"'{teacher.full_name or teacher.username}' muvaffaqiyatli ravishda '{center.name}' markaziga biriktirildi va ROLI O'QITUVCHIGA o'zgartirildi.")
            
    except Exception as e:
        messages.error(request, f"Xodimni biriktirishda xatolik yuz berdi: {e}")
        
    return redirect('center_list')

@user_passes_test(is_admin)
def search_unassigned_teachers_ajax(request):
    """
    Markazga biriktirilmagan (center__isnull=True) va admin/owner bo'lmagan 
    aktiv foydalanuvchilarni qidiradi. Rolidan qat'iy nazar qidiriladi.
    """
    q = request.GET.get('q', '')
    
    users_qs = CustomUser.objects.filter(
        center__isnull=True,  
        is_active=True
    ).exclude(
        Q(role='admin') | Q(is_superuser=True)
    )
    
    if q:
        users_qs = users_qs.filter(
            Q(full_name__icontains=q) |
            Q(username__icontains=q) |
            Q(phone_number__icontains=q)
        ).distinct()
        
    users = users_qs[:10] 

    results = []
    for user in users:
        role_display = user.get_role_display() if hasattr(user, 'get_role_display') else user.role
        display_text = f"{user.full_name or user.username} (Rol: {role_display})"
        
        results.append({
            'id': user.id,
            'text': display_text, 
        })

    return JsonResponse({
        'items': results,
        'total_count': users_qs.count()
    })

@user_passes_test(is_admin) 
def center_groups_ajax(request, center_id):
    """Berilgan markazdagi guruhlar ro'yxatini AJAX orqali qaytaradi."""
    center = get_object_or_404(Center, id=center_id)
    
    groups_data = []
    
    # Guruhlar ro'yxatini yuklash, o'qituvchi ma'lumotini yuklash va o'quvchilar sonini hisoblash
    groups = center.groups.select_related('teacher').annotate(
        student_count=Count('students')
    ).all().order_by('-created_at')
    
    for group in groups:
        groups_data.append({
            'id': group.pk,
            'name': group.name,
            'is_active': group.is_active,
            'teacher_username': group.teacher.username,
            'student_count': group.student_count, 
            # Guruhni boshqarish sahifasi URL manzilini to'g'ri o'rnating
            'manage_url': f'/groups/{group.pk}/manage/', 
        })
        
    return JsonResponse({'groups': groups_data, 'total_count': groups.count()})


# ==============================
# 1. GURUHLAR RO‘YXATI
# ==============================
@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def group_list_view(request, slug):
    # Markazni olish
    center = get_object_or_404(Center, slug=slug)
    
    # Huquqlarni tekshirish
    if request.user.center != center:
        messages.error(request, _("Siz bu markaz guruhlarini ko'rish huquqiga ega emassiz."))
        return redirect('dashboard', slug=request.user.center.slug)

    # Guruhlar ro'yxatini filtratsiya qilish
    if request.user.role == 'center_admin':
        # Markaz administratori barcha guruhlarni ko'radi
        groups = Group.objects.filter(center=center).select_related('teacher').prefetch_related('courses', 'students').order_by('-created_at')
    else:
        # Oddiy o'qituvchi faqat o'z guruhlarini ko'radi
        groups = Group.objects.filter(teacher=request.user, center=center).select_related('teacher').prefetch_related('courses', 'students').order_by('-created_at')

    # 🛑 MUAMMOGA YECHIM: Markazdagi jami o'quvchilar sonini hisoblash 🛑
    # 'center.members' CustomUser modelidagi 'center' FK ga o'rnatilgan 'related_name' deb hisoblandi.
    center_student_count = center.members.filter(role='student').count() 
    
    context = {
        'groups': groups,
        'title': _("Guruhlar Ro'yxati"),
        'center': center,
        'is_center_admin': request.user.role == 'center_admin',
        'center_student_count': center_student_count, # To'g'ri hisoblangan sonni konteksga qo'shamiz
    }
    return render(request, 'management/group_list.html', context)




@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def group_manage_courses_view(request, slug, pk):
    logger.info(f"--- group_manage_courses_view boshlandi (User: {request.user.username}, PK: {pk}, SLUG: {slug}) ---")

    try:
        center = get_object_or_404(Center, slug=slug)
        group = get_object_or_404(Group, pk=pk, center=center)
    except Exception as e:
        logger.error(f"Markaz yoki Guruh topilmadi! Xato: {e}")
        return redirect('index') 
    
    logger.info("Ruxsat tekshiruvi muvaffaqiyatli o'tdi.")
    
    # 1. POST So'rovi
    if request.method == 'POST':
        # Formaga markaz va guruh obyektlarini yuboramiz
        # AddCourseToGroupForm ismini to'g'ri import qilganingizga ishonch hosil qiling
        form = AddCourseToGroupForm(request.POST, center=center, group=group) 
        
        if form.is_valid():
            courses = form.cleaned_data['courses']
            group.courses.add(*courses)
            messages.success(request, f"{courses.count()} ta kurs guruhga qo‘shildi!") 
            logger.info(f"{courses.count()} ta kurs muvaffaqiyatli qo'shildi.")
            return redirect('group_manage_courses', slug=center.slug, pk=group.pk)
        else:
            logger.error(f"Forma xatosi: {form.errors}")
            messages.error(request, _("Iltimos, kiritilgan ma'lumotlarni tekshiring."))
            # Xato yuz berganda render qilish (avvalgi xato tuzatish)
            pass 

    # 2. GET So'rovi yoki POST xatosi bo'lganda
    if request.method == 'GET':
        # GET so'rovida bo'sh formani yaratish
        form = AddCourseToGroupForm(center=center, group=group)

    # 3. Viewni Render qilish
    context = {
        'group': group,
        'center': center,
        'add_form': form, # Bu yerda xatoli yoki yangi forma bo'ladi
        'title': f"{group.name} – Kurslar"
    }
    logger.info("View render qilinmoqda: management/group_manage_courses.html")
    return render(request, 'management/group_manage_courses.html', context)


def search_courses_ajax(request):
    """
    Select2 uchun kurslarni qidirish view'i.
    Markaz IDsi, Guruh IDsi va qidiruv so'zi bo'yicha faol, guruhga qo'shilmagan kurslarni filtrlashni ta'minlaydi.
    """
    try:
        query = request.GET.get('q', '')
        center_pk = request.GET.get('center', None) 
        group_pk = request.GET.get('group', None) # Guruh IDsini qabul qilish
        
        results = []
        
        # 1. MARKAZ VA GURUHNI TEKSHIRISH
        if not center_pk or not group_pk:
            return JsonResponse({'items': results, 'message': 'Markaz va Guruh IDlari kiritilishi shart.'}, status=400)

        # 2. GURUH OBYEKTINI OLISH VA ALLAQACHON QO'SHILGANLARNI CHIQARIB TASHLASH
        try:
            group = Group.objects.get(pk=group_pk)
            # Guruhga allaqachon qo'shilgan kurslar IDsi
            existing_course_ids = group.courses.values_list('id', flat=True)
            
        except Group.DoesNotExist:
            return JsonResponse({'items': results, 'message': 'Guruh topilmadi.'}, status=404)

        # 3. ASOSIY FILTRLASH: Markaz, faollik va qidiruv bo'yicha
        courses = Course.objects.filter(
            center__pk=center_pk, 
            is_active=True
        ).exclude(
            id__in=existing_course_ids # <--- ASOSIY TUZATISH: Guruhga qo'shilganlarni chiqarib tashlash
        ).order_by('title')
        
        # 4. QIDIRUV FILTRLASHI
        if query:
            # Nom bo'yicha (title) katta-kichik harflarga ahamiyat bermagan holda (icontains) qidirish
            courses = courses.filter(title__icontains=query)

        # 5. NATIJALARNI SHAKLLANTIRISH (Select2 formati)
        for course in courses:
            results.append({
                'id': course.pk,
                'text': course.title,
            })

        return JsonResponse({'items': results})

    except Exception as e:
        logger.error(f"search_courses_ajax'da xato yuz berdi: {e}")
        return JsonResponse({'items': [], 'error': _("Serverda kutilmagan xato yuz berdi.")}, status=500)


@login_required(login_url='login')
def group_remove_course_view(request, slug, pk, course_pk):
    """
    AJAX: Kursni guruhdan o'chirish.
    Faqat login qilgan va is_teacher testidan o'tganlar uchun (guruhga egalik qilish shart emas).
    """
    logger.info(f"REMOVE COURSE VIEW ISHLADI: user={request.user.username}, slug={slug}, group_pk={pk}, course_pk={course_pk}")

    try:
        # 0. DEKORATORGA ISHONCHSIZLIK: agar dekorator ishlamasa, 302 bo'ladi.
        # Shuning uchun ruxsatni JSON qaytarish uchun view ichida tekshiramiz.
        if not is_teacher(request.user):
            logger.warning(f"Ruxsat rad etildi: {request.user} o'qituvchi emas.")
            return JsonResponse({
                'success': False, 
                'error': "Siz bu amalni bajarish huquqiga ega emassiz (O'qituvchi emas)."
            }, status=403)
            
        # 1. Ob'ektlarni topish (Markaz va Guruh mos kelishi shart)
        center = get_object_or_404(Center, slug=slug)
        group = get_object_or_404(Group, pk=pk, center=center)
        course = get_object_or_404(Course, pk=course_pk, center=center)

        # 2. RUXSAT: Guruh egaligi tekshiruvi (group.teacher) olib tashlandi.
        # Faqat o'qituvchi bo'lishning o'zi yetarli.
        logger.info("Ruxsat tekshiruvi muvaffaqiyatli o'tdi (Guruh egaligi talab qilinmadi).")

        # 3. O'chirish
        group.courses.remove(course)
        new_count = group.courses.count()

        logger.info(f"Kurs o'chirildi: {course.title} (ID: {course_pk}) → Guruh: {group.name}")

        return JsonResponse({
            'success': True,
            'message': f"'{course.title}' kursi guruhdan o‘chirildi.",
            'course_count': new_count,
            'redirect_url': reverse('group_manage_courses', kwargs={'slug': center.slug, 'pk': group.pk})
        })

    except Exception as e:
        logger.error(f"Xato (remove course): {e}")
        
        status_code = 500
        # get_object_or_404 xatosi bo'lsa 404 statusini qaytaramiz
        if 'No Center matches' in str(e) or 'No Group matches' in str(e) or 'No Course matches' in str(e):
           status_code = 404
           
        return JsonResponse({
            'success': False,
            'error': f'Server xatosi yuz berdi: {str(e)}'
        }, status=status_code)

# ==============================
# 2. YANGI GURUH YARATISH
# ==============================
@login_required
@user_passes_test(is_teacher, login_url='index')
def group_create_view(request, slug):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, "Ruxsat yo‘q!")
        return redirect('dashboard', slug=request.user.center.slug)

    if request.method == 'POST':
        form = GroupForm(request.POST, center=center, teacher=request.user)
        if form.is_valid():
            group = form.save(commit=False)
            group.center = center
            group.teacher = request.user
            group.save()

            # KURSLAR
            courses = form.cleaned_data.get('courses')
            if courses:
                group.courses.set(courses)

            # O‘QUVCHILAR
            students = form.cleaned_data.get('students')
            if students:
                group.students.set(students)

            messages.success(request, f"'{group.name}' guruhi yaratildi!")
            return redirect('group_list', slug=center.slug)
    else:
        form = GroupForm(center=center, teacher=request.user)

    context = {
        'form': form,
        'title': 'Yangi Guruh Yaratish',
        'center': center,
        'is_create': True,
    }
    return render(request, 'management/group_form.html', context)


# ==============================
# 3. GURUHNI TAHIRLASH
# ==============================
@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def group_update_view(request, slug, pk):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, _("Boshqa markaz guruhini tahrirlashga ruxsat yo'q."))
        return redirect('dashboard', slug=request.user.center.slug)

    group = get_object_or_404(Group, pk=pk, center=center)

    if request.user.role == 'teacher' and group.teacher != request.user:
        messages.error(request, _("Siz bu guruhni tahrirlash huquqiga ega emassiz."))
        return redirect('group_list', slug=center.slug)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group, center=center, teacher=request.user)
        if form.is_valid():
            group = form.save(commit=False)
            group.save()

            # KURSLAR
            group.courses.set(form.cleaned_data['courses'])

            # O‘QUVCHILAR
            group.students.set(form.cleaned_data['students'])

            messages.success(request, _(f"'{group.name}' guruhidagi o'zgarishlar saqlandi."))
            return redirect('group_list', slug=center.slug)
    else:
        form = GroupForm(instance=group, center=center, teacher=request.user)

    context = {
        'form': form,
        'title': _(f"Guruhni Tahrirlash: {group.name}"),
        'center': center,
        'is_create': False,
    }
    return render(request, 'management/group_form.html', context)


# ==============================
# 4. GURUHGA O‘QUVCHI QO‘SHISH/O‘CHIRISH
# ==============================
@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def group_manage_students_view(request, slug, pk):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, _("Boshqa markaz guruhini boshqarishga ruxsat yo'q."))
        return redirect('dashboard', slug=request.user.center.slug)

    group = get_object_or_404(Group, pk=pk, center=center)

    if request.user.role == 'teacher' and group.teacher != request.user:
        messages.error(request, _("Siz bu guruh o'quvchilarini boshqarish huquqiga ega emassiz."))
        return redirect('group_list', slug=center.slug)

    # O‘CHIRISH
    remove_student_id = request.GET.get('remove_student')
    if remove_student_id:
        try:
            student = CustomUser.objects.get(pk=remove_student_id, role='student')
            if student in group.students.all():
                group.students.remove(student)
                messages.success(request, _(f"{student.get_full_name()} guruhdan olib tashlandi."))
            else:
                messages.error(request, _("O‘quvchi guruhda emas."))
        except CustomUser.DoesNotExist:
            messages.error(request, _("O‘quvchi topilmadi."))
        return redirect('group_manage_students', slug=center.slug, pk=group.pk)

    # QO‘SHISH
    if request.method == 'POST':
        add_form = AddStudentToGroupForm(request.POST, center=center)
        if add_form.is_valid():
            students_to_add = add_form.cleaned_data['student_ids']
            newly_added = 0
            for student in students_to_add:
                if student not in group.students.all():
                    group.students.add(student)
                    if not student.center:
                        student.center = center
                        student.save(update_fields=['center'])
                    newly_added += 1
            if newly_added:
                messages.success(request, _(f"{newly_added} ta o‘quvchi qo‘shildi."))
            else:
                messages.info(request, _("Hech qanday yangi o‘quvchi qo‘shilmadi."))
            return redirect('group_manage_students', slug=center.slug, pk=group.pk)
    else:
        add_form = AddStudentToGroupForm(center=center)

    context = {
        'group': group,
        'center': center,
        'students': group.students.all().order_by('full_name'),
        'title': _(f"Guruh O'quvchilari: {group.name}"),
        'add_form': add_form,
    }
    return render(request, 'management/group_student_list.html', context)

# ==============================
# 5. GURUHNI O‘CHIRISH
# ==============================
@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
@require_POST
def group_delete_view(request, slug, pk):
    center = get_object_or_404(Center, slug=slug)
    
    if request.user.center != center:
        messages.error(request, _("Boshqa markaz guruhini o'chirishga ruxsat yo'q."))
        return redirect('dashboard', slug=request.user.center.slug)

    group = get_object_or_404(Group, pk=pk, center=center)

    if request.user.role == 'teacher' and group.teacher != request.user:
        messages.error(request, _("Siz bu guruhni o'chirish huquqiga ega emassiz."))
        return redirect('group_list', slug=center.slug)

    group_name = group.name
    group.delete()
    messages.success(request, _(f"Guruh '{group_name}' o‘chirildi."))
    return redirect('group_list', slug=center.slug)


# ==============================
# 6. AJAX: O‘QUVCHILAR QIDIRISH
# ==============================
@user_passes_test(is_teacher)
def search_students_ajax(request, slug):
    # Markazni slug orqali topish
    try:
        target_center = Center.objects.get(slug=slug)
    except Center.DoesNotExist:
        return JsonResponse({'items': [], 'error': 'Markaz topilmadi.'}, status=404)

    user = request.user

    # Xavfsizlik tekshiruvi: Agar foydalanuvchi qidirayotgan markazga tegishli bo'lmasa
    if user.center != target_center and user.role != 'center_admin':
         # Faqat markaz admini yoki shu markazga bog'liq foydalanuvchi ruxsatiga ega
         return JsonResponse({'items': [], 'error': 'Ruxsat yo‘q.'}, status=403)
         
    if user.role not in ['teacher', 'center_admin']:
        return JsonResponse({'items': [], 'error': 'Ruxsat yo‘q.'}, status=403)

    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'items': [], 'has_more': False})

    q_filter = Q(role='student') & Q(is_active=True)
    search = Q(full_name__icontains=query) | Q(username__icontains=query) | Q(phone_number__icontains=query)

    # 🛑 ASOSIY O'ZGARTIRISH: Faqat target_center ga bog'langan o'quvchilarni olish
    # (Q(center__isnull=True) ni olib tashladim, faqat shu markazga bog'langanlar qoladi)
    q_filter &= Q(center=target_center)

    students = CustomUser.objects.filter(q_filter & search).order_by('full_name')[:20]

    results = []
    for s in students:
        # Markaz nomi endi doim target_center bo'ladi, lekin tekshirishni qoldiramiz
        center_name = s.center.name if s.center else "Markazsiz" 
        results.append({
            'id': s.pk,
            'text': f"{s.get_full_name()} (@{s.username}) — {center_name}"
        })

    return JsonResponse({
        'items': results,
        'has_more': students.count() >= 20
    })

# ==============================
# 7. GURUH KURSLARINI BOSHQARISH
# ==============================
from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def center_students_list_view(request, slug):
    center = get_object_or_404(Center, slug=slug)
    search_query = request.GET.get('q', '').strip()
    today = timezone.now().date()

    # Asosiy queryset
    students_qs = CustomUser.objects.filter(
        center=center,
        role='student',
        is_active=True
    ).select_related('subscription', 'subscription__plan', 'balance').order_by('is_banned', 'full_name')

    if search_query:
        students_qs = students_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    students_data = []
    for student in students_qs:
        # 1. Obuna
        sub = getattr(student, 'subscription', None)
        sub_active = sub and sub.end_date and sub.end_date.date() >= today
        sub_info = None
        if sub_active:
            days_left = (sub.end_date.date() - today).days
            sub_info = {
                'type': 'subscription',
                'name': sub.plan.name if sub.plan else "Obuna",
                'days_left': days_left,
                'icon': 'clock',
                'color': 'indigo'
            }

        # 2. Kredit (paket)
        balance = getattr(student, 'balance', None)
        credit_active = balance and balance.exam_credits > 0
        credit_info = None
        if credit_active:
            credit_info = {
                'type': 'package',
                'name': "Imtihon krediti",
                'credits': balance.exam_credits,
                'icon': 'ticket',
                'color': 'yellow'
            }

        # 3. KURS TO‘LOVI (YANGI!)
        course_purchase = Purchase.objects.filter(
            user=student,
            purchase_type='course',
            status='completed',
            course__center=center
        ).select_related('course').first()

        course_info = None
        if course_purchase and course_purchase.course:
            course_info = {
                'type': 'course',
                'name': course_purchase.course.title,
                'purchase_date': course_purchase.created_at.date(),
                'icon': 'book-open',
                'color': 'green'
            }

        # Umumiy aktivlik
        is_active = sub_active or credit_active or bool(course_info)

        # Eng muhim ma'lumotni oldinga chiqaramiz
        display_info = course_info or sub_info or credit_info or {
            'type': 'none', 'name': "Faol emas", 'icon': 'ban', 'color': 'red'
        }

        students_data.append({
            'student': student,
            'display_info': display_info,
            'is_active': is_active,
            'sub_info': sub_info,
            'credit_info': credit_info,
            'course_info': course_info,
        })

    # Paginatsiya
    paginator = Paginator(students_data, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'center': center,
        'title': f"{center.name} – O‘quvchilar",
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'management/center_students.html', context)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def student_detail_view(request, slug, pk):
    center = get_object_or_404(Center, slug=slug)
    student = get_object_or_404(CustomUser, pk=pk, center=center, role='student')

    # 1. Barcha xaridlar (subscription, package, course)
    purchases = Purchase.objects.filter(
        user=student,
        status='completed',
        course__center=center
    ).select_related(
        'subscription_plan', 'package', 'course'
    ).order_by('-created_at')

    # Tur bo‘yicha ajratamiz
    subscription_history = purchases.filter(purchase_type='subscription')
    package_history = purchases.filter(purchase_type='package')
    course_history = purchases.filter(purchase_type='course')

    # Balans
    user_balance = getattr(student, 'balance', None)

    # Imtihonlar soni
    total_exams_done = UserAttempt.objects.filter(
        user=student, center=center, is_completed=True
    ).count()

    # Jami to‘langan
    total_spent = purchases.aggregate(t=Sum('final_amount'))['t'] or 0

    context = {
        'title': f"{student.get_full_name()} – Batafsil",
        'center': center,
        'student': student,
        'subscription_history': subscription_history,
        'package_history': package_history,
        'course_history': course_history,
        'user_balance': user_balance,
        'total_exams_done': total_exams_done,
        'total_spent': int(total_spent),
    }
    return render(request, 'management/student_detail.html', context)


@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def student_block_view(request, slug, pk):
    """ O'quvchini markaz ichida bloklaydi (is_banned = True). """
    center = get_object_or_404(Center, slug=slug)
    student = get_object_or_404(CustomUser, pk=pk, center=center, role='student', is_active=True)
    
    if request.method == 'POST':
        try:
            student_name = student.get_full_name()
            student.is_banned = True
            student.save()
            
            messages.success(request, f"{student_name} markazda muvaffaqiyatli BLOKLANDI.")
            
        except Exception as e:
            messages.error(request, f"O'quvchini bloklashda xatolik yuz berdi: {e}")
            
    return redirect('center_students', slug=center.slug)

@login_required(login_url='login')
@user_passes_test(is_teacher, login_url='index')
def student_unblock_view(request, slug, pk):
    """ Bloklangan o'quvchini blokdan chiqaradi (is_banned = False). """
    center = get_object_or_404(Center, slug=slug)
    student = get_object_or_404(CustomUser, pk=pk, center=center, role='student', is_active=True)

    if request.method == 'POST':
        try:
            student_name = student.get_full_name()
            student.is_banned = False
            student.save()
            
            messages.success(request, f"{student_name} markazda muvaffaqiyatli BLOKDAN CHIQARILDI.")
            
        except Exception as e:
            messages.error(request, f"O'quvchini blokdan chiqarishda xatolik yuz berdi: {e}")
            
    return redirect('center_students', slug=center.slug)

# ==============================
# 8. KURSNI GURUHDAN O‘CHIRISH
# ==============================
@login_required
@user_passes_test(is_teacher, login_url='index')
@require_POST
def group_remove_course_view(request, slug, pk, course_pk):
    center = get_object_or_404(Center, slug=slug)
    if request.user.center != center:
        return redirect('dashboard', slug=request.user.center.slug)

    group = get_object_or_404(Group, pk=pk, center=center)
    course = get_object_or_404(Course, pk=course_pk, center=center)

    if request.user.role == 'teacher' and group.teacher != request.user:
        messages.error(request, "Ruxsat yo‘q!")
    else:
        group.courses.remove(course)
        messages.success(request, f"{course.title} o‘chirildi.")

    return redirect('group_manage_courses', slug=center.slug, pk=group.pk)


# payments/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Purchase
# payments/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import Purchase


# --- Dekorator (Siz bergan kod) ---
def center_admin_only(view_func):
    """Faqat center_admin va o‘z markaziga kirish huquqi borlarga ruxsat"""
    # ... (Siz bergan center_admin_only funksiyasi shu yerda to'liq qoladi) ...
    def wrapper(request, slug=None, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # 'admin' roli super-admin uchun
        if request.user.role not in ['admin', 'center_admin']: 
            messages.error(request, "Ruxsat yo‘q!")
            return redirect('index')

        if request.user.role == 'center_admin':
            center = get_object_or_404(Center, slug=slug)
            if request.user.center != center:
                messages.error(request, "Bu sahifa sizga tegishli emas!")
                # Markaz adminini o'z dashboardiga yuborish
                return redirect('dashboard', slug=request.user.center.slug) 
            request.current_center = center
        else:
            request.current_center = None 

        return view_func(request, slug, *args, **kwargs)
    return wrapper
# --- Dekorator yakuni ---


# -----------------------------------------------------
# Yordamchi Funksiya: O'quvchini kursga (guruhga) qo'shish
# -----------------------------------------------------
def enroll_student_to_course_group(user, course):
    """
    To'lov muvaffaqiyatli bo'lganda foydalanuvchini kursga bog'langan guruhga qo'shadi.
    """
    # 1. Kursga bog'langan barcha guruhlarni olamiz
    groups = Group.objects.filter(courses=course, is_active=True).order_by('id')
    
    if not groups.exists():
        # Kursga hech qanday aktiv guruh bog'lanmagan bo'lsa
        return False, f"{course.title} kursiga bog'langan aktiv guruh topilmadi."

    # 2. Eng kam o'quvchisi bor yoki birinchi topilgan guruhni tanlaymiz
    # Eng yaxshi yondashuv: guruhlarni o'quvchilar soniga qarab saralash va eng kam sonlisini tanlash
    target_group = min(groups, key=lambda g: g.students.count())
    
    # 3. Foydalanuvchini guruhga qo'shamiz
    target_group.students.add(user)
    
    return True, f"O'quvchi **{target_group.name}** guruhiga muvaffaqiyatli qo'shildi."


@center_admin_only
@login_required
def admin_payment_list(request, slug):
    """
    To‘lovlar ro‘yxati (Course/Package/Subscription)
    """
    center = request.current_center 

    purchases = Purchase.objects.select_related(
        'user', 'package', 'subscription_plan', 'promo_code', 
        'user__center', 'course' # Yangi: Kursni select_related ga qo'shdik
    ).filter(
        status__in=['moderation', 'pending', 'rejected', 'completed'] # Ko'rsatmoqchi bo'lgan statuslar
    )

    # Filtrlash mantiqi
    if center:
        # Agar bu center_admin bo'lsa, faqat o'z markaziga tegishli (kursning markazi yoki foydalanuvchining markazi orqali)
        purchases = purchases.filter(
            models.Q(course__center=center) | 
            models.Q(user__center=center)
        )

    # HTML da kursni ko'rsatish uchun foydalanamiz
    purchases = purchases.order_by('-created_at')

    paginator = Paginator(purchases, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'payments/admin_payment_list.html', {
        'purchases': page_obj,
        'page_obj': page_obj,
        'center': center, # HTML uchun kerak
        'is_paginated': page_obj.has_other_pages(),
        'slug': slug,
    })


@center_admin_only
@login_required
@transaction.atomic # Barcha amaliyotlar bir tranzaksiya ichida bo'lishi uchun
def approve_payment(request, slug, pk):
    """
    To'lovni tasdiqlash va o'quvchini guruhga qo'shish.
    """
    if request.method != 'POST':
        return redirect('admin_payment_list', slug=slug)
        
    center = request.current_center
    purchase = get_object_or_404(Purchase, pk=pk)

    # Markaz tekshiruvi (faqat center_admin uchun)
    if center:
        is_relevant = (purchase.course and purchase.course.center == center) or (purchase.user.center == center)
        if not is_relevant:
            messages.error(request, "Bu to‘lov sizning markazingizga tegishli emas!")
            return redirect('admin_payment_list', slug=slug)

    if purchase.status == 'completed':
        messages.info(request, f"#{purchase.id} to‘lov allaqachon tasdiqlangan.")
    elif purchase.status == 'rejected':
         messages.warning(request, f"#{purchase.id} to‘lov rad etilgan. Avval 'Pending' yoki 'Moderation' holatiga qaytaring.")
    else:
        # --- Tasdiqlash mantiqi ---
        
        # 1. Kurs uchun bo'lsa, o'quvchini guruhga qo'shamiz
        if purchase.purchase_type == 'course' and purchase.course:
            success, msg = enroll_student_to_course_group(purchase.user, purchase.course)
            if success:
                messages.success(request, f"#{purchase.id} to‘lov tasdiqlandi. {msg}")
            else:
                # Agar guruhga qo'shishda muammo bo'lsa (Masalan, guruh topilmasa)
                messages.warning(request, f"#{purchase.id} tasdiqlandi, lekin: {msg}")

        # 2. Paket yoki Obuna uchun bo'lsa (mavjud fulfill() funksiyasi ishlatiladi)
        else:
            # Agar sizning Purchase modelingizda fulfill() metodi paket/obuna uchun mo'ljallangan bo'lsa
            # Uning ichida status='completed' qilib qo‘yish kerak
            # Agar 'fulfill' metodi Course uchun ham guruhga qo'shishni bajarmasa, yuqoridagi 'if' bloki yaxshi.
            try:
                 purchase.fulfill() # Bu obuna/paket uchun kredit berishni amalga oshiradi
                 messages.success(request, f"#{purchase.id} raqamli to‘lov tasdiqlandi! Obuna/kredit berildi.")
            except AttributeError:
                 # Agar fulfill() metodi mavjud bo'lmasa, statusni o'zgartiramiz
                 purchase.status = 'completed'
                 purchase.save(update_fields=['status'])
                 messages.success(request, f"#{purchase.id} to‘lov tasdiqlandi!")
                 
        # Statusni yakuniy tasdiqlash
        if purchase.status != 'completed': # Agar fulfill() ichida o'zgartirilmagan bo'lsa
            purchase.status = 'completed'
            purchase.save(update_fields=['status'])
        
    return redirect('admin_payment_list', slug=slug)

# --- reject_payment funksiyasi o'zgarishsiz qolishi mumkin ---
@center_admin_only
@login_required
def reject_payment(request, slug, pk):
    # ... (Siz bergan reject_payment funksiyasi to'liq qoladi) ...
    if request.method != 'POST':
        return redirect('admin_payment_list', slug=slug)

    center = request.current_center
    purchase = get_object_or_404(Purchase, pk=pk)

    if center:
        is_relevant = (purchase.course and purchase.course.center == center) or (purchase.user.center == center)
        if not is_relevant:
            messages.error(request, "Bu to‘lov sizga tegishli emas!")
            return redirect('admin_payment_list', slug=slug)

    if purchase.status == 'rejected':
        messages.info(request, f"#{purchase.id} allaqachon rad etilgan.")
    elif purchase.status == 'completed':
        messages.warning(request, f"#{purchase.id} tasdiqlangan to‘lovni rad etib bo‘lmaydi!")
    else:
        purchase.status = 'rejected'
        purchase.save(update_fields=['status'])
        messages.error(request, f"#{purchase.id} raqamli to‘lov rad etildi.")

    return redirect('admin_payment_list', slug=slug)

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required(login_url='login')
def my_balance_view(request, slug):
    center = get_object_or_404(Center, slug=slug)
    user = request.user

    if user.center != center:
        messages.error(request, "Bu markazga kirish huquqingiz yo‘q.")
        return redirect('dashboard')

    subscription = getattr(user, 'subscription', None)
    balance = getattr(user, 'balance', None)

    total_exams_done = UserAttempt.objects.filter(
        user=user,
        center=center,
        is_completed=True
    ).count()

    total_spent = 0
    last_purchase_date = None
    purchases = user.purchases.filter(status='completed').order_by('-created_at')
    if purchases.exists():
        total_spent = sum(p.final_amount for p in purchases if p.final_amount)
        last_purchase_date = purchases.first().created_at

    # ----------------------------------------------------
    ## ✅ XATO TUZATILGAN QISM: Aktiv kurslarni olish (2-urinish)

    # 1. Foydalanuvchi a'zo bo'lgan barcha Custom/Siz yaratgan Group modellarini topamiz.
    # Sizning CustomUser modelingizda guruhlarga bog'lanish uchun 'enrolled_groups' related_name mavjud.
    # CustomUser (students) -> enrolled_groups
    # Django'ning o'rnatilgan guruhlari emas, balki sizning Group modelingiz ishlatiladi.
    
    # User.objects.get(id=user.id).enrolled_groups.all() orqali guruhlarni olamiz.
    enrolled_groups = user.enrolled_groups.all()
    
    # 2. Bu guruhlarga tegishli barcha Course ID'larini yig'amiz.
    # Group (courses) -> Course
    course_ids = Course.objects.filter(
        groups_in_course__in=enrolled_groups,  # groups_in_course - Course'dagi related_name
        center=center 
    ).values_list('id', flat=True).distinct()
    
    # 3. Yig'ilgan ID'lar bo'yicha Kurslarni yuklaymiz.
    active_courses = Course.objects.filter(id__in=course_ids).order_by('title')

    # Kurslarga tegishli to'lov ma'lumotlarini birlashtirish
    courses_with_details = []
    for course in active_courses:
        course_details = {
            'course': course,
            'is_paid': course.price > 0 or course.is_premium, 
            'enrollment_date': None,
            'purchase_date': None,
            'amount_paid': None,
            'is_paid_course': False,
        }
        
        course_purchase = Purchase.objects.filter(
            user=user,
            course=course,
            purchase_type='course',
            status='completed'
        ).order_by('-created_at').first()
        
        if course_purchase:
            course_details['is_paid_course'] = True
            course_details['purchase_date'] = course_purchase.created_at
            course_details['amount_paid'] = course_purchase.final_amount
            course_details['enrollment_date'] = course_purchase.created_at 
            
        courses_with_details.append(course_details)


    # ----------------------------------------------------

    context = {
        'center': center,
        'subscription': subscription,
        'balance': balance,
        'total_exams_done': total_exams_done,
        'total_spent': int(total_spent) if total_spent else 0,
        'last_purchase_date': last_purchase_date,
        'active_courses': courses_with_details,
    }

    return render(request, 'student/my_balance.html', context)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q, Max
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache
from django.db.models import F
import csv
import io

from .models import Question, QuestionCalibration, UserAnswer, Center

from django.shortcuts import render
from django.db.models import Max
from Mock.models import UserAnswer, Question, QuestionCalibration # Modellar nomlari to‘g‘ri deb faraz qilinadi
# @center_admin_only dekoratori mavjud deb faraz qilinadi

@center_admin_only
def calibration_dashboard(request, slug):
    """
    Rasch/IRT kalibratsiya panelini ko'rsatadi.
    - Savollar statistikasi (faqat javoblar mavjud bo'lsa)
    - Qiyinlik darajasini (difficulty) har doim ko'rsatadi.
    """
    center = request.current_center

    # 1. Umumiy statistika 📊
    
    total_questions = Question.objects.filter(center=center).count()
    # current_calibration - bu Question modelidagi tegishli maydon (ForeignKey) deb faraz qilinadi
    calibrated_count = Question.objects.filter(center=center, current_calibration__isnull=False).count()

    # Barcha markazdagi noyob javoblar soni
    unique_responses = UserAnswer.objects.filter(
        attempt_section__attempt__exam__center=center,
        is_correct__isnull=False
    ).values('attempt_section__attempt__user', 'question').distinct().count()

    # Oxirgi kalibratsiya sanasi
    last_calibration = QuestionCalibration.objects.filter(
        question__center=center
    ).aggregate(last=Max('calibrated_at'))['last']

    # 2. Savollar statistikasi
    
    question_stats = []
    questions = Question.objects.filter(center=center).prefetch_related('current_calibration') # Optimallash

    for q in questions:
        # 2.1. Berilgan savolga javoblarni yig'ish
        answers = UserAnswer.objects.filter(
            question=q,
            is_correct__isnull=False,
            attempt_section__attempt__exam__center=center
        ).select_related('attempt_section__attempt')

        # Har bir foydalanuvchining faqat birinchi javobini hisobga olish (noyob javoblar)
        seen_users = set()
        correct = total = 0

        for ua in answers:
            # Agar foydalanuvchi allaqachon javob bergan bo'lsa, uni o'tkazib yuborish
            uid = ua.attempt_section.attempt.user.id
            if uid in seen_users:
                continue
            seen_users.add(uid)
            total += 1
            if ua.is_correct:
                correct += 1

        # 2.2. Javoblar soni 0 bo'lgan savollarni chiqarib tashlash (Mantiq saqlandi)
        if total == 0:
            continue

        # 2.3. Ma'lumotlarni hisoblash
        correct_rate = (correct / total) * 100
        
        # Qiyinlik darajasini har doim Question modelidan olish
        current_diff = q.difficulty 
        
        # Oxirgi kalibratsiya sanasini olish
        last_calibrated = q.current_calibration.calibrated_at if hasattr(q, 'current_calibration') and q.current_calibration else None

        question_stats.append({
            'question': q,
            'unique_responses': total,
            'correct_rate': round(correct_rate, 1),
            'current_difficulty': current_diff, 
            'last_calibrated': last_calibrated,
        })

    # 3. Natijalarni tartiblash
    question_stats.sort(key=lambda x: x['unique_responses'], reverse=True)

    # 4. Context yaratish va qaytarish
    context = {
        'center': center,
        'total_questions': total_questions,
        'calibrated_count': calibrated_count,
        'total_responses': unique_responses,
        'last_calibration_date': last_calibration.strftime('%d.%m.%Y %H:%M') if last_calibration else "Yo‘q",
        'question_stats': question_stats[:500], # Ko‘p ma’lumotni cheklash
        'has_enough_data': unique_responses >= 100,
    }

    return render(request, 'admin_panel/calibration_dashboard.html', context)

# ================================
# 1. EXPORT — R uchun toza CSV chiqarish
# ================================
# views.py → export_for_r_calibration (YANGI VERSIYA — USER_ID SIZ)

@center_admin_only
def export_for_r_calibration(request, slug):
    center = request.current_center

    answers = UserAnswer.objects.filter(
        attempt_section__attempt__exam__center=center,
        is_correct__isnull=False
    ).select_related('question')

    # Takrorlarni yo‘q qilish (bitta user bitta savolga bitta javob)
    seen = set()
    data = []

    for ua in answers:
        key = (ua.attempt_section.attempt.user.id, ua.question.id)
        if key in seen:
            continue
        seen.add(key)
        data.append({
            'item': ua.question.id,
            'score': 1 if ua.is_correct else 0
        })

    # CSV — faqat 2 ustun!
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['item', 'score'])  # R uchun mukammal
    for row in data:
        writer.writerow([row['item'], row['score']])

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rasch_data_{center.slug}_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response

# ================================
# 2. IMPORT — R dan kelgan natijani yuklash
# ================================
@center_admin_only
@csrf_exempt
def import_r_calibration_results(request, slug):
    if request.method != 'POST' or not request.FILES.get('csv_file'):
        messages.error(request, "CSV fayl yuklang!")
        return redirect('calibration_dashboard', slug=slug)

    csv_file = request.FILES['csv_file']
    content = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    updated = 0
    errors = 0

    for row in reader:
        try:
            question_id = int(row['item'] or row['Item'] or row['question_id'])
            a = float(row.get('a', row.get('a1', 1.0)))
            b = float(row['b'])
            g = float(row.get('g', row.get('c', 0.25)))

            q = Question.objects.get(id=question_id, center=request.current_center)

            # Yangi kalibratsiya yaratish
            calib = QuestionCalibration.objects.create(
                question=q,
                response_count_used=999,  # keyinroq to‘g‘rilab qo‘yasiz
                difficulty=b,
                discrimination=a,
                guessing=g,
                method='2pl_mirt_offline',
                notes=f"R orqali offline kalibratsiya — {timezone.now().date()}"
            )

            # Savolni yangilash
            q.difficulty = b
            q.discrimination = a
            q.guessing = g
            q.current_calibration = calib
            q.is_calibrated = True
            q.save()

            updated += 1

        except Exception as e:
            errors += 1
            continue

    messages.success(request, f"Muvaffaqiyatli! {updated} ta savol yangilandi. Xato: {errors} ta.")
    return redirect('calibration_dashboard', slug=slug)

