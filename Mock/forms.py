from django import forms
from django.forms import modelformset_factory
from .models import *
from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.widgets import CKEditorWidget 
from django.forms import BaseInlineFormSet
from django.forms import inlineformset_factory
from django_select2.forms import Select2MultipleWidget, Select2Widget as DjangoSelect2Widget # Nom o'zgartirildi
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.forms import Select
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

form_control_class = 'shadow-sm appearance-none border border-gray-300 rounded-lg w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition'

# Select2 stilini qo'llash uchun oddiy Select vidjetining o'zgartirilgan versiyasi
class CustomSelectWidget(Select):
    def __init__(self, attrs=None):
        # 'w-full' klassini qo'shadi, lekin Select2 funksionalligini bermaydi (faqat Select2MultipleWidget/DjangoSelect2Widget beradi)
        final_attrs = {'class': 'w-full ' + (attrs.get('class', '') if attrs else ''), **(attrs or {})}
        super().__init__(attrs=final_attrs)

# Select2 vidjetlari uchun qisqa nomlar
Select2 = DjangoSelect2Widget
Select2Multiple = Select2MultipleWidget

# ======================================================================
# 1. AUTH FORMLARI
# ======================================================================

import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm

form_control_class = "shadow-md appearance-none border border-gray-300 rounded-xl w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:ring-4 focus:ring-indigo-200 focus:border-indigo-400 transition duration-200"

class SignUpForm(forms.ModelForm):
    """
    Markaziy tizim uchun ro'yxatdan o'tish formasi.
    Yangi foydalanuvchini tizimdagi asosiy markazga avtomatik biriktiradi.
    """
    password = forms.CharField(label="Parol", widget=forms.PasswordInput(attrs={'class': form_control_class, 'placeholder': '********'}))
    password_confirm = forms.CharField(label="Parolni tasdiqlang", widget=forms.PasswordInput(attrs={'class': form_control_class, 'placeholder': '********'}))

    class Meta:
        # CustomUser modelini import qilganingizga ishonch hosil qiling
        model = CustomUser 
        fields = ['full_name', 'email', 'phone_number', 'username']
        labels = {
            'full_name': "To'liq ismingiz (F.I.Sh)",
            'email': "Elektron pochta",
            'phone_number': "Telefon raqamingiz",
            'username': "Foydalanuvchi nomi (login)",
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': form_control_class, 'placeholder': 'Aliyev Vali G\'aniyevich'}),
            'email': forms.EmailInput(attrs={'class': form_control_class, 'placeholder': 'example@mail.com'}),
            'phone_number': forms.TextInput(attrs={'class': form_control_class, 'placeholder': '+998 xx xxx xx xx'}),
            'username': forms.TextInput(attrs={'class': form_control_class, 'placeholder': 'alivaliyev'}),
        }

    # =============================================================
    # TOZALASH METODLARI (Validation)
    # =============================================================

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu elektron pochta manzili bilan allaqachon ro'yxatdan o'tilgan.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Telefon raqamini tozalash (masalan, bo'sh joylarni olib tashlash)
            clean_phone = re.sub(r'[\s\-()]', '', phone)
            if CustomUser.objects.filter(phone_number=clean_phone).exists():
                raise forms.ValidationError("Bu telefon raqami bilan allaqachon ro'yxatdan o'tilgan.")
        return phone

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Bu foydalanuvchi nomi band. Boshqa nom tanlang.")
        return username

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Kiritilgan parollar bir-biriga mos kelmadi.")
        return password_confirm
    
    # =============================================================
    # SAQLASH METODI (Avtomatik Markaz Biriktirish)
    # =============================================================

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        # Markaziy Tizim Logikasi: Avtomatik ravishda Asosiy Markazni Biriktirish
        try:
            # Tizimdagi mavjud birinchi yoki asosiy markazni topish
            primary_center = Center.objects.first()
            user.center = primary_center 
        except (NameError, ObjectDoesNotExist): # Center modeli import qilinmagan yoki Center jadvali bo'sh
            user.center = None 
            
        user.role = 'student' # Barcha yangi ro'yxatdan o'tuvchilar Talaba roliga ega bo'ladi
        
        if commit:
            user.save()
            
        return user

class LoginForm(AuthenticationForm):
    """
    Markaziy tizimga moslashtirilgan kirish formasi.
    """
    username = forms.CharField(label="Foydalanuvchi nomi", widget=forms.TextInput(attrs={'class': form_control_class, 'placeholder': 'Login'}))
    password = forms.CharField(label="Parol", widget=forms.PasswordInput(attrs={'class': form_control_class, 'placeholder': '********'}))

class PasswordResetForm(forms.Form):
    """
    Faqat email so'rovini qabul qilish uchun oddiy forma.
    """
    email = forms.EmailField(
        label="Elektron pochta",
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    
class ProfileUpdateForm(forms.ModelForm):
    """Foydalanuvchi o'z profilidagi asosiy ma'lumotlarni o'zgartirishi uchun forma."""
    
    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if self.instance.email and self.instance.email.lower() != email and CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu elektron pochta manzili bilan boshqa foydalanuvchi ro'yxatdan o'tgan.")
        return email

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'bio', 'profile_picture']
        
        labels = {
            'full_name': "To'liq ism (F.I.Sh)",
            'email': "Elektron pochta",
            'bio': "O'zi haqida qisqacha",
            'profile_picture': "Profil rasmini o'zgartirish",
        }
        
        widgets = {
            'full_name': forms.TextInput(attrs={'class': form_control_class, 'placeholder': 'Ism va familiyangiz'}),
            'email': forms.EmailInput(attrs={'class': form_control_class, 'placeholder': 'Email manzilingiz'}),
            'bio': forms.Textarea(attrs={'class': form_control_class, 'rows': 4, 'placeholder': 'O\'zingiz haqingizda qisqacha ma\'lumot...'}),
            'profile_picture': forms.FileInput(attrs={'class': form_control_class}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(label="Joriy parol", widget=forms.PasswordInput(attrs={'class': form_control_class, 'autocomplete': 'current-password'}))
    new_password1 = forms.CharField(label="Yangi parol", widget=forms.PasswordInput(attrs={'class': form_control_class, 'autocomplete': 'new-password'}))
    new_password2 = forms.CharField(label="Yangi parolni tasdiqlang", widget=forms.PasswordInput(attrs={'class': form_control_class, 'autocomplete': 'new-password'}))

# ======================================================================
# 2. SAVOL VA JAVOB FORMLARI
# ======================================================================

try:
    from ckeditor.widgets import CKEditorWidget
except ImportError:
    CKEditorWidget = forms.Textarea



# ==============================================================================
# 🛠️ ANSWER OPTION FORMASI
# ==============================================================================
class AnswerOptionForm(forms.ModelForm):
    # CKEditorWidget o'rniga CKEditorUploadingWidget ishlatilmoqda
    text = forms.CharField(
        label=_("Javob varianti matni"),
        widget=CKEditorUploadingWidget(config_name='default'),
        required=True
    )
    is_correct = forms.BooleanField(required=False, label=_("To'g'ri javob"))

    class Meta:
        model = AnswerOption
        fields = ['text', 'is_correct']

    def clean_text(self):
        text = self.cleaned_data.get('text')
        if not text or not text.strip():
            raise forms.ValidationError(_("Javob varianti matni bo'sh bo'lmasligi kerak."))
        
        # 🛑 Rasm (img) tegiga va uning atributlariga ruxsat berish
        allowed_tags = bleach.ALLOWED_TAGS + ['p', 'b', 'i', 'u', 'em', 'strong', 'sup', 'sub', 'br', 'img', 'span', 'div', 'ol', 'ul', 'li', 'table', 'thead', 'tbody', 'tr', 'td', 'th']
        
        allowed_attributes = bleach.ALLOWED_ATTRIBUTES
        allowed_attributes.update({
            'img': ['src', 'alt', 'width', 'height', 'style', 'data-cke-saved-src', 'class'],
            'a': ['href', 'title', 'target', 'class', 'style'], # Linklar uchun
            '*': ['class', 'style', 'dir'], # Umumiy atributlar
        })
        
        cleaned_text = bleach.clean(
            text, 
            tags=allowed_tags, 
            attributes=allowed_attributes,
            strip=True
        )
        return cleaned_text

# ==============================================================================
# 🛠️ JAVOB VARIANTLARI FORMSETI
# ==============================================================================
# Question va AnswerOption modellari mavjud deb hisoblab yozildi
BaseAnswerOptionFormSet = inlineformset_factory(
    Question,
    AnswerOption,
    form=AnswerOptionForm,
    fields=('text', 'is_correct'),
    extra=5,
    max_num=5,
    can_delete=True
)


class AnswerOptionFormSet(BaseAnswerOptionFormSet):
    """Javob variantlari uchun maxsus formset validatsiyasi."""
    
    def clean(self):
        super().clean()
        
        if not self.instance or not self.instance.answer_format:
            return 

        answer_format = self.instance.answer_format
        
        # 1. Short Answer turida validatsiyani o'tkazib yuborish
        if answer_format == 'short_answer':
            return 
        
        # 2. Faqat Single/Multiple formatlari uchun davom etish
        if answer_format in ['single', 'multiple']:
            
            valid_forms = [
                form for form in self.forms 
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            ]
            
            valid_forms_count = len(valid_forms)
            correct_count = sum(1 for form in valid_forms if form.cleaned_data.get('is_correct', False))
            
            # 2 TA VARIANT BO'LISHI SHARTI
            if valid_forms_count < 2:
                raise forms.ValidationError(
                    _("Yagona yoki ko‘p javob formatida kamida ikkita to‘ldirilgan variant bo‘lishi shart.") 
                )
            
            # Single javob tekshiruvi (faqat 1 ta to'g'ri javob sharti)
            if answer_format == 'single':
                if correct_count != 1:
                    raise forms.ValidationError(
                        _("Yagona javob formatida faqat bitta to‘g‘ri javob tanlanishi kerak.")
                    )
            
            # Multiple javob tekshiruvi (kamida 1 ta to'g'ri javob sharti)
            if answer_format == 'multiple':
                if correct_count < 1:
                    raise forms.ValidationError(
                        _("Bir nechta javob formatida kamida bitta to‘g‘ri javob tanlanishi kerak.")
                    )


# ==============================================================================
# 🛠️ SAVOL FORMASI (QUESTION FORM) - Barcha tuzatishlar bilan
# ==============================================================================

class QuestionForm(forms.ModelForm):
    # Solution maydonlari QuestionSolution modeliga tegishli (bu formda alohida maydon sifatida)
    hint = forms.CharField(
        label=_("Yechim uchun maslahat"),
        widget=CKEditorUploadingWidget(config_name='default', attrs={'id': 'id_hint'}),
        required=False
    )
    detailed_solution = forms.CharField(
        label=_("Batafsil yechim"),
        widget=CKEditorUploadingWidget(config_name='default', attrs={'id': 'id_detailed_solution'}),
        required=False
    )

    class Meta:
        model = Question # Sizning Question modelingiz
        fields = [
            'text', 'subtopic', 'answer_format', 'passage', 'image',
            'flashcards', 'tags', 'difficulty_level', 'difficulty',
            'discrimination', 'guessing', 'status', 'is_solution_free',
            'correct_short_answer', 'center'
        ]
        widgets = {
             # CKEditorWidget o'rniga CKEditorUploadingWidget ishlatilmoqda
             'text': CKEditorUploadingWidget(config_name='default', attrs={'id': 'id_text'}),
             'answer_format': forms.Select(attrs={'class': 'w-full', 'id': 'id_answer_format'}),
             'subtopic': forms.Select(attrs={'class': 'w-full', 'id': 'id_subtopic'}),
             'passage': forms.Select(attrs={'class': 'w-full', 'id': 'id_passage'}),
             'flashcards': forms.SelectMultiple(attrs={'class': 'w-full', 'id': 'id_flashcards'}),
             'tags': forms.SelectMultiple(attrs={'class': 'w-full', 'id': 'id_tags'}),
             'difficulty_level': forms.Select(attrs={'class': 'w-full', 'id': 'id_difficulty_level'}),
             'difficulty': forms.NumberInput(attrs={
                 'class': 'w-full border rounded-md p-2',
                 'step': '0.1', 'min': '-3.0', 'max': '3.0',
                 'id': 'id_difficulty',
                 'placeholder': _('Oson: -3.0 to -1.5, O‘rta: -1.5 to 1.5, Qiyin: 1.5 to 3.0')
             }),
             'discrimination': forms.NumberInput(attrs={
                 'class': 'w-full border rounded-md p-2',
                 'step': '0.1', 'min': '0.0', 'max': '2.0',
                 'id': 'id_discrimination'
             }),
             'guessing': forms.NumberInput(attrs={
                 'class': 'w-full border rounded-md p-2',
                 'step': '0.01', 'min': '0.0', 'max': '1.0',
                 'id': 'id_guessing',
                 'placeholder': _('Multiple-choice uchun 0.0–0.2')
             }),
             'status': forms.Select(attrs={'class': 'w-full', 'id': 'id_status'}),
             'is_solution_free': forms.CheckboxInput(attrs={
                 'class': 'form-checkbox h-5 w-5 text-indigo-600',
                 'id': 'id_is_solution_free'
             }),
             'correct_short_answer': forms.TextInput(attrs={
                 'class': 'w-full border rounded-md p-2',
                 'id': 'id_correct_short_answer'
             }),
             'center': forms.HiddenInput()
            }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Centerga bog'liqlik
        if user and user.center:
            self.fields['center'].initial = user.center
            # Queryset filtering (mavjud bo'lsa, sharhni olib tashlang)
            # self.fields['subtopic'].queryset = Subtopic.objects.filter(center=user.center)
            # self.fields['tags'].queryset = Tag.objects.filter(center=user.center)
            # self.fields['flashcards'].queryset = Flashcard.objects.filter(center=user.center)
        
        # Tahrirlash rejimida QuestionSolution ni yuklash
        if self.instance and self.instance.pk:
            try:
                # QuestionSolution modeli mavjud deb hisoblandi
                solution = self.instance.solution 
                self.fields['hint'].initial = solution.hint
                self.fields['detailed_solution'].initial = solution.detailed_solution
            except Exception: # QuestionSolution.DoesNotExist:
                pass
        
        # Yangi savol uchun default IRT qiymatlarini o'rnatish
        if not self.instance.pk:
            self.fields['difficulty'].initial = -2.0 
            self.fields['discrimination'].initial = 1.0
            self.fields['guessing'].initial = 0.1
            self.fields['answer_format'].initial = 'single'

    def clean(self):
        cleaned_data = super().clean()
        
        # O'zgaruvchilarni olish
        answer_format = cleaned_data.get('answer_format')
        correct_short_answer = cleaned_data.get('correct_short_answer')
        difficulty = cleaned_data.get('difficulty')
        difficulty_level = cleaned_data.get('difficulty_level')
        guessing = cleaned_data.get('guessing')
        discrimination = cleaned_data.get('discrimination')
        center = cleaned_data.get('center')
        text = cleaned_data.get('text')
        hint = cleaned_data.get('hint') 
        detailed_solution = cleaned_data.get('detailed_solution') 
        
        # TEGlar uchun ruxsat berilgan atributlar va teglar to'plamini belgilash (Barcha tozalashlar uchun kerak)
        allowed_tags = bleach.ALLOWED_TAGS + ['p', 'b', 'i', 'u', 'em', 'strong', 'sup', 'sub', 'br', 'img', 'span', 'div', 'ol', 'ul', 'li', 'table', 'thead', 'tbody', 'tr', 'td', 'th']
        allowed_attributes = bleach.ALLOWED_ATTRIBUTES
        allowed_attributes.update({
            'img': ['src', 'alt', 'width', 'height', 'style', 'data-cke-saved-src', 'class'],
            'a': ['href', 'title', 'target', 'class', 'style'],
            '*': ['class', 'style', 'dir'],
        })

        if not center:
            raise forms.ValidationError(_("Savol markazga bog‘lanishi kerak."))
        
        
        # 1. Savol matnini tozalash (o'zgarishsiz)
        if text:
            cleaned_data['text'] = bleach.clean(
                text, 
                tags=allowed_tags, 
                attributes=allowed_attributes,
                strip=True
            )
        
        # 2. Yechim uchun maslahatni tozalash (MUAMMO YECHIMI)
        if hint:
            # a) bleach orqali standart tozalash
            cleaned_hint = bleach.clean(hint, tags=allowed_tags, attributes=allowed_attributes, strip=True)
            
            # b) ASOSIY TUZATISH: Regeks orqali bosh va oxiridagi <p> tegini o'chirish
            # Regeks: Matnning boshida <p> va oxirida </p> bo'lsa, ichidagi matnni oladi.
            cleaned_hint = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1', cleaned_hint, flags=re.DOTALL | re.IGNORECASE)
            
            cleaned_data['hint'] = cleaned_hint.strip() # Saqlashdan oldin matnni trim qilish

        # 3. Batafsil yechimni tozalash (MUAMMO YECHIMI)
        if detailed_solution:
            # a) bleach orqali standart tozalash
            cleaned_solution = bleach.clean(detailed_solution, tags=allowed_tags, attributes=allowed_attributes, strip=True)
            
            # b) ASOSIY TUZATISH: Regeks orqali bosh va oxiridagi <p> tegini o'chirish
            cleaned_solution = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1', cleaned_solution, flags=re.DOTALL | re.IGNORECASE)
            
            cleaned_data['detailed_solution'] = cleaned_solution.strip() # Saqlashdan oldin matnni trim qilish

        # 4. Short Answer javobini tozalash (BOLD ** MUAMMOSI YECHIMI)
        if correct_short_answer:
            # Agar foydalanuvchi **dfdf** kiritgan bo'lsa, yulduzlarni olib tashlaymiz.
            # Matnni tozalashdan oldin boshidagi va oxiridagi bo'shliqlarni olib tashlaymiz
            cleaned_answer = correct_short_answer.strip()
            # Boshidan va oxiridan ** ni o'chirish (Agar mavjud bo'lsa, 1 marta)
            if cleaned_answer.startswith('**') and cleaned_answer.endswith('**'):
                 cleaned_answer = cleaned_answer[2:-2].strip()
            
            cleaned_data['correct_short_answer'] = cleaned_answer

        
        # 5. Qolgan validatsiya mantiqi (o'zgarishsiz)
        if answer_format == 'short_answer' and not cleaned_data.get('correct_short_answer'):
            self.add_error('correct_short_answer', _("Qisqa javob formatida to‘g‘ri javob kiritilishi shart."))
        elif answer_format in ['single', 'multiple'] and cleaned_data.get('correct_short_answer'):
            self.add_error('correct_short_answer', _("Yagona yoki ko‘p javob formatida qisqa javob kiritilmasligi kerak."))
        
        # IRT validatsiyasi (o'zgarishsiz qoldi)
        if guessing is not None and not (0.0 <= guessing <= 1.0):
            self.add_error('guessing', _("Taxmin qilish 0.0 dan 1.0 gacha bo‘lishi kerak."))
        if difficulty is not None and not (-3.0 <= difficulty <= 3.0):
            self.add_error('difficulty', _("Qiyinlik -3.0 dan 3.0 gacha bo‘lishi kerak."))
        if difficulty_level and difficulty is not None:
            if not (difficulty_level.min_difficulty <= difficulty <= difficulty_level.max_difficulty):
                self.add_error('difficulty', _(f"{difficulty_level.name} darajasi uchun qiyinlik {difficulty_level.min_difficulty} dan {difficulty_level.max_difficulty} gacha bo‘lishi kerak."))
        if discrimination is not None and not (0.0 <= discrimination <= 2.0):
            self.add_error('discrimination', _("Diskriminatsiya 0.0 dan 2.0 gacha bo‘lishi kerak."))

        return cleaned_data

    def save(self, commit=True):
        """Question obyektini saqlaydi."""
        question = super().save(commit)
        return question
    
# ======================================================================
# 3. IMTIHON, BO'LIM VA KOMPONENT FORMLARI
# ======================================================================

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        # ✅ TUZATILDI: 'exam_type' maydoni butunlay olib tashlandi.
        fields = ['title', 'description', 'is_subject_exam', 'passing_percentage', 'is_premium', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-md'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'rows': 4}),
            'is_subject_exam': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-indigo-600'}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'min': 0, 'max': 100}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-indigo-600'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-indigo-600'}),
        }
        labels = {
            'title': 'Imtihon nomi',
            'description': 'Tavsif',
            'is_subject_exam': 'Fan bo‘yicha imtihonmi?',
            'passing_percentage': 'O‘tish foizi',
            'is_premium': 'Premium imtihonmi?',
            'is_active': 'Faolmi?',
        }

class ExamSectionForm(forms.ModelForm):
    class Meta:
        model = ExamSection
        fields = ['name', 'section_type', 'duration_minutes', 'max_questions', 'min_difficulty', 'max_difficulty']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'id': 'id_name'}),
            'section_type': Select2(attrs={'class': 'w-full', 'id': 'id_section_type'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'min': 1, 'id': 'id_duration_minutes'}),
            'max_questions': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'min': 1, 'id': 'id_max_questions'}),
            'min_difficulty': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'step': '0.1', 'id': 'id_min_difficulty'}),
            'max_difficulty': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'step': '0.1', 'id': 'id_max_difficulty'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_difficulty = cleaned_data.get('min_difficulty')
        max_difficulty = cleaned_data.get('max_difficulty')
        if min_difficulty is not None and max_difficulty is not None and min_difficulty > max_difficulty:
            raise forms.ValidationError("Minimal qiyinlik maksimal qiyinlikdan katta bo'lmasligi kerak.")
        return cleaned_data
        
class ExamSectionStaticQuestionForm(forms.ModelForm):
    class Meta:
        model = ExamSectionStaticQuestion
        fields = ['question', 'question_number']
        widgets = {
            'question': Select2(attrs={'class': 'w-full'}),
            'question_number': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'min': 1}),
        }

class PassageForm(forms.ModelForm):
    content = forms.CharField(
        label="Matn (HTML)",
        widget=CKEditorWidget(config_name='default', attrs={'id': 'id_content'}),
        required=False
    )

    class Meta:
        model = Passage
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'id': 'id_title'}),
        }

from django import forms
from .models import Flashcard, Tag, Question

class FlashcardForm(forms.ModelForm):
    # Tags uchun SelectMultiple widget ishlatish
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full select2-tags', 
            # Select2 klassi bu yerda berildi
        }), 
        label="Tegishli Taglar/Mavzular"
    )

    # Source Question uchun Select widget ishlatish
    source_question = forms.ModelChoiceField(
        queryset=Question.objects.all(), # Question modelidan tanlash
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full select2-source-question',
        }),
        label="Manba savol (Agar mavjud bo'lsa)"
    )

    class Meta:
        model = Flashcard
        fields = [
            'content_type', 'tags', 'english_content', 'uzbek_meaning', 
            'context_sentence', 'source_question', 
        ]
        # Boshqa maydonlar uchun ham CSS klasslarini berish muhim
        widgets = {
            'content_type': forms.Select(attrs={'class': 'w-full'}), 
            'english_content': forms.Textarea(attrs={'rows': 4, 'class': 'w-full rounded-md border-gray-300 shadow-sm'}),
            'uzbek_meaning': forms.Textarea(attrs={'rows': 4, 'class': 'w-full rounded-md border-gray-300 shadow-sm'}),
            'context_sentence': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm'}),
        }

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['name', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'id': 'id_name'}),
            'order': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'id': 'id_order'}),
        }
        labels = {
            'name': 'Mavzu nomi',
            'order': 'Tartib raqami'
        }

class SubtopicForm(forms.ModelForm):
    class Meta:
        model = Subtopic
        fields = ['name', 'topic', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'id': 'id_name'}),
            'topic': Select2(attrs={'class': 'w-full', 'id': 'id_topic'}),
            'order': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'id': 'id_order'}),
        }
        labels = {
            'name': 'Ichki mavzu nomi',
            'topic': 'Asosiy mavzu',
            'order': 'Tartib raqami'
        }

class PurchaseForm(forms.Form):
    promo_code = forms.CharField(
        max_length=50,
        required=False,
        label="Promo kod (agar mavjud bo'lsa)",
        widget=forms.TextInput(attrs={'placeholder': 'Promo kodingizni kiriting', 'class': 'w-full px-3 py-2 border rounded-md', 'id': 'id_promo_code'})
    )

class ScreenshotUploadForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['payment_screenshot', 'payment_comment']
        labels = {
            'payment_screenshot': 'To\'lov cheki (skrinshot yoki PDF)',
            'payment_comment': 'To\'lov haqida izoh (ixtiyoriy)',
        }
        widgets = {
            'payment_comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Masalan, qaysi kartadan yoki qachon to\'lov qilganingiz haqida...', 'class': 'w-full px-3 py-2 border rounded-md'}),
            'payment_screenshot': forms.FileInput(attrs={'class': 'w-full px-3 py-2 border rounded-md'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_screenshot'].required = True 

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'teacher', 'course_type', 'online_lesson_flow', 'is_premium', 'is_active', 'price', 'course_img']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class CourseModuleForm(forms.ModelForm):
    class Meta:
        model = CourseModule
        # 🔥🔥🔥 MUHIM: 'course' va 'order' maydonlari formadan chiqarildi.
        # Sababi: Biz ularni view funksiyalarida (module_create/update) qo'lda boshqaramiz.
        fields = ['title', 'description'] # Faqat foydalanuvchi kiritishi kerak bo'lgan maydonlar qoldi
        # Agar modelingizda 'order' kiritilmasa (masalan, auto-now orqali), uni qo'shish shart emas.
        # Agar 'order'ni formaga qo'shsangiz va uni yashirin maydon qilmasangiz, 
        # u POST so'rovida bo'lmagani uchun validatsiya xato beradi.
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        # 'course' va 'order' ni field/exclude dan qaysi biri qulay bo'lsa, shuni ishlating.
        # Hozirgi holatda, "fields" da ularni olib tashlash eng yaxshi yechim.

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'related_exam']

    def __init__(self, *args, **kwargs):
        module = kwargs.pop('module', None)
        super().__init__(*args, **kwargs)

        if module and module.course and module.course.center:
            self.fields['related_exam'].queryset = Exam.objects.filter(
                center=module.course.center,
                is_subject_exam=True
            ).order_by('title')
        else:
            self.fields['related_exam'].queryset = Exam.objects.none()

        # Select2 uchun chiroyli placeholder
        self.fields['related_exam'].empty_label = "— Mavzu testi tanlanmadi —"
        self.fields['title'].required = True

class LessonResourceForm(forms.ModelForm):
    class Meta:
        model = LessonResource
        fields = ['resource_type', 'title', 'link']  # order olib tashlandi!
        widgets = {
            'resource_type': forms.Select(attrs={
                'class': 'mt-1 block w-full border border-gray-300 bg-white rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'title': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': "Masalan: 1-dars video, Yechim PDF, Qo'shimcha mashq"
            }),
            'link': forms.URLInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'https://youtube.com/watch?v=... yoki https://t.me/...'
            }),
        }
        labels = {
            'resource_type': 'Resurs turi',
            'title': 'Sarlavha (talaba ko‘radi)',
            'link': 'Havola (URL)',
        }
        help_texts = {
            'title': 'Talaba sahifasida ko‘rinadigan matn',
            'link': 'YouTube, Telegram, Google Drive, PDF yoki boshqa havola',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = True
        self.fields['link'].required = True

class CourseScheduleForm(forms.ModelForm):
    """
    Takrorlanuvchi CourseSchedule modeli uchun forma.
    Kurs ma'lumotlari View orqali olinadi va forma ichida yashiriladi.
    """
    
    # TimeField ni maxsus TimeInput widgeti bilan belgilash
    start_time = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-field-style'}),
        label="Boshlanish vaqti"
    )

    class Meta:
        model = CourseSchedule
        # Barcha kerakli maydonlar, jumladan 'course' ni ham Meta.fields ga qo'shamiz
        fields = ['course', 'day_of_week', 'start_time', 'order_in_cycle', 'is_start_slot']
        
    def __init__(self, *args, **kwargs):
        # course_instance ni pop qilib olamiz
        course_instance = kwargs.pop('course_instance', None)
        super().__init__(*args, **kwargs)
        
        # 'course' maydoni bilan ishlash
        if course_instance and 'course' in self.fields:
            # 1. Boshlang'ich qiymatni o'rnatish
            self.fields['course'].initial = course_instance.pk
            # 2. Maydonni yashirish
            self.fields['course'].widget = forms.HiddenInput()
        elif 'course' in self.fields:
             # Agar instance berilmasa (yaratish/tahrirlash uchun), 'course' ni o'chiramiz, chunki u majburiy emas. 
             # View uni saqlashdan oldin o'rnatadi.
             # Ammo bizning mantig'imizda uni har doim yashirish kerak. Shuning uchun else shartini qo'ymadim.
             pass

        # Hafta kuni tanlovini sozlash va CSS qo'shish
        if 'day_of_week' in self.fields:
            # Django ning o'rnatilgan choices bilan Select widgeti
            self.fields['day_of_week'].widget.attrs.update({'class': 'form-field-style'})
            
        # order_in_cycle uchun CSS qo'shish
        if 'order_in_cycle' in self.fields:
            self.fields['order_in_cycle'].widget.attrs.update({'class': 'form-field-style'})
                          
class TagForm(forms.ModelForm):
    # Ota-ona tegini tanlash maydoni. Hamma taglar ichidan tanlash imkonini beradi.
    # Agar sizda o'z CustomUser modelingiz bo'lsa, uni ham import qiling
    
    class Meta:
        model = Tag
        fields = ['name', 'parent', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matematika, Geometriya, Algebra kabi...'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': "Teg/Mavzu nomi",
            'parent': "Ota-ona teg/Mavzu",
            'description': "Tavsif",
        }

class CenterForm(forms.ModelForm):
    """Yangi O'quv Markazi va uning birinchi obunasini yaratish uchun shakl"""
    
    # 1. Obuna muddati maydoni (faqat YARATISH uchun mantiqiy)
    # Bu maydon Center modelida emas, shuning uchun uni formaga alohida qo'shamiz.
    subscription_months = forms.IntegerField(
        label="Obuna muddati (oy)",
        initial=12,
        min_value=1,
        # max_value=24, # Agar maksimal qiymat kerak bo'lsa
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Yaratilgan markaz necha oydan keyin avtomatik bloklanadi."
    )

    class Meta:
        model = Center
        # 2. MUHIM TUZATISH: 'owner' maydonini fields ro'yxatidan butunlay olib tashlaymiz
        fields = ['name', 'slug'] 
        
        # Agar Center modelida boshqa maydonlar bo'lsa, ularni qo'shing.
        # Masalan: fields = ['name', 'slug', 'address', 'phone_number']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Markaz nomi..."}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "url-uchun-unikal-nom"}),
            # 'owner' uchun widget endi kerak emas, chunki u fields'da yo'q
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 3. MUHIM TUZATISH: Owner bilan bog'liq bo'lgan barcha mantiqlarni olib tashlaymiz
        # if 'owner' in self.fields:
        #     self.fields['owner'].queryset = CustomUser.objects.filter(is_superuser=False).order_by('username')
        #     self.fields['owner'].required = True # Bu qism ham o'chiriladi

    # 4. SLUGni faqat yangi yaratishda tekshirish (Tahrirlashda o'z-o'zini tekshirmaslik uchun)
    def clean_slug(self):
        slug = self.cleaned_data['slug']
        
        # Agar markaz mavjud bo'lsa (tahrirlash rejimida)
        if self.instance.pk:
            # Agar slug o'zgarmagan bo'lsa, tekshirmaymiz
            if slug == self.instance.slug:
                return slug
        
        # Yangi markaz yoki slug o'zgargan bo'lsa, mavjudligini tekshiramiz
        if Center.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Bu SLUG (URL manzil) allaqachon band. Iltimos, boshqasini tanlang.")
            
        return slug

    # 5. Tahrirlashda 'subscription_months' ni majburiy qilmaslik
    def clean(self):
        cleaned_data = super().clean()
        
        # Agar form tahrirlash rejimida bo'lsa (markaz mavjud bo'lsa)
        if self.instance.pk:
            # 'subscription_months' ni majburiy emas qilish (chunki u faqat yaratish shablonida bor)
            if 'subscription_months' in self.fields:
                self.fields['subscription_months'].required = False
                
        return cleaned_data

class TeacherAssignmentForm(forms.Form):
    """O'qituvchini Markazga biriktirish uchun shakl"""
    
    # Faqat staff bo'lmagan va markazi belgilanmagan foydalanuvchilarni tanlash
    # Barcha custom userlardan tanlash uchun, o'qituvchilikka nomzodlar ro'yxati
    user_to_assign = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(center__isnull=True).exclude(is_superuser=True).order_by('username'),
        label="O'qituvchi / Xodim (ro'yxatdan o'tgan)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class GroupForm(forms.ModelForm):
    # O‘QUVCHILAR – AJAX orqali qidiriladi
    students = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        label=_("Guruh o'quvchilari"),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'select2-students'})
    )

    # KURSLAR – Markazdagi faqat aktiv kurslar
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        label=_("Kurslar"),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'select2-courses'})
    )

    class Meta:
        model = Group
        fields = ('name', 'courses', 'students', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masalan: Inglizcha A1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.teacher = kwargs.pop('teacher', None)
        self.center = kwargs.pop('center', None)
        
        # Tahrirlash rejimida mavjud ma'lumotlar
        initial_students = []
        initial_courses = []
        instance = kwargs.get('instance')

        # 1. SUPER() – BIRINCHI!
        super().__init__(*args, **kwargs)

        if instance and instance.pk:
            self.initial['courses'] = [c.pk for c in instance.courses.all()]
            self.initial['students'] = [s.pk for s in instance.students.all()]


        # MARKAZ BO‘YICHA KURSLAR
        if self.center:
            self.fields['courses'].queryset = Course.objects.filter(
                center=self.center,
                is_active=True
            ).order_by('title')

        # POST (forma yuborilganda)
        if self.is_bound:
            # O‘quvchilar ID’lari POST dan olinadi
            posted_student_ids = self.data.getlist('students')
            if posted_student_ids:
                self.fields['students'].queryset = CustomUser.objects.filter(
                    pk__in=posted_student_ids
                )

            # Kurslar ID’lari POST dan olinadi
            posted_course_ids = self.data.getlist('courses')
            if posted_course_ids:
                self.fields['courses'].queryset = Course.objects.filter(
                    pk__in=posted_course_ids,
                    center=self.center
                )

        # GET yoki Tahrirlash
        else:
            if initial_students:
                self.fields['students'].queryset = initial_students
                self.initial['students'] = [s.pk for s in initial_students]
            
            if initial_courses:
                self.fields['courses'].queryset = Course.objects.filter(
                    center=self.center,
                    is_active=True
                )
                self.initial['courses'] = [c.pk for c in initial_courses]

        # Tahrirlash rejimida kurslarni to‘g‘ri ko‘rsatish
        if instance and instance.pk:
            self.fields['courses'].queryset = Course.objects.filter(
                center=self.center,
                is_active=True
            )

from django import forms
from django.utils.translation import gettext_lazy as _
# CustomUser modelini import qilishni unutmang
from .models import CustomUser # O'zingizning to'g'ri model yo'lingizni kiriting

class AddStudentToGroupForm(forms.Form):
    student_ids = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(), 
        label=_("O'quvchini qidirish va tanlash"),
        required=True,
    )

    def __init__(self, *args, **kwargs):

        self.center = kwargs.pop('center', None) 
 

        super().__init__(*args, **kwargs)
        # POST so'rovi kelganda, tanlangan ID'larni tekshirish uchun querysetni vaqtinchalik to'ldiramiz.
        if self.is_bound:# 'SelectMultiple' widgetining 'name' atributini chaqirish xatoga sabab bo'layotgan edi.
            posted_student_ids = self.data.getlist('student_ids')

            if posted_student_ids:
                self.fields['student_ids'].queryset = CustomUser.objects.filter(pk__in=posted_student_ids)

    pass

class AddCourseToGroupForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        label="Guruhga qo'shish uchun kurslarni tanlang",
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple', 'data-placeholder': "Kurslarni qidirish..."})
    )

    def __init__(self, *args, center=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)

        if center and group:
            # Markaz bo'yicha kurslarni filtrlash
            all_center_courses = Course.objects.filter(center=center)
            
            # Guruhga allaqachon qo'shilgan kurslarning IDlarini olish
            existing_course_ids = group.courses.values_list('id', flat=True)
            
            # Guruhga hali qo'shilmagan kurslarni tanlab olish (siz so'ragan mantiq)
            available_courses = all_center_courses.exclude(id__in=existing_course_ids)
            
            # ModelMultipleChoiceField ning queryset'ini yangilash
            self.fields['courses'].queryset = available_courses
            
        elif center:
            # Agar guruh berilmagan bo'lsa, faqat markaz kurslarini ko'rsatish
            self.fields['courses'].queryset = Course.objects.filter(center=center)