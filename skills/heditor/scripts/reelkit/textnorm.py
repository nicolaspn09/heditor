"""Text normalisation shared by asr-check and triage: tokens, and notation-only differences.

ASR writes the same spoken words in different notations ("pra"/"para", "7h30"/"sete e meia", "5"/"cinco",
"IA Builders"/"IABuilders"). Those are not masking or editing errors. `notation_tokens` folds them on both sides so
a comparison only counts real word changes. Languages: "pt" (default) and "en".
"""
import re

_NUM_PT = {"zero": "0", "um": "1", "uma": "1", "dois": "2", "duas": "2", "três": "3", "tres": "3", "quatro": "4",
           "cinco": "5", "seis": "6", "sete": "7", "oito": "8", "nove": "9", "dez": "10", "onze": "11", "doze": "12",
           "treze": "13", "catorze": "14", "quatorze": "14", "quinze": "15", "dezesseis": "16", "dezessete": "17",
           "dezoito": "18", "dezenove": "19", "vinte": "20", "trinta": "30", "cinquenta": "50", "cem": "100"}
_NUM_EN = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
           "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20",
           "thirty": "30", "fifty": "50", "hundred": "100"}
_CONTRACTIONS_PT = {"pra": "para", "pro": "para o", "pras": "para as", "pros": "para os", "tá": "está", "tô": "estou",
                    "tão": "estão", "cê": "você", "num": "em um", "numa": "em uma", "às": "as", "à": "a"}
_CONTRACTIONS_EN = {"gonna": "going to", "wanna": "want to", "gotta": "got to"}
WORD = re.compile(r"[a-zà-ú0-9]+")


def tokens(text):
    """Lower-case word tokens (letters with Portuguese accents and digits)."""
    return WORD.findall(text.lower())


def _times(text, lang):
    """'7h30', '19:30', '7 e meia', 'sete e meia' -> '7 30' (hour and minutes as separate digits)."""
    t = re.sub(r"\b(\d{1,2})\s*[h:]\s*(\d{2})\b", r" \1 \2 ", text)
    t = re.sub(r"\b(\d{1,2})\s*h\b", r" \1 ", t)
    if lang == "pt":
        t = re.sub(r"\b(\d{1,2}|[a-zç]+) e meia\b", r" \1 30 ", t)
        t = re.sub(r"\b(\d{1,2}) e (\d{2})\b", r" \1 \2 ", t)
    return t


def notation_tokens(text, lang="pt"):
    """Tokens with notation folded: contractions expanded, number words as digits, times as 'h m'."""
    nums = _NUM_PT if lang == "pt" else _NUM_EN
    contr = _CONTRACTIONS_PT if lang == "pt" else _CONTRACTIONS_EN
    t = text.lower().replace("-", " ")
    out = []
    for tok in tokens(_times(t, lang)):
        tok = contr.get(tok, tok)
        for part in tok.split():
            if lang == "pt" and part in ("a", "o", "as", "os") and out and out[-1] == "para":
                continue        # "para a" is said and often transcribed as "pra"
            out.append(nums.get(part, part))
    # glue frequent split/merged brand-like pairs: "ia builders" == "iabuilders", "py code" == "pycode"
    joined, i = [], 0
    while i < len(out):
        if i + 1 < len(out) and out[i] + out[i + 1] in _GLUE:
            joined.append(out[i] + out[i + 1])
            i += 2
            continue
        joined.append(out[i])
        i += 1
    return joined


_GLUE = {"iabuilders", "pycode", "pycodebr", "fastapi", "whatsapp", "chatbot", "iamaster", "openai", "youtube"}


def same_notation(a, b, lang="pt"):
    """True when two strings only differ in notation (or not at all)."""
    return notation_tokens(a, lang) == notation_tokens(b, lang)
