import re

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """
    Build AnalyzerEngine with custom recognizers for Vietnamese PII.
    Uses regex-based pattern recognizers since Vietnamese spaCy model
    is not available in this environment.
    """

    # --- TASK 2.2.1 ---
    # CCCD recognizer: Vietnamese ID card number (12 digits)
    cccd_pattern = Pattern(name="cccd_pattern", regex=r"\d{12}", score=0.9)
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[cccd_pattern],
        context=["cccd", "căn cước", "chứng minh", "cmnd"],
        supported_language="vi",
    )

    # Custom Vietnamese person name recognizer
    # Matches Faker's output format: "First Last" (e.g., "Khoa Bùi", "Huy Trần")
    # Also matches names with title prefixes: "Ông Trung Hoàng", "Cô Lan Hoàng"
    # Combined list: common Vietnamese names that can appear as first OR last name
    vn_name_word = (
        r"(?:Khoa|Huy|Trung|Hoàng|Lan|Lâm|Mai|Lê|Vũ|"
        r"Nguyễn|Trần|Xuân|Phương|Anh|Thị|Trọng|Nam|"
        r"Thành|Bảo|Hưng|Phạm|Bùi|Linh|Duyên|An|Trí|"
        r"Hồng|Mạnh|Kỳ|Nhi|Hùng|Phúc|Quý|Tuấn|Thanh|"
        r"Chi|Giang|Quang|Hà|Huyền|Quỳnh|Phước|Văn|"
        r"Thảo|Khánh|Dũng|Hiền|Bình|Ngọc|Trang|Thuỷ|"
        r"Thùy|Đức|Hạnh|Thắng|Sơn|Hải|Long|Đạt|Thông|"
        r"Tân|Kiên|Kiều|Minhol|Gia|Hữu|Thanh|Bảo|"
        r"Quang|Phúc|Lộc|Khanh|Nhân|Toàn|Thắng)"
    )
    vn_title = r"(?:Ông|Bà|Cô|Anh|Chị|Anh|Quý|Ông)"
    # Match: [Title ]Name Name  or  Name Name
    name_pattern = Pattern(
        name="vn_person_name",
        regex=(rf"(?:{vn_title}\s+)?{vn_name_word}\s+{vn_name_word}"),
        score=0.9,
    )
    person_recognizer = PatternRecognizer(
        supported_entity="VN_PERSON",
        patterns=[name_pattern],
        context=[
            "bệnh nhân",
            "khách hàng",
            "họ tên",
            "tên",
            "bệnh nhân A",
            "người bệnh",
            "bệnh nhân được chẩn đoán",
        ],
        supported_language="vi",
    )

    # --- TASK 2.2.2 ---
    # Phone recognizer: Vietnamese phone numbers
    # Vietnamese mobile phone formats in dataset:
    # - 84 + 10 digits (no separator): e.g. 8402350290 (11 digits total)
    # - 0 + 10 digits (standard): e.g. 0912345678
    phone_pattern = Pattern(
        name="vn_phone",
        # Matches Vietnamese phone numbers (10 digits, pandas reads as int64
        # stripping leading 0):
        # - Mobile: starts with 09 (without leading 0 = 9), 03, 05, 07, 08
        #   Pattern: 9xxxxxxxx or 03xxxxxxxx etc. → allow [0-9] start
        # - Landline: starts with 02x/04x/06x/08x area codes
        # General pattern: 10 consecutive digits
        regex=r"\d{10}",
        score=0.85,
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[phone_pattern],
        context=["điện thoại", "sdt", "phone", "liên hệ", "số điện thoại"],
        supported_language="vi",
    )

    # Custom email recognizer for Vietnamese
    email_pattern = Pattern(
        name="vn_email",
        regex=r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        score=0.95,
    )
    email_recognizer = PatternRecognizer(
        supported_entity="VN_EMAIL",
        patterns=[email_pattern],
        context=["email", "thư", "hộp thư"],
        supported_language="vi",
    )

    # --- TASK 2.2.3 & 2.2.4 ---
    # Use transformer-based NlpEngine if available, otherwise use
    # rudimentary NLP engine. Since Vietnamese spaCy model is not available,
    # we use a minimal configuration with no NLP enrichment.
    try:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "vi", "model_name": "xx_ent_wiki_sm"}],
            }
        )
        nlp_engine = provider.create_engine()
    except Exception:
        # Fallback: create analyzer without NLP engine (pattern-only)
        nlp_engine = None

    # Initialize AnalyzerEngine
    if nlp_engine:
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    else:
        analyzer = AnalyzerEngine()

    # Add custom recognizers
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(email_recognizer)
    analyzer.registry.add_recognizer(person_recognizer)

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """
    Detect PII in Vietnamese text.
    Returns list of RecognizerResult objects.
    Detects: VN_PERSON, VN_EMAIL, VN_CCCD, VN_PHONE (custom recognizers)
    """
    results = analyzer.analyze(
        text=text,
        language="vi",
        entities=["PERSON", "VN_PERSON", "VN_EMAIL", "VN_CCCD", "VN_PHONE"],
    )
    return results
