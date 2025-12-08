from django import template
from django.utils.safestring import mark_safe
from datetime import date
import re

register = template.Library()   # FAQAT BITTA MAROTABA!!!

# ------------------ Barcha filterlar ------------------

@register.filter
def add(value, arg):
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def sub(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def mul(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary[key]
    except (KeyError, IndexError, TypeError):
        return None

@register.filter
def filter_by_id(queryset, id):
    try:
        return queryset.get(id=int(id))
    except (queryset.model.DoesNotExist, ValueError, TypeError):
        return None

@register.filter
def remove_p_tags(value):
    if not value or not isinstance(value, str):
        return value
    stripped = value.strip()
    match = re.match(r'^\s*<p>(.*?)</p>\s*$', stripped, re.DOTALL | re.IGNORECASE)
    if match:
        return mark_safe(match.group(1).strip())
    return mark_safe(value)

@register.filter
def clean_uzbek_text(value):
    if not value:
        return value
    clean = re.sub(r'<[^>]*?>', '', str(value))
    clean = clean.replace('‘', "'").replace('’', "'").replace('`', "'")
    return mark_safe(clean)

@register.filter
def get_percentage(value):
    if isinstance(value, str) and value.endswith('%'):
        try:
            return int(value.rstrip('%'))
        except ValueError:
            return 0
    return 0

@register.filter
def gt(value, arg):
    try:
        return value > int(arg)
    except (ValueError, TypeError):
        return False

@register.filter
def days_left(end_date):
    """Obuna tugashiga qancha kun qoldi (30-dekabr → 29 kun qoldi)"""
    if not end_date:
        return None
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    delta = end_date - date.today()
    return delta.days

@register.filter
def filter_active_subs(students_data):
    """ Faqat aktiv obunasi (subscription) bor o'quvchilarni sanaydi. """
    return [item for item in students_data if item.get('is_active') and item.get('sub_info', {}).get('type') == 'subscription']

@register.filter
def filter_active_packages(students_data):
    """ Faqat aktiv kreditlari (package) bor o'quvchilarni sanaydi. """
    
    # 1. 'balance_info' ni None bo'lishi mumkinligi bilan olamiz.
    # 2. Keyin bu ma'lumotlar None emasligini va uning ichidagi 'is_active' True ekanligini tekshiramiz.
    return [
        item for item in students_data 
        if item.get('balance_info') is not None and item.get('balance_info', {}).get('is_active')
    ]
    # Yoki qisqaroq va to'g'riroq:
    # return [
    #     item for item in students_data 
    #     if item.get('balance_info') and item.get('balance_info').get('is_active')
    # ]


@register.filter
def get_youtube_id(url):
    """
    Berilgan YouTube URL (qisqa yoki to'liq) dan video IDni ajratib oladi.
    """
    if not url:
        return None
        
    # Standart URLlar uchun: https://www.youtube.com/watch?v=ID
    match = re.search(r'(?<=v=)[a-zA-Z0-9_-]+', url)
    if match:
        return match.group(0)

    # Qisqa URLlar uchun: https://youtu.be/ID
    match = re.search(r'(?<=youtu\.be/)[a-zA-Z0-9_-]+', url)
    if match:
        return match.group(0)
    
    # Yangi (o'rnatilgan) havolalar uchun, masalan: embed/ID
    match = re.search(r'embed/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    return None




@register.filter
def filter_active_courses(progress_data):
    """
    Kurs progressi ma'lumotlari ro'yxatidan faqat 100% dan kam bo'lgan kurslarni (aktiv kurslarni) filtrlaydi.
    
    Misol:
    {% with active_courses=course_progress_data|filter_active_courses %}
        ...
    {% endwith %}
    """
    
    # Ma'lumotlar list ekanligiga va unda 'progress_percent' kaliti borligiga ishonch hosil qilinadi
    if not isinstance(progress_data, list):
        return []
        
    active_list = []
    for data in progress_data:
        # progress_percent 100 dan kichik bo'lsa, bu kurs hali tugallanmagan (aktiv) hisoblanadi.
        # Bu yerda data obyekt/dict bo'lishi va progress_percent ga ega bo'lishi kutiladi.
        if hasattr(data, 'progress_percent') and data.progress_percent < 100:
            active_list.append(data)
        elif isinstance(data, dict) and data.get('progress_percent', 0) < 100:
            active_list.append(data)
            
    return active_list

# Qo'shimcha: Agar kerak bo'lsa, tugallangan kurslarni hisoblash uchun ham filter.
@register.filter
def filter_completed_courses(progress_data):
    """
    Kurs progressi ma'lumotlari ro'yxatidan faqat 100% bo'lgan kurslarni (tugallangan kurslarni) filtrlaydi.
    """
    if not isinstance(progress_data, list):
        return []
        
    completed_list = []
    for data in progress_data:
        if hasattr(data, 'progress_percent') and data.progress_percent == 100:
            completed_list.append(data)
        elif isinstance(data, dict) and data.get('progress_percent', 0) == 100:
            completed_list.append(data)
            
    return completed_list