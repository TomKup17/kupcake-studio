"""Jazyky řeči, které umí Whisper (faster-whisper large-v3), pro výběr jazyka přepisu."""
from PySide6.QtCore import QLocale

# kód → anglický název (podle tokenizeru Whisperu)
ANGLICKY = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "as": "Assamese", "az": "Azerbaijani", "ba": "Bashkir",
    "be": "Belarusian", "bg": "Bulgarian", "bn": "Bengali", "bo": "Tibetan", "br": "Breton", "bs": "Bosnian",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "es": "Spanish", "et": "Estonian", "eu": "Basque", "fa": "Persian", "fi": "Finnish",
    "fo": "Faroese", "fr": "French", "gl": "Galician", "gu": "Gujarati", "ha": "Hausa", "haw": "Hawaiian",
    "he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "ht": "Haitian Creole", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian", "ja": "Japanese",
    "jw": "Javanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer", "kn": "Kannada", "ko": "Korean",
    "la": "Latin", "lb": "Luxembourgish", "ln": "Lingala", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mg": "Malagasy", "mi": "Maori", "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian",
    "mr": "Marathi", "ms": "Malay", "mt": "Maltese", "my": "Myanmar", "ne": "Nepali", "nl": "Dutch",
    "nn": "Nynorsk", "no": "Norwegian", "oc": "Occitan", "pa": "Punjabi", "pl": "Polish", "ps": "Pashto",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sa": "Sanskrit", "sd": "Sindhi", "si": "Sinhala",
    "sk": "Slovak", "sl": "Slovenian", "sn": "Shona", "so": "Somali", "sq": "Albanian", "sr": "Serbian",
    "su": "Sundanese", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "tg": "Tajik",
    "th": "Thai", "tk": "Turkmen", "tl": "Tagalog", "tr": "Turkish", "tt": "Tatar", "uk": "Ukrainian",
    "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese", "yi": "Yiddish", "yo": "Yoruba", "zh": "Chinese",
    "yue": "Cantonese",
}

# kde Qt vrací název s oblastí („American English“) nebo jinou abecedu, pevný název
NATIVNI = {"en": "English", "es": "Español", "zh": "中文", "ka": "ქართული", "id": "Bahasa Indonesia"}

# nejpoužívanější nahoře (zbytek abecedně podle anglického názvu)
OBLIBENE = ["cs", "sk", "en", "de", "es", "pl", "fr", "it", "pt", "uk", "ru", "hu", "nl"]


def nazev(kod):
    """Název jazyka v jeho vlastní podobě (např. „Čeština“, „Deutsch“, „日本語“), s anglickým pro jistotu."""
    anglicky = ANGLICKY.get(kod, kod)
    if kod in NATIVNI:
        return NATIVNI[kod] if NATIVNI[kod] == anglicky else f"{NATIVNI[kod]} – {anglicky}"
    loc = QLocale(kod)
    nativni = loc.nativeLanguageName() if loc.language() != QLocale.C else ""
    if not nativni or kod in ("jw", "haw", "ln", "sn", "ba", "oc", "yue") and loc.language() == QLocale.English:
        return anglicky
    nativni = nativni[:1].upper() + nativni[1:]
    return nativni if nativni.lower() == anglicky.lower() else f"{nativni} – {anglicky}"


def serazene():
    """[(kód, název)]: oblíbené jazyky, pak ostatní abecedně."""
    ostatni = sorted((k for k in ANGLICKY if k not in OBLIBENE), key=lambda k: ANGLICKY[k])
    return [(k, nazev(k)) for k in OBLIBENE], [(k, nazev(k)) for k in ostatni]
