# services/sat_scoring_engine.py
# FINAL VERSIYA — ABADIY O‘ZGARMAS!
# NOMI: calculate_sat_math_score
# QAYTARADI: 200, 210, ..., 800
# ISHLATILADI: handle_exam_ajax da

from Mock.models import UserAnswer
import math

# Rasch model — theta hisoblash
def _estimate_theta(answers_qs):
    """Ichki funksiya — faqat theta qaytaradi"""
    if not answers_qs.exists():
        return 0.0

    theta = 0.0
    max_iter = 50

    for _ in range(max_iter):
        deriv = 0.0
        info = 0.0

        for ua in answers_qs:
            b = ua.question.difficulty or 0.0
            exp_term = math.exp(-(theta - b))
            p = 1 / (1 + exp_term)

            if ua.is_correct:
                deriv += (1 - p)
            else:
                deriv += -p
            info += p * (1 - p)

        if abs(deriv) < 0.001 or info == 0:
            break
        theta += deriv / info

    return round(theta, 3)

# Theta → 200-800 (SAT Digital jadvali)
def _theta_to_score(theta):
    """SAT Digital conversiyasi — abadiy shu jadval"""
    table = {
        -4.0: 200, -3.5: 250, -3.0: 300, -2.5: 350, -2.0: 400,
        -1.5: 450, -1.0: 500, -0.5: 540,  0.0: 580,  0.5: 620,
         1.0: 660,  1.5: 700,  2.0: 740,  2.5: 770,  3.0: 790,
         3.5: 800,  4.0: 800
    }
    if theta >= 3.5: return 800
    if theta <= -4.0: return 200

    keys = sorted(table.keys())
    for i in range(len(keys)-1):
        if keys[i] <= theta < keys[i+1]:
            low_val = table[keys[i]]
            high_val = table[keys[i+1]]
            return int(low_val + (high_val - low_val) * (theta - keys[i]) / (keys[i+1] - keys[i]))
    return 800

# BITTA ASOSIY FUNKSION — ABADIY SHU NOMDA!
def calculate_sat_math_score(attempt):
    """
    SIZNING ABADIY FUNKSIONINGIZ
    Ishlatish: score = calculate_sat_math_score(attempt)
    Qaytaradi: 200–800 ball (int)
    """
    answers = UserAnswer.objects.filter(
        attempt_section__attempt=attempt,
        is_correct__isnull=False
    ).select_related('question')

    total = answers.count()
    if total == 0:
        return 200

    theta = _estimate_theta(answers)
    raw_scaled = _theta_to_score(theta)
    final_score = int(round(raw_scaled / 10) * 10)  # 10 lik qadam

    # 100% to‘g‘ri bo‘lsa — 800 kafolat!
    if answers.filter(is_correct=True).count() == total:
        final_score = 800

    return final_score