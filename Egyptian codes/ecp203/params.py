"""معاملات الكود المصري ECP 203-2020 المستخدمة في الحسابات.

كل قيمة مربوطة بمرجعها (البند / المعادلة / صفحة PDF في ملف الكود الكامل).
المرجع المتاح للكود نص OCR، وبعض الأرقام فيه مشوهة. أي قيمة verified=False
اتاخدت من المعرفة العامة بالكود (طبعة 2007/2001) أو قراءة غير مؤكدة للـ OCR،
ولازم تتراجع على الـ PDF الأصلي قبل الاعتماد. التقرير بيطبع تحذير لكل قيمة منها
اتستخدمت في الحساب.

الوحدات: N و mm و N/mm² (MPa) داخلياً.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ref:
    clause: str
    page: int | None = None
    verified: bool = True
    note: str = ""

    def __str__(self) -> str:
        s = f"ECP 203-2020 {self.clause}"
        if self.page:
            s += f" (صفحة {self.page})"
        if not self.verified:
            s += " ⚠️ تحقق من الأصل"
        return s


# ---------------------------------------------------------------- عامة
GAMMA_C = 1.5
GAMMA_S = 1.15
REF_GAMMA = Ref("بند 4-2 / معاملات خفض المقاومة γc=1.5 و γs=1.15", 155)

ES = 200_000.0  # N/mm²
EPS_CU = 0.003
REF_STRAIN = Ref("بند 4-2-1-1 فرض 5 وشكل 4-1 (εcu=0.003، Es=200 kN/mm²)", 82)

STRESS_BLOCK = 0.67  # 0.67 fcu/γc
BETA1 = 0.8          # a = 0.8 c
REF_BLOCK = Ref("بند 4-2-1-1 فرض 9 وشكل 4-4 (0.67fcu/γc، a=0.8c)", 84)

LOAD_D, LOAD_L = 1.4, 1.6
REF_LOADS = Ref("بند 3-2 معادلة 3-1: U = 1.4 D + 1.6 L", None, True,
                "رقم الصفحة غير مقروء في النسخة المتاحة")

# ---------------------------------------------------------------- الانحناء
A_MIN_OVER_D = 0.1        # a/d لا تقل عن 0.1
LEVER_MAX = 0.95          # ذراع العزم لا يزيد عن 0.95d
REF_A_MIN = Ref("بند 4-2-1-2-أ (a/d ≥ 0.1، ذراع العزم ≤ 0.95d)", 85)

CMAX_FACTOR = 2.0 / 3.0   # cmax = 2/3 cb (بدون إعادة توزيع)
REF_CMAX = Ref("بند 4-2-1-2-ج جدول 4-1 (cmax/d)", 86, False,
               "الجدول غير مقروء في الـ OCR؛ مستخدم cmax = 2/3 cb كما في طبعة 2007")

MIN_RHO_EQ_A = 0.225      # 0.225 √fcu / fy
MIN_RHO_EQ_B = 1.1        # ≥ 1.1 / fy
MIN_INCREASE = 1.3        # أو 1.3 × المطلوب
REF_MIN_FLEX = Ref("بند 4-2-1-2-ح معادلة 4-9", 89, False,
                   "صيغة 0.225√fcu/fy مقروءة؛ الحد 1.1/fy ومعامل 1.3 من طبعة 2007")
MIN_RHO_ABS_MILD = 0.0025   # صلب طري 240
MIN_RHO_ABS_HT = 0.0015     # صلب عالي المقاومة
REF_MIN_ABS = Ref("بند 4-2-1-2-ح (الحد المطلق كنسبة من Ac)", 89, False,
                  "النسب في الـ OCR مشوهة؛ مستخدم 0.25% للطري و0.15% لعالي المقاومة")

COMP_STEEL_MIN_RATIO = 0.10   # As' ≥ 10% As في الكمرات
REF_COMP_MIN = Ref("بند 4-2-1-2-د شرط 5", 88, False, "النسبة مشوهة في الـ OCR")
DPRIME_LIMIT = {240: 0.20, 360: 0.15, 400: 0.10, 420: 0.10, 500: 0.10}
REF_DPRIME = Ref("بند 4-2-1-2-د شرط 1 (حدود d'/d)", 88, False,
                 "ربط كل نسبة برتبة الصلب غير مؤكد من الـ OCR")

# ---------------------------------------------------------------- القص
QCU_UNCRACKED = 0.16   # √(fcu/γc)
REF_QCU_UNC = Ref("بند 4-2-2-1-3-أ معادلة 4-29", 98)
QCU_CRACKED = 0.12
REF_QCU_CR = Ref("بند 4-2-2-1-3-ب معادلة 4-30 و qsu = qu − qcu(cracked) معادلة 4-33", 100)
QU_MAX = 0.70
QU_MAX_CAP = 4.4
REF_QUMAX = Ref("بند 4-2-2-1-2-ج معادلة 4-27 (حد أقصى 4.4 N/mm²)", 97)
DELTA_COMP = 0.07      # δ = 1 + 0.07 Pu/Ac ≤ 1.5
DELTA_COMP_MAX = 1.5
REF_DELTA = Ref("بند 4-2-2-1-3-ب معادلة 4-31", 100, False, "الحد الأقصى لـ δ مشوه")

STIRRUP_MIN_NUM = 0.40          # μmin = 0.4 / fy
STIRRUP_MIN_MILD = 0.0015
STIRRUP_MIN_HT = 0.0010
REF_STIRRUP_MIN = Ref("بند 4-2-2-1-6-أ معادلة 4-40", 102, False,
                      "البسط والنسب الدنيا مشوهة؛ مستخدم قيم طبعة 2007")
STIRRUP_SMAX = 200.0
REF_STIRRUP_SMAX = Ref("بند 4-2-2-1-6-و (أقصى مسافة بين الكانات)", 102, False,
                       "القيمة مشوهة؛ مستخدم 200 مم")
FOUR_LEGS_WIDTH = 400.0
REF_FOUR_LEGS = Ref("بند 4-2-2-1-6-ب (4 فروع للكمرات العريضة)", 102, False,
                    "عرض الكمرة مشوه؛ مستخدم 400 مم")

# ---------------------------------------------------------------- القص الثاقب
PUNCH_ALPHA = {"interior": 4.0, "edge": 3.0, "corner": 2.0}
PUNCH_A = 0.8     # 0.8 (α d/bo + 0.2) √(fcu/γc)
PUNCH_A0 = 0.2
PUNCH_B = 0.316   # 0.316 (0.5 + a/b) √(fcu/γc)
PUNCH_C = 0.316   # 0.316 √(fcu/γc)
PUNCH_CAP = 1.7
REF_PUNCH = Ref("بند 4-2-2-3 معادلات 4-44 و 4-46-a,b,c", 106, False,
                "المعاملات 0.8 و 0.316 مقروءة؛ الحد 0.2 والسقف 1.7 N/mm² من طبعة 2007")

# ---------------------------------------------------------------- الأعمدة
COL_CONC = 0.35
COL_STEEL = 0.67
REF_COL_AXIAL = Ref("بند 4-2-1-3-ج معادلة 4-12-a: Pu = 0.35fcu(Ac−As) + 0.67fy As", 90)
COL_FY_MAX = 420.0
REF_COL_FY = Ref("بند 4-2-1-3-ج (حد أقصى fy للتسليح الطولي)", 91, False,
                 "القيمة مشوهة في الـ OCR")
E_MIN_RATIO = 0.05
E_MIN_ABS = 20.0
REF_EMIN = Ref("بند 4-2-1-3-ج معادلة 4-11 وبند 6-4-5-3 (emin = max(0.05t, 20 مم))", 90, False,
               "القيمة المطلقة مشوهة؛ مستخدم 20 مم")

SHORT_LIMIT = {True: 15.0, False: 10.0}      # braced / unbraced (λ = He/t)
SLENDER_MAX = {True: 30.0, False: 23.0}
REF_SLENDER = Ref("بند 6-4-5 جدولي 6-7 و 6-8", 279, False,
                  "الجداول غير مقروءة؛ مستخدم قيم طبعة 2007 (15/10 و 30/23)")
DELTA_ADD_DIV = 2000.0
REF_ADD_MOM = Ref("بند 6-4-5 (العزوم الإضافية δ = λ² t / 2000)", 280, False,
                  "المعادلة من طبعة 2007؛ راجع صيغة 2020")

COL_MIN_REQ = 0.008       # 0.8% من المساحة المطلوبة حسابياً
COL_MIN_ACT = 0.006       # لا يقل عن 0.6% من الفعلية
REF_COL_MIN = Ref("بند 6-4-6-أ", 293, False,
                  "النسبة من الفعلي مشوهة؛ وفي 2020 حد إضافي للأعمدة النحيفة (معادلة 6-49)")
COL_MAX = {"interior": 0.04, "edge": 0.05, "corner": 0.06}
REF_COL_MAX = Ref("بند 6-4-6-ب (4% وسطية، 5% طرفية، 6% ركنية)", 293)
COL_MIN_BAR = 12.0
COL_MIN_DIM = 200.0
COL_TIE_SPACING_DIA = 15.0
COL_TIE_SPACING_MAX = 200.0
COL_TIE_MIN_DIA = 8.0
REF_COL_DETAIL = Ref("بند 6-4-6-د,ه,ز وصفحة 294 (قطر 12 مم، بعد 200 مم، كانات 15Ø و200 مم، Ø ≥ max(8، Ø/4))",
                     293, False, "بعض الأرقام مشوهة")

# ---------------------------------------------------------------- التماسك
FBU = 0.30    # √(fcu/γc) للأسياخ ذات النتوءات
BETA_DEFORMED = 0.75
REF_LD = Ref("بند 4-2-5-1 معادلة 4-66 و 4-67: Ld = α β η (fy/γs) Ø / (4 fbu)", 130, False,
             "معامل β من جدول 4-8 مشوه؛ مستخدم 0.75 للأسياخ ذات النتوءات")
LD_MIN_DIA, LD_MIN_ABS = 40.0, 300.0
REF_LD_MIN = Ref("بند 4-2-5-1-ج (حد أدنى لطول التماسك)", 130, False, "الأرقام مشوهة")


def sqrt_fcu_gc(fcu: float) -> float:
    return (fcu / GAMMA_C) ** 0.5


def fyd(fy: float) -> float:
    return fy / GAMMA_S


def is_mild(fy: float) -> bool:
    return fy <= 280
