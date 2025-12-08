from django.core.exceptions import ObjectDoesNotExist
from .models import Center 
from django.contrib.auth import get_user_model
from django.db.models import Q

# Agar CustomUser modeli foydalanilayotgan bo'lsa
User = get_user_model() 

def global_context(request):
    """
    Har bir so'rovga foydalanuvchining biriktirilgan markazi (Center FK) asosida
    CENTER_NAME, center va CENTER_SLUG ni qo'shadi.
    Markaziy tizimda faqat request.user.center maydoni tekshiriladi.
    """
    
    # Boshlang'ich kontekst (markaz biriktirilmagan yoki foydalanuvchi kirmagan)
    context = {
        'CENTER_NAME': "SAT Makon", # Umumiy nom
        'center': None,
        'CENTER_SLUG': None,
        'user_is_manager': False,
    }

    if not request.user.is_authenticated:
        return context

    user = request.user
    
    # 1. SUPERUSER / Global Admin
    if user.is_superuser or user.role == 'admin':
        context['CENTER_NAME'] = "Admin"
        context['user_is_manager'] = True
        return context

    # 2. MARKAZNI ANIQLASH (CustomUser.center Foreign Key orqali)
    current_center = user.center

    # 3. YAKUNIY KONTEKST
    if current_center:
        context['center'] = current_center
        context['CENTER_SLUG'] = current_center.slug
        context['CENTER_NAME'] = current_center.name
        
        # 4. ROLNI TEKSHIRISH
        if user.role in ['teacher', 'center_admin', 'owner']:
             context['user_is_manager'] = True
        
    return context
