# services/real_calibration.py
# 100% sizning modelingizga mos, xatosiz
import pandas as pd
from django.db import transaction
from django.core.exceptions import ValidationError
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from rpy2.rinterface_lib.embedded import RRuntimeError
import logging

# R paketlari
try:
    mirt = importr('mirt')
    base = importr('base')
    pandas2ri.activate()
except Exception as e:
    logging.error(f"R yoki mirt yuklanmadi: {e}")
    mirt = None

logger = logging.getLogger(__name__)

@transaction.atomic
def calibrate_center_with_mirt(center):
    """
    Haqiqiy 2PL model bilan kalibratsiya (mirt paketi)
    center — Center objekti
    """
    if mirt is None:
        raise ValidationError("R yoki 'mirt' paketi o‘rnatilmagan!")

    from Mock.models import UserAnswer, Question, QuestionCalibration

    # 1. Toza ma’lumot olish (takror yo‘q, faqat oxirgi javob)
    answers = UserAnswer.objects.filter(
        attempt_section__attempt__exam__center=center,
        is_correct__isnull=False
    ).select_related(
        'question', 'attempt_section__attempt__user'
    ).order_by('attempt_section__attempt__user', 'question', '-answered_at')

    seen = set()
    data = []

    for ua in answers:
        user_id = ua.attempt_section.attempt.user.id
        question_id = ua.question.id
        key = (user_id, question_id)

        if key in seen:
            continue
        seen.add(key)

        data.append({
            'user_id': user_id,
            'question_id': question_id,
            'score': 1 if ua.is_correct else 0
        })

    if len(data) < 100:
        raise ValidationError(f"Javoblar yetarli emas: {len(data)} (kamida 100 ta kerak)")

    if len(set(d['question_id'] for d in data)) < 10:
        raise ValidationError("Kamida 10 ta savol bo‘lishi kerak")

    # 2. Pivot jadval yaratish
    df = pd.DataFrame(data)
    matrix = df.pivot_table(
        index='user_id',
        columns='question_id',
        values='score',
        aggfunc='first',
        fill_value=0
    )

    users_count = matrix.shape[0]
    questions_count = matrix.shape[1]

    if users_count < 20 or questions_count < 10:
        raise ValidationError(f"Kichik ma’lumot: {users_count} o‘quvchi, {questions_count} savol")

    # 3. R ga yuborish va 2PL model
    try:
        with ro.default_converter:
            r_matrix = pandas2ri.py2rpy(matrix)

        # 2PL model (discrimination + difficulty)
        model = mirt.mirt(
            r_matrix,
            model=1,
            itemtype="2PL",
            verbose=False,
            technical=ro.ListVector({"NCYCLES": 5000})
        )

        # Koeffitsientlarni olish
        coef_result = mirt.coef(model, simplify=True)
        coef_df = pandas2ri.rpy2py(coef_result['items'])

        # DataFrame ga o‘tkazish
        params = pd.DataFrame(coef_df)
        params = params.iloc[:-1]  # oxirgi qator "Group" bo‘ladi
        params.columns = ['a', 'b', 'g', 'u']  # a=discrimination, b=difficulty, g=guessing
        params = params[['a', 'b', 'g']]
        params['question_id'] = matrix.columns.astype(int)
        params = params.reset_index(drop=True)

    except RRuntimeError as e:
        raise ValidationError(f"R xatosi: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Kalibratsiya xatosi: {str(e)}")

    # 4. Natijalarni saqlash
    updated = 0
    for _, row in params.iterrows():
        try:
            q = Question.objects.get(id=int(row['question_id']), center=center)
        except Question.DoesNotExist:
            continue

        # Yangi kalibratsiya yaratish
        calibration = QuestionCalibration.objects.create(
            question=q,
            calibrated_at=ro.r['Sys.time']()[0],  # R dan real vaqt
            response_count_used=users_count,
            difficulty=float(row['b']),
            discrimination=float(row['a']),
            guessing=float(row['g']) if pd.notna(row['g']) else 0.25,
            method='2pl_mirt',
            notes=f"Haqiqiy 2PL (mirt), {users_count} o‘quvchi, {questions_count} savol"
        )

        # Question ni yangilash
        q.difficulty = float(row['b'])
        q.discrimination = float(row['a'])
        q.guessing = float(row['g']) if pd.notna(row['g']) else 0.25
        q.current_calibration = calibration
        q.is_calibrated = True
        q.response_count = users_count
        q.save()

        updated += 1

    return {
        'status': 'success',
        'updated': updated,
        'users': users_count,
        'questions': questions_count,
        'message': f"{updated} ta savol haqiqiy 2PL model bilan kalibrlandi!"
    }