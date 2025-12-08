from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.admin import GenericTabularInline
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib.auth.admin import UserAdmin 
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Max
from django.db.models import Q

from .models import (
    Center, CustomUser, Group, Subscription,
    SystemConfiguration, SiteSettings, PromoCode, ExamPackage,
    SubscriptionPlan, UserBalance, UserSubscription, Purchase,
    Tag, UserTagPerformance, Flashcard, UserFlashcardStatus, FlashcardReviewLog,
    UserFlashcardDeck, FlashcardExam, Topic, Subtopic, Passage,
    RaschDifficultyLevel, Question, QuestionSolution, AnswerOption,
    QuestionReview, Exam, ExamSection, ExamSectionOrder,
    ExamSectionStaticQuestion, UserAttempt, UserAttemptSection, UserAttemptQuestion,
    # 3-qism
    UserAnswer, UserAnswerArchive, Course, CourseModule, Lesson, LessonResource,
    CourseSchedule, UserSolutionView, Notification, Badge, UserBadge,
    LeaderboardEntry, UserMissionProgress,QuestionCalibration
)

# ========================
# INLINES
# ========================

class GroupInline(admin.TabularInline):
    model = Group
    extra = 0
    fields = ('name', 'teacher', 'is_active')
    show_change_link = True


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    readonly_fields = ('start_date',)
    fields = ('start_date', 'end_date', 'price', 'is_active')


class PromoCodeInline(admin.TabularInline):
    model = PromoCode
    extra = 0
    fields = ('code', 'discount_type', 'discount_percent', 'discount_amount',
              'valid_from', 'valid_until', 'max_uses', 'is_active')


class ExamPackageInline(admin.TabularInline):
    model = ExamPackage
    extra = 0
    fields = ('name', 'price', 'exam_credits', 'solution_view_credits_on_purchase',
              'includes_flashcards', 'is_active')


class TagInline(admin.TabularInline):
    model = Tag
    extra = 0
    fields = ('name', 'parent', 'description')
    show_change_link = True


class FlashcardInline(admin.TabularInline):
    model = Flashcard
    extra = 0
    fields = ('english_content', 'uzbek_meaning', 'content_type', 'author')
    readonly_fields = ('created_at',)


class UserFlashcardStatusInline(admin.TabularInline):
    model = UserFlashcardStatus
    extra = 0
    readonly_fields = ('last_reviewed_at', 'next_review_at')
    fields = ('flashcard', 'status', 'ease_factor', 'review_interval', 'repetition_count')


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 1
    fields = ('text', 'is_correct')


class ExamSectionOrderInline(admin.TabularInline):
    model = ExamSectionOrder
    extra = 0
    fields = ('exam_section', 'order')
    ordering = ('order',)


class ExamSectionStaticQuestionInline(admin.TabularInline):
    model = ExamSectionStaticQuestion
    extra = 0
    fields = ('question', 'question_number')
    ordering = ('question_number',)


class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0
    readonly_fields = ('answered_at', 'time_taken_seconds')
    fields = ('question', 'is_correct', 'is_marked_for_review', 'time_taken_seconds')


class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 0
    fields = ('title', 'order')
    ordering = ('order',)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ('title', 'related_exam', 'order')
    ordering = ('order',)


class LessonResourceInline(admin.TabularInline):
    model = LessonResource
    extra = 0
    fields = ('resource_type', 'title', 'link', 'order')
    ordering = ('order',)


class CourseScheduleInline(admin.TabularInline):
    model = CourseSchedule
    extra = 0
    fields = ('day_of_week', 'start_time', 'order_in_cycle', 'is_start_slot')
    ordering = ('order_in_cycle',)


class UserBadgeInline(admin.TabularInline):
    model = UserBadge
    extra = 0
    readonly_fields = ('awarded_at',)
    fields = ('badge', 'awarded_at')


class NotificationInline(GenericTabularInline):
    model = Notification
    extra = 0
    readonly_fields = ('created_at', 'is_read')
    fields = ('title', 'is_read', 'created_at')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    CustomUser modelining admin interfeysini sozlash.
    Standart UserAdmin dagi first_name, last_name kabi mavjud bo'lmagan maydonlar olib tashlandi.
    """
    
    # CustomUserAdminForm talab qilinmagani uchun olib tashlandi.
    # form = CustomUserAdminForm 

    # 1. Ma'lumotlarni o'zgartirish sahifasi uchun maydonlar to'plami (fieldsets)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_("Shaxsiy ma'lumotlar"), {'fields': (
            'full_name', 'email', 'phone_number', 'bio', 'profile_picture', 'ability'
        )}),
        (_('Markaz & Rol'), {'fields': (
            'role', 
            'center',      # ForeignKey: Endi filter_horizontal dan olib tashlandi
            'teacher',     # ForeignKey: Endi filter_horizontal dan olib tashlandi
            'is_approved', 
            'is_banned'
        )}),
        (_('Ruxsatlar'), {'fields': (
            'is_active', 
            'is_staff', 
            'is_superuser', 
            'groups', 
            'user_permissions'
        )}),
        (_('Muhim sanalar'), {'fields': ('last_login', 'date_joined')}),
    )

    # 2. Yangi foydalanuvchi qo'shish uchun maydonlar to'plami (add_fieldsets)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            # password2 UserAdmin dagi UserCreationForm tomonidan talab qilinadi
            'fields': (
                'username', 'email', 'full_name', 'password', 'password2', 
                'role', 'center', 'is_approved', 'is_banned'
            ),
        }),
    )

    # 3. List displey va filtrlash sozlamalari
    list_display = ('username', 'full_name', 'email', 'phone_number', 'is_staff', 'role', 'is_approved')
    # Bitta elementli tuplelar uchun vergul to'g'ri ishlatilgan.
    list_filter = ('role', 'is_approved', 'is_banned', 'is_staff', 'center')
    search_fields = ('username', 'email', 'full_name', 'phone_number')
    ordering = ('username',)
    
    # 4. M2M aloqalar uchun filter_horizontal: center olib tashlandi.
    filter_horizontal = ('groups', 'user_permissions',)
    
    # 5. FK aloqalar uchun raw_id_fields: Bu filter_horizontal o'rniga ishlatiladi
    # va center, teacher kabi FK maydonlarida tanlash oynasi o'rniga ID kiritish imkonini beradi.
    raw_id_fields = ('center', 'teacher',)

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'center', 'teacher', 'student_count', 'is_active')
    list_filter = ('center', 'is_active', 'teacher')
    search_fields = ('name', 'center__name', 'teacher__username')
    filter_horizontal = ('students', 'courses')

    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = _("O'quvchilar")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('center', 'start_date', 'end_date', 'price', 'is_active')
    list_filter = ('is_active', 'center')
    search_fields = ('center__name',)
    readonly_fields = ('start_date',)

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return not SystemConfiguration.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return not SiteSettings.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'center', 'discount_type', 'discount_value', 'max_uses', 'is_active', 'valid_until')
    list_filter = ('center', 'discount_type', 'is_active')
    search_fields = ('code', 'center__name')

    def discount_value(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount_percent}%"
        return f"{obj.discount_amount} so'm"
    discount_value.short_description = _("Chegirma")

@admin.register(ExamPackage)
class ExamPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'center', 'price', 'exam_credits', 'solution_view_credits_on_purchase', 'is_active')
    list_filter = ('center', 'is_active')
    search_fields = ('name', 'center__name')
    filter_horizontal = ('exams',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'includes_solution_access', 'is_active')
    list_filter = ('is_active', 'includes_solution_access')
    search_fields = ('name',)


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam_credits', 'solution_view_credits', 'updated_at')
    search_fields = ('user__username', 'user__full_name')
    readonly_fields = ('updated_at',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'auto_renewal')
    list_filter = ('plan', 'auto_renewal')
    search_fields = ('user__username', 'plan__name')

    def is_active(self, obj): return obj.is_active()
    is_active.boolean = True


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'purchase_type', 'package_or_plan', 'final_amount', 'status', 'created_at')
    list_filter = ('status', 'purchase_type', 'created_at')
    search_fields = ('user__username', 'id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_completed', 'mark_as_moderation', 'mark_as_rejected']

    def package_or_plan(self, obj):
        return obj.package.name if obj.package else (obj.subscription_plan.name if obj.subscription_plan else "-")
    package_or_plan.short_description = _("Paket/Reja")

    def mark_as_completed(self, request, queryset):
        for p in queryset.filter(status='moderation'): p.fulfill()
    mark_as_completed.short_description = _("Tasdiqlash")


# ========================
# FLASHCARD & TAG
# ========================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'center', 'get_full_hierarchy')
    list_filter = ('center', 'parent')
    search_fields = ('name', 'description')
    inlines = [TagInline]

    def get_full_hierarchy(self, obj):
        return obj.get_full_hierarchy()
    get_full_hierarchy.short_description = _("Ierarxiya")


@admin.register(UserTagPerformance)
class UserTagPerformanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'tag', 'correct_answers', 'incorrect_answers', 'success_rate', 'last_attempted_at')
    list_filter = ('tag__center', 'tag')
    search_fields = ('user__username', 'tag__name')

    def success_rate(self, obj):
        return f"{obj.success_rate():.1f}%"
    success_rate.short_description = _("Muvaffaqiyat %")


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('english_preview', 'uzbek_preview', 'content_type', 'author', 'center', 'created_at')
    list_filter = ('content_type', 'center', 'author', 'tags')
    search_fields = ('english_content', 'uzbek_meaning', 'author__username')
    filter_horizontal = ('tags', 'questions')
    inlines = [UserFlashcardStatusInline]
    readonly_fields = ('created_at',)

    def english_preview(self, obj):
        return format_html("<div style='max-width:150px'>{}</div>", obj.english_content[:60] + '...')
    english_preview.short_description = _("Inglizcha")

    def uzbek_preview(self, obj):
        return format_html("<div style='max-width:150px'>{}</div>", obj.uzbek_meaning[:60] + '...')
    uzbek_preview.short_description = _("O'zbekcha")


@admin.register(UserFlashcardStatus)
class UserFlashcardStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'flashcard', 'status', 'next_review_at', 'ease_factor', 'repetition_count')
    list_filter = ('status', 'next_review_at')
    search_fields = ('user__username', 'flashcard__english_content')


@admin.register(FlashcardReviewLog)
class FlashcardReviewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'flashcard', 'quality_rating', 'reviewed_at')
    list_filter = ('quality_rating', 'reviewed_at')
    search_fields = ('user__username', 'flashcard__english_content')
    readonly_fields = ('reviewed_at',)


@admin.register(UserFlashcardDeck)
class UserFlashcardDeckAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'center', 'flashcard_count', 'created_at')
    list_filter = ('center', 'user')
    search_fields = ('title', 'user__username')
    filter_horizontal = ('flashcards',)

    def flashcard_count(self, obj):
        return obj.flashcards.count()
    flashcard_count.short_description = _("Kartochkalar")


@admin.register(FlashcardExam)
class FlashcardExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_exam', 'center', 'flashcard_count', 'created_at')
    list_filter = ('center', 'is_exam_review')
    search_fields = ('title', 'source_exam__title')
    filter_horizontal = ('flashcards',)

    def flashcard_count(self, obj):
        return obj.flashcards.count()
    flashcard_count.short_description = _("Flashcardlar")


# ========================
# CONTENT & EXAM
# ========================

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'center', 'order')
    list_filter = ('center', 'teacher')
    search_fields = ('name', 'teacher__username')
    ordering = ('center', 'order')


@admin.register(Subtopic)
class SubtopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'topic', 'center', 'order')
    list_filter = ('center', 'topic')
    search_fields = ('name', 'topic__name')
    ordering = ('topic', 'order')


@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'center', 'created_at')
    list_filter = ('center', 'author')
    search_fields = ('title', 'content', 'author__username')


@admin.register(RaschDifficultyLevel)
class RaschDifficultyLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'center', 'min_difficulty', 'max_difficulty')
    list_filter = ('center',)
    search_fields = ('name',)

from django.contrib import admin
from django.utils.html import format_html

# ------------------------------------------------------------------
# 1. QuestionAdmin — sizning hozirgisiga faqat qo'shamiz
# ------------------------------------------------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'text_preview', 'subtopic', 'author', 'status',
        'difficulty_colored', 'is_calibrated_badge', 'response_count',
        'current_calibration_info'
    )
    list_filter = (
        'status', 'is_calibrated', 'center', 'subtopic', 'author',
        'answer_format', 'difficulty_level'
    )
    search_fields = ('text', 'id', 'author__username')
    inlines = [AnswerOptionInline, FlashcardInline]  # sizniki qoldi
    filter_horizontal = ('tags', 'flashcards')
    readonly_fields = (
        'created_at', 'updated_at', 'response_count', 'version',
        'current_calibration_preview', 'calibrations_history'
    )
    fieldsets = (
        (None, {'fields': ('text', 'image', 'passage', 'subtopic', 'center')}),
        ('Javob formati', {'fields': ('answer_format', 'correct_short_answer', 'options')}),
        ('IRT parametrlari', {'fields': ('difficulty', 'discrimination', 'guessing', 'difficulty_level')}),
        ('Kalibratsiya', {'fields': ('current_calibration_preview', 'calibrations_history'), 'classes': ('collapse',)}),
        ('Boshqa', {'fields': ('author', 'tags', 'flashcards', 'status', 'is_calibrated', 'response_count', 'created_at', 'updated_at')}),
    )

    def text_preview(self, obj):
        return format_html("<div style='max-width:300px'>{}</div>", obj.__str__())
    text_preview.short_description = "Savol"

    # Yangi: rangli qiyinlik
    def difficulty_colored(self, obj):
        if obj.difficulty is None:
            return "—"
        d = obj.difficulty
        if d <= -2.0:
            color = "#065f46"
        elif d <= -1.0:
            color = "#16a34a"
        elif d <= 0:
            color = "#84cc16"
        elif d <= 1.0:
            color = "#f59e0b"
        elif d <= 2.0:
            color = "#ea580c"
        else:
            color = "#dc2626"
        return format_html(
            '<b style="color:white;background:{};padding:4px 12px;border-radius:12px;">{:+.2f}</b>',
            color, d
        )
    difficulty_colored.short_description = "Qiyinlik"

    # Yangi: badge
    def is_calibrated_badge(self, obj):
        if obj.current_calibration:
            return format_html('<span style="background:#10b981;color:white;padding:3px 8px;border-radius:8px;font-size:10px;">Kalibrlangan</span>')
        return format_html('<span style="background:#ef4444;color:white;padding:3px 8px;border-radius:8px;font-size:10px;">Yo‘q</span>')
    is_calibrated_badge.short_description = "Kalibr."
    is_calibrated_badge.boolean = True

    # Yangi: oxirgi kalibratsiya
    def current_calibration_info(self, obj):
        if obj.current_calibration:
            url = reverse("admin:Mock_questioncalibration_change", args=[obj.current_calibration.id])
            return format_html(
                '<a href="{}" target="_blank" style="font-size:11px;color:#6366f1;">{} ↗</a>',
                url,
                obj.current_calibration.calibrated_at.strftime("%d.%m %H:%M")
            )
        return "—"
    current_calibration_info.short_description = "Oxirgi kal."

    # Admin ichida ko‘rish uchun
    def current_calibration_preview(self, obj):
        if not obj.current_calibration:
            return "Hali kalibratsiya yo‘q"
        c = obj.current_calibration
        return mark_safe(f"""
        <div style="background:#f0fdf4;padding:12px;border-radius:8px;border-left:4px solid #10b981;">
            <b>Sana:</b> {c.calibrated_at.strftime("%d.%m.%Y %H:%M")}<br>
            <b>Javoblar:</b> {c.response_count_used}<br>
            <b>Qiyinlik:</b> <big><b>{c.difficulty:+.3f}</b></big>
        </div>
        """)
    current_calibration_preview.short_description = "Hozirgi kalibratsiya"

    def calibrations_history(self, obj):
        history = obj.calibrations.order_by('-calibrated_at')[:6]
        if not history:
            return "Tarix yo‘q"
        html = "<small><ol style='margin:8px 0;padding-left:20px;'>"
        for c in history:
            html += f"<li>{c.calibrated_at.strftime('%d.%m %H:%M')} → <b>{c.difficulty:+.2f}</b> ({c.response_count_used} javob)</li>"
        html += "</ol></small>"
        return mark_safe(html)
    calibrations_history.short_description = "So‘nggi kalibratsiyalar"


# ------------------------------------------------------------------
# 2. QuestionCalibration admin — alohida sahifa
# ------------------------------------------------------------------
@admin.register(QuestionCalibration)
class QuestionCalibrationAdmin(admin.ModelAdmin):
    list_display = ('question', 'calibrated_at', 'response_count_used', 'difficulty', 'method', 'center_name')
    list_filter = ('method', 'calibrated_at', 'question__center')
    search_fields = ('question__id',)
    readonly_fields = ('question', 'calibrated_at', 'response_count_used', 'difficulty', 'discrimination', 'guessing', 'method', 'notes')
    date_hierarchy = 'calibrated_at'

    def center_name(self, obj):
        return obj.question.center.name if obj.question.center else "—"
    center_name.short_description = "Markaz"


# ------------------------------------------------------------------
# 3. CenterAdmin — sizning uslubingiz + kalibratsiya tugmasi
# ------------------------------------------------------------------
def recalibrate_selected_centers(modeladmin, request, queryset):
    """Sizning uslubingizda — sodda va aniq"""
    from .views import run_calibration_task
    from django.core.cache import cache
    import threading, time

    for center in queryset:
        task_id = f"admin_calib_{center.id}_{int(time.time())}"
        cache.set(task_id, {'status': 'running', 'progress': 0}, timeout=7200)
        threading.Thread(target=run_calibration_task, args=(center, task_id), daemon=True).start()
        messages.success(request, f"✓ {center.name} uchun kalibratsiya boshlandi!")

recalibrate_selected_centers.short_description = "Tanlangan markazlarni qayta kalibrlash (Rasch)"

@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'owner', 'is_active',
        'subscription_status', 'total_questions',
        'calibrated_count', 'last_calibration'
    )
    
    # Faqat haqiqiy maydonlar! Xato yo'q!
    list_filter = (
        'is_active',
        # 'created_at' yo'q → olib tashladik
        # Agar kerak bo'lsa, quyidagilardan birini qo‘shing:
        # 'owner', 'teachers', 'is_subscription_valid' — agar maydon bo‘lsa
    )
    
    search_fields = ('name', 'owner__username', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('teachers',)
    raw_id_fields = ('owner',)
    actions = [recalibrate_selected_centers]  # kalibratsiya tugmasi

    # Obuna holati (agar property bo‘lsa)
    def subscription_status(self, obj):
        if hasattr(obj, 'is_subscription_valid'):
            if obj.is_subscription_valid:
                return format_html('<span style="color:green;font-weight:bold;">Faol</span>')
            else:
                return format_html('<span style="color:red;">Muddati tugagan</span>')
        return format_html('<span style="color:gray;">Noma’lum</span>')
    subscription_status.short_description = "Obuna"

    def total_questions(self, obj):
        return obj.questions.count()
    total_questions.short_description = "Savollar"

    def calibrated_count(self, obj):
        return obj.questions.filter(current_calibration__isnull=False).count()
    calibrated_count.short_description = "Kalibrlangan"

    def last_calibration(self, obj):
        last = QuestionCalibration.objects.filter(question__center=obj).aggregate(m=Max('calibrated_at'))['m']
        return last.strftime("%d.%m.%Y %H:%M") if last else "—"
    last_calibration.short_description = "Oxirgi kalibr."

@admin.register(QuestionSolution)
class QuestionSolutionAdmin(admin.ModelAdmin):
    list_display = ('question', 'has_hint', 'has_solution')
    search_fields = ('question__id',)

    def has_hint(self, obj): return bool(obj.hint)
    has_hint.boolean = True
    def has_solution(self, obj): return bool(obj.detailed_solution)
    has_solution.boolean = True


@admin.register(QuestionReview)
class QuestionReviewAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('question__id', 'user__username', 'comment')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'center', 'is_subject_exam', 'passing_percentage', 'is_premium', 'is_active')
    list_filter = ('center', 'is_subject_exam', 'is_premium', 'is_active')
    search_fields = ('title', 'teacher__username')
    inlines = [ExamSectionOrderInline]
    filter_horizontal = ('sections',)


@admin.register(ExamSection)
class ExamSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'section_type', 'duration_minutes', 'max_questions', 'center')
    list_filter = ('center', 'section_type')
    search_fields = ('name',)
    inlines = [ExamSectionStaticQuestionInline]
    filter_horizontal = ('static_questions',)


@admin.register(UserAttempt)
class UserAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'center', 'started_at', 'is_completed', 'correct_percentage', 'final_total_score')
    list_filter = ('is_completed', 'center', 'exam', 'mode')
    search_fields = ('user__username', 'exam__title')
    readonly_fields = ('started_at', 'completed_at')
    inlines = []


@admin.register(UserAttemptSection)
class UserAttemptSectionAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'section', 'score', 'correct_answers_count', 'is_completed')
    list_filter = ('section', 'is_completed')
    search_fields = ('attempt__user__username', 'section__name')
    inlines = [UserAnswerInline]

@admin.register(UserAttemptQuestion)
class UserAttemptQuestionAdmin(admin.ModelAdmin):
    list_display = ('attempt_section', 'question', 'question_number')
    search_fields = ('question__id', 'attempt_section__attempt__user__username')
    ordering = ('attempt_section', 'question_number')


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt_section', 'question', 'get_user', 'is_correct', 'time_taken_seconds', 'answered_at')
    list_filter = ('is_correct', 'attempt_section__attempt__exam')
    search_fields = ('question__id', 'attempt_section__attempt__user__username')
    readonly_fields = ('answered_at', 'time_taken_seconds')

    def get_user(self, obj):
        return obj.attempt_section.attempt.user
    get_user.short_description = 'Foydalanuvchi'
    get_user.admin_order_field = 'attempt_section__attempt__user__username'  # saralash uchun


@admin.register(UserAnswerArchive)
class UserAnswerArchiveAdmin(admin.ModelAdmin):
    list_display = ('attempt_section', 'question', 'get_user', 'is_correct', 'center', 'answered_at')
    list_filter = ('center', 'is_correct')
    search_fields = ('question__id', 'attempt_section__attempt__user__username')
    readonly_fields = ('answered_at', 'time_taken_seconds')

    def get_user(self, obj):
        return obj.attempt_section.attempt.user
    get_user.short_description = 'Foydalanuvchi'
    get_user.admin_order_field = 'attempt_section__attempt__user__username'

# ========================
# COURSES
# ========================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'center', 'course_type', 'is_premium', 'price', 'is_active')
    list_filter = ('center', 'course_type', 'is_premium', 'is_active')
    search_fields = ('title', 'teacher__username')
    inlines = [CourseModuleInline, CourseScheduleInline]


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course__center',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline]
    ordering = ('course', 'order')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'related_exam', 'order', 'has_resources', 'has_exam')
    list_filter = ('module__course__center', 'related_exam')
    search_fields = ('title', 'module__title')
    inlines = [LessonResourceInline]
    ordering = ('module', 'order')


@admin.register(LessonResource)
class LessonResourceAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'resource_type', 'title', 'link_preview', 'order')
    list_filter = ('resource_type', 'lesson__module__course__center')
    search_fields = ('title', 'link', 'lesson__title')

    def link_preview(self, obj):
        return format_html('<a href="{}" target="_blank">Link</a>', obj.link)
    link_preview.short_description = _("Link")


@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'day_of_week', 'start_time', 'order_in_cycle', 'is_start_slot')
    list_filter = ('course__center', 'day_of_week')
    search_fields = ('course__title',)
    ordering = ('course', 'order_in_cycle')


# ========================
# USER INTERACTIONS
# ========================

@admin.register(UserSolutionView)
class UserSolutionViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'viewed_at', 'credit_spent')
    list_filter = ('credit_spent', 'viewed_at')
    search_fields = ('user__username', 'question__id')
    readonly_fields = ('viewed_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'trigger_type', 'center', 'exam_count', 'min_score')
    list_filter = ('center', 'trigger_type')
    search_fields = ('title',)
    inlines = [UserBadgeInline]


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'center', 'awarded_at')
    list_filter = ('center', 'badge__trigger_type')
    search_fields = ('user__username', 'badge__title')
    readonly_fields = ('awarded_at',)


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'leaderboard_type', 'week_number', 'score', 'center')
    list_filter = ('leaderboard_type', 'week_number', 'center')
    search_fields = ('user__username',)
    ordering = ('-score',)


@admin.register(UserMissionProgress)
class UserMissionProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam_attempts_completed', 'study_attempts_completed', 'highest_score', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)