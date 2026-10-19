"""
Fast heuristic language detector specialized for CJK, Vietnamese, and English.
Accurately distinguishes Vietnamese (with diacritics), Japanese (Hiragana/Katakana),
Chinese (Hanzi), and English.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

Language = Literal["vi", "en", "zh", "ja", "ru", "ko"]

# Specific regex patterns
# Hiragana & Katakana (uniquely identifies Japanese)
JA_KANA_REGEX = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF]")

# Korean Hangul
KO_HANGUL_REGEX = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF]")

# CJK Unified Ideographs (Chinese Hanzi or Japanese Kanji)
CJK_REGEX = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")

# Cyrillic script (Russian, Ukrainian, etc.)
CYRILLIC_REGEX = re.compile(r"[\u0400-\u04FF]")

# Vietnamese specific diacritic characters (in NFC)
VI_DIACRITICS_REGEX = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)

# Common Vietnamese words (even if written without accents or short)
VI_COMMON_WORDS = {
    "va", "la", "cua", "nhung", "cac", "co", "duoc", "trong", "mot", "cho",
    "nguoi", "nay", "de", "khi", "voi", "khong", "tai", "ve", "ra", "vao",
    "se", "da", "dang", "rat", "hon", "nhu", "tu", "theo", "len", "xuong"
}


def detect_language(text: str) -> Language:
    """
    Detects if text is Vietnamese ('vi'), Japanese ('ja'), Chinese ('zh'),
    Russian/Cyrillic ('ru'), Korean ('ko'), or English ('en').
    """
    normalized = unicodedata.normalize("NFC", text.strip())
    if not normalized:
        return "en"

    # 1. Check for Japanese Kana
    if JA_KANA_REGEX.search(normalized):
        return "ja"

    # 2. Check for Korean Hangul
    if KO_HANGUL_REGEX.search(normalized):
        return "ko"

    # 3. Check for CJK characters (without Kana -> Chinese)
    if CJK_REGEX.search(normalized):
        return "zh"

    # 4. Check for Cyrillic (Russian)
    if CYRILLIC_REGEX.search(normalized):
        return "ru"

    # 5. Check for Vietnamese accented characters
    if VI_DIACRITICS_REGEX.search(normalized):
        return "vi"

    # 6. Check for common unaccented Vietnamese words if multi-word
    words = [w.lower() for w in re.findall(r"\b\w+\b", normalized)]
    if len(words) >= 2:
        vi_word_count = sum(1 for w in words if w in VI_COMMON_WORDS)
        if vi_word_count / len(words) >= 0.4:
            return "vi"

    # 7. Default to English
    return "en"


def determine_translation_route(
    text: str,
    reverse_vi_to_en: bool = True,
    pivot_cjk: bool = True,
    target_lang: str = "vi",
) -> tuple[str, str, list[tuple[str, str]]]:
    """
    Returns (src_lang, tgt_lang, list_of_pipeline_pairs) based on detected source and user's target_lang.
    Supports:
      - Default target 'vi': All foreign text -> Vietnamese; Vietnamese -> English [vi -> en].
      - Target 'en': All foreign text -> English; English -> Vietnamese [en -> vi].
      - Target 'ru': All text -> Russian (e.g. vi -> en -> ru, en -> ru); Russian -> English [ru -> en].
      - Any other target 'T': Text -> English -> T; T -> English.
    """
    src_lang = detect_language(text)
    t = target_lang.lower().strip() if target_lang else "vi"

    if t == "vi":
        if src_lang == "vi":
            if not reverse_vi_to_en:
                return "vi", "vi", []
            return "vi", "en", [("vi", "en")]
        elif src_lang == "en":
            return "en", "vi", [("en", "vi")]
        else:
            # Foreign (zh, ja, ru, ko, etc.) -> English -> Vietnamese
            return src_lang, "vi", [(src_lang, "en"), ("en", "vi")]

    elif t == "en":
        if src_lang == "en":
            # Reverse translate English to Vietnamese
            return "en", "vi", [("en", "vi")]
        elif src_lang == "vi":
            return "vi", "en", [("vi", "en")]
        else:
            # Foreign -> English direct
            return src_lang, "en", [(src_lang, "en")]

    else:
        # Target is a third language (e.g. "ru", "zh", "ja", "ko", "de", "fr", "es")
        if src_lang == t:
            # Already target language -> reverse to English
            return src_lang, "en", [(t, "en")]
        elif src_lang == "en":
            # English -> target
            return "en", t, [("en", t)]
        elif src_lang == "vi":
            # Vietnamese -> English -> target (e.g. vi -> en -> ru)
            return "vi", t, [("vi", "en"), ("en", t)]
        else:
            # Other -> English -> target
            return src_lang, t, [(src_lang, "en"), ("en", t)]


