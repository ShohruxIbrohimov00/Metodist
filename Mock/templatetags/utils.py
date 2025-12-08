# Mock/templatetags/utils.py
from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split string by arg"""
    return value.split(arg)

@register.filter
def first_char(value):
    """Birinchi harfni olish"""
    return value[0] if value else ''

@register.filter
def initials(name):
    """Ism familiyadan bosh harflar"""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        return parts[0][:2].upper()
    return '??'


@register.filter
def get_percentage(value):
    """
    Natija satridagi (masalan, '80%') foiz belgisini (%) olib tashlaydi
    va qiymatni butun songa (integer) aylantiradi.
    """
    if isinstance(value, str) and value.endswith('%'):
        try:
            # Foiz belgisini olib tashlash va butun songa o'girish
            return int(value.rstrip('%'))
        except ValueError:
            # Agar konvertatsiya qilishda xato bo'lsa (masalan, '80A%')
            return 0
    # Agar format mos kelmasa yoki string bo'lmasa, 0 qaytariladi
    return 0


@register.filter
def gt(value, arg):
    """Qiyos: value > arg"""
    try:
        return value > int(arg)
    except (ValueError, TypeError):
        return value > arg