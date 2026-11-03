"""Přesné časování slov po přepisu.

1. Forced alignment: každé slovo z Whisperu se zarovná ke zvuku akustickým modelem wav2vec2 (CTC) –
   stejný postup jako WhisperX, jen bez jeho závislostí. Pro jazyky s vlastním modelem (cs, sk, en, de,
   es, fr, it, pl) se použije ten, ostatní jazyky vícejazyčný MMS (text se převede do latinky přes uroman).
2. Dorovnání začátku slova k nástupu zvuku – až o 60 ms dřív (onset podle náběhu energie).
3. Dočištění: slova se nepřekrývají, každé je vidět aspoň MIN_ZOBRAZENI, mezi slovy je MIN_MEZERA.

Modely se stahují při prvním použití do %LOCALAPPDATA%\\KupcakeStudio\\models\\zarovnani.
Licence modelů: THIRD_PARTY_LICENSES.md (MMS je CC-BY-NC 4.0 – jen nekomerčně).
"""
import logging
import json
import os
import re
import unicodedata
import numpy as np

from cesty import MODELY_DIR
from i18n import t

# bez ukazatelů průběhu na stdout – v exe bez konzole stdout neexistuje
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
# modely stahuje a ověřuje jen stahovani.py – transformers ani huggingface_hub nesmí na síť samy
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

_log = logging.getLogger("kupcake").info  # výchozí log: do souboru (logy.py)
SR = 16000
KROK = 320 / SR            # wav2vec2: jeden výstupní snímek = 20 ms
ONSET_PRED = 0.06          # dorovnání začátku k nástupu zvuku: až o 60 ms dřív…
ONSET_PO = 0.0             # …a nikdy později (viz dorovnej_k_nastupu)
MIN_ZOBRAZENI = 0.12       # nejkratší doba zobrazení slova (s)
MIN_MEZERA = 0.02          # nejmenší mezera mezi slovy (s)
OKRAJ = 0.25               # kolik zvuku navíc vzít kolem úseku Whisperu (s)

MODELY = {  # jazyk → wav2vec2 CTC model (Apache-2.0); stejné, jaké používá WhisperX
    "cs": "comodoro/wav2vec2-xls-r-300m-cs-250",
    "sk": "comodoro/wav2vec2-xls-r-300m-sk-cv8",
    "en": "facebook/wav2vec2-base-960h",
    "de": "jonatasgrosman/wav2vec2-large-xlsr-53-german",
    "es": "jonatasgrosman/wav2vec2-large-xlsr-53-spanish",
    "fr": "jonatasgrosman/wav2vec2-large-xlsr-53-french",
    "it": "jonatasgrosman/wav2vec2-large-xlsr-53-italian",
    "pl": "jonatasgrosman/wav2vec2-large-xlsr-53-polish",
}
MMS = "MahmoudAshraf/mms-300m-1130-forced-aligner"  # vícejazyčný (CC-BY-NC 4.0 – jen nekomerčně)
POUZIT_MMS = True  # False = jazyky bez vlastního modelu zůstanou na časech z Whisperu (pro komerční použití)
# potřebné soubory modelu (+ váhy) – z nich nastroje/vytvor_manifest.py sestaví manifest se SHA-256
SOUBORY = ["config.json", "vocab.json", "preprocessor_config.json", "tokenizer_config.json",
           "special_tokens_map.json", "added_tokens.json"]

_zarovnavace = {}


def repo_pro(jazyk):
    if jazyk in MODELY:
        return MODELY[jazyk]
    if not POUZIT_MMS:
        raise LookupError(f"pro jazyk „{jazyk}“ není model s volnou licencí")
    return MMS


def _stahni(repo, log):
    """Model do MODELY_DIR/zarovnani/<repo>: jen potřebné soubory v pevné revizi, každý ověřený SHA-256
    (manifest_modelu.py); stažení se nejdřív potvrdí uživatelem."""
    import stahovani
    cil = MODELY_DIR / "zarovnani" / repo.replace("/", "--")
    if not stahovani.je_pripraveno(repo, cil):
        log(t("log.zarovnani_stahuji", model=repo))
        stahovani.priprav_repo(repo, cil, t("stahovani.zarovnani", model=repo), log=log)
    return cil


class Zarovnavac:
    """Akustický model + slovník znaků pro jeden jazyk."""

    def __init__(self, jazyk, log=_log):
        from transformers import Wav2Vec2ForCTC
        self.repo = repo_pro(jazyk)
        self.mms = self.repo == MMS
        cesta = _stahni(self.repo, log)
        self.zarizeni = zarizeni()
        # jen z disku; safetensors, kde jsou – u pytorch_model.bin (de, es, fr, it, pl, sk) načítá transformers
        # omezeným unpicklerem (weights_only=True, tady výslovně) a soubor je navíc ověřený SHA-256
        self.model = Wav2Vec2ForCTC.from_pretrained(str(cesta), local_files_only=True,
                                                    weights_only=True).to(self.zarizeni).eval()
        slovnik = json.loads((cesta / "vocab.json").read_text(encoding="utf-8"))
        if slovnik and isinstance(next(iter(slovnik.values())), dict):  # vícejazyčný formát {jazyk: {znak: id}}
            slovnik = next(iter(slovnik.values()))
        self.slovnik = {k.lower(): v for k, v in slovnik.items()}
        self.prazdny = slovnik.get("<pad>", slovnik.get("[PAD]", 0))
        self.oddelovac = self.slovnik.get("|")
        pre = cesta / "preprocessor_config.json"
        self.normalizovat = json.loads(pre.read_text(encoding="utf-8")).get("do_normalize", True) if pre.exists() else True

    # ---------- text → znaky modelu ----------
    def znaky(self, slovo):
        """ID znaků slova, které model zná (u MMS po převodu do latinky); prázdné = slovo nejde zarovnat."""
        text = slovo.lower()
        if self.mms:
            text = _latinka(text)
        vys = []
        for z in text:
            if z in self.slovnik:
                vys.append(self.slovnik[z])
                continue
            zaklad = unicodedata.normalize("NFKD", z)[0]  # „ů“ → „u“, když model diakritiku nezná
            if zaklad in self.slovnik and zaklad.isalpha():
                vys.append(self.slovnik[zaklad])
        return vys

    # ---------- zvuk → pravděpodobnosti znaků ----------
    def emise(self, audio):
        import torch
        x = audio.astype(np.float32)
        if self.normalizovat:
            x = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
        with torch.inference_mode():
            vstup = torch.from_numpy(x)[None].to(self.zarizeni)
            logity = self.model(vstup).logits[0]
            return torch.log_softmax(logity.float(), dim=-1).cpu().numpy()

    def zarovnej_usek(self, audio, slova, t0):
        """slova = [{text, start, end}] jednoho úseku; audio začíná v čase t0. Vrátí (start, end) nebo None
        pro každé slovo."""
        if len(audio) < SR * 0.1:
            return [None] * len(slova)
        lp = self.emise(audio)
        tokeny, patri = [], []  # patri[i] = index slova pro token i (oddělovač = -1)
        for i, s in enumerate(slova):
            z = self.znaky(s["text"])
            if not z:
                continue
            if tokeny and self.oddelovac is not None:
                tokeny.append(self.oddelovac)
                patri.append(-1)
            tokeny += z
            patri += [i] * len(z)
        vysledek = [None] * len(slova)
        if not tokeny or len(tokeny) > lp.shape[0]:
            return vysledek
        useky = viterbi(lp, tokeny, self.prazdny)
        if useky is None:
            return vysledek
        for i in range(len(slova)):
            snimky = [useky[k] for k, p in enumerate(patri) if p == i]
            if snimky:
                vysledek[i] = (t0 + snimky[0][0] * KROK, t0 + (snimky[-1][1] + 1) * KROK)
        return vysledek


def _latinka(text):
    """Převod do latinky pro MMS (uroman); bez něj aspoň odstraní diakritiku."""
    try:
        import uroman
        global _uroman
        if "_uroman" not in globals():
            _uroman = uroman.Uroman()
        text = _uroman.romanize_string(text)
    except Exception:
        text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z' ]", "", text.lower())


def viterbi(lp, tokeny, prazdny):
    """CTC forced alignment (Viterbi): nejpravděpodobnější cesta přes tokeny s volitelnými mezerami (blank).
    Vrátí [(první_snímek, poslední_snímek)] pro každý token, nebo None."""
    T, S = lp.shape[0], len(tokeny)
    L = 2 * S + 1
    ext = np.full(L, prazdny, dtype=np.int64)
    ext[1::2] = tokeny
    neg = -1e30
    skok = np.zeros(L, dtype=bool)  # přeskočit blank smí jen mezi dvěma různými znaky
    skok[3::2] = ext[3::2] != ext[1:-2:2]
    dp = np.full(L, neg)
    dp[0] = lp[0, ext[0]]
    dp[1] = lp[0, ext[1]]
    zpet = np.zeros((T, L), dtype=np.int8)
    for t in range(1, T):
        b = np.concatenate(([neg], dp[:-1]))
        c = np.where(skok, np.concatenate(([neg, neg], dp[:-2])), neg)
        moznosti = np.stack((dp, b, c))
        volba = moznosti.argmax(axis=0)
        dp = moznosti[volba, np.arange(L)] + lp[t, ext]
        zpet[t] = volba
    stav = L - 1 if dp[L - 1] >= dp[L - 2] else L - 2
    if dp[stav] <= neg / 2:
        return None
    cesta = np.empty(T, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        cesta[t] = stav
        stav -= int(zpet[t, stav])
    useky = [None] * S
    for t, st in enumerate(cesta):
        if st % 2:
            k = st // 2
            useky[k] = (t, t) if useky[k] is None else (useky[k][0], t)
    return None if any(u is None for u in useky) else useky


# ---------- nástup zvuku ----------
def obalka_nastupu(audio, hop=160):
    """Síla náběhu zvuku po 10 ms: kladný přírůstek energie v dB, mírně vyhlazený."""
    n = len(audio) // hop
    if n < 3:
        return np.zeros(max(n, 0))
    e = np.sqrt((audio[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)
    db = 20 * np.log10(e)
    narust = np.maximum(np.diff(db, prepend=db[0]), 0)
    return np.convolve(narust, [0.25, 0.5, 0.25], mode="same")


def dorovnej_k_nastupu(slova, audio, pred=ONSET_PRED, po=ONSET_PO, hop=160):
    """Začátek každého slova posune k nejsilnějšímu výraznému náběhu zvuku v okně [start − pred, start + po].
    Měřením (porovnání se spektrálními nástupy na 3 videích) vyšlo nejlépe jen dopředu do 60 ms:
    akustický model začátek slova spíš opožďuje, posun dozadu přesnost zhoršoval."""
    if not slova:
        return slova
    obalka = obalka_nastupu(audio, hop)
    if not len(obalka):
        return slova
    prah = max(np.percentile(obalka, 80), 3.0)  # „výrazný“ = mezi 20 % nejsilnějších náběhů, aspoň 3 dB
    krok = hop / SR
    for i, s in enumerate(slova):
        a = max(int((s["start"] - pred) / krok), 0)
        b = min(int((s["start"] + po) / krok) + 1, len(obalka))
        if b <= a:
            continue
        j = a + int(np.argmax(obalka[a:b]))
        if obalka[j] < prah:
            continue
        novy = j * krok
        dolni = slova[i - 1]["end"] if i else 0.0
        if dolni <= novy < s["end"] - 0.05:
            s["start"] = round(novy, 3)
    return slova


# ---------- dočištění ----------
def docisti(slova, min_zobrazeni=MIN_ZOBRAZENI, mezera=MIN_MEZERA):
    """Slova se nepřekrývají, mezi nimi je aspoň `mezera`, každé trvá aspoň `min_zobrazeni`, pokud to
    následující slovo dovolí (jinak ho zvýraznění ukáže spolu se sousedem – titulky.MIN_ZOBRAZENI)."""
    for i, s in enumerate(slova):
        if i:
            predchozi = slova[i - 1]["end"]
            # mezera jen tam, kde se slovo nezkrátí pod 50 ms; překryv se odstraní vždy
            s["start"] = max(s["start"], predchozi + mezera if predchozi + mezera < s["end"] - 0.05 else predchozi)
        strop = slova[i + 1]["start"] - mezera if i + 1 < len(slova) else s["end"] + min_zobrazeni
        if s["end"] - s["start"] < min_zobrazeni:
            s["end"] = max(s["end"], min(s["start"] + min_zobrazeni, strop))
        if s["end"] - s["start"] < min_zobrazeni:  # dozadu nejde – zkusit začít dřív (v mezeře před slovem)
            dno = slova[i - 1]["end"] + mezera if i else 0.0
            s["start"] = min(s["start"], max(dno, s["end"] - min_zobrazeni))
        s["end"] = max(s["end"], s["start"] + 0.05)
        s["start"], s["end"] = round(s["start"], 3), round(s["end"], 3)
    return slova


# ---------- zařízení ----------
_vynucene = None  # "cpu" = vše na procesoru (slabší počítač, vynucení v nastavení, došla VRAM)


def nastav_zarizeni(zarizeni):
    """None = automaticky (CUDA, je-li), "cpu" = jen procesor. Modely na jiném zařízení se zahodí."""
    global _vynucene
    if zarizeni != _vynucene:
        _vynucene = zarizeni
        _zarovnavace.clear()


def zarizeni():
    import torch
    import hardware
    if _vynucene == "cpu" or hardware.vynuceny_procesor() or not torch.cuda.is_available():
        return "cpu"
    return "cuda"


def _usek(jazyk, log, audio, slova, t0):
    """Zarovnání úseku; když GPU dojde paměť, přejde na procesor a zkusí to znovu."""
    try:
        return zarovnavac(jazyk, log).zarovnej_usek(audio, slova, t0)
    except Exception as e:
        if zarizeni() == "cpu" or "out of memory" not in str(e).lower():
            raise
        log(t("log.zarovnani_cpu"))
        nastav_zarizeni("cpu")
        return zarovnavac(jazyk, log).zarovnej_usek(audio, slova, t0)


# ---------- celý postup ----------
def zarovnavac(jazyk, log=_log):
    repo = repo_pro(jazyk)
    if repo not in _zarovnavace:
        _zarovnavace[repo] = Zarovnavac(jazyk, log)
    return _zarovnavace[repo]


def zarovnej(slova, useky, audio, jazyk, log=_log, progress=lambda p: None, docisteni=lambda: None):
    """slova = [{text, start, end}] v pořadí; useky = [(start, end, [indexy slov])] z Whisperu.
    Zarovná slova po úsecích, nezarovnatelná (čísla, symboly) dopočítá mezi sousedy, pak dorovná
    začátky k nástupu zvuku a dočistí. Mění a vrací `slova`.
    progress(0–1) = průběh zarovnání po úsecích; docisteni() = ohlášení poslední fáze (vrátí její progress)."""
    zarovnavac(jazyk, log)  # model načíst hned (stažení / chyba ještě před průběhem po úsecích)
    delka = len(audio) / SR
    for n, (a, b, indexy) in enumerate(useky):
        progress(n / len(useky))
        if not indexy:
            continue
        t0 = max(a - OKRAJ, 0.0)
        t1 = min(b + OKRAJ, delka)
        casy = _usek(jazyk, log, audio[int(t0 * SR):int(t1 * SR)], [slova[i] for i in indexy], t0)
        for i, c in zip(indexy, casy):
            if c is not None:
                slova[i]["start"], slova[i]["end"] = c
                slova[i]["zarovnano"] = True
        progress((n + 1) / len(useky))
    p = docisteni() or (lambda x: None)
    _dopocitej(slova)
    p(0.4)
    dorovnej_k_nastupu(slova, audio)
    p(0.8)
    for s in slova:
        s.pop("zarovnano", None)
    docisti(slova)
    p(1.0)
    return slova


def _dopocitej(slova):
    """Nezarovnaná slova rozprostře mezi nejbližší zarovnané sousedy (zachová pořadí)."""
    i = 0
    while i < len(slova):
        if slova[i].get("zarovnano"):
            i += 1
            continue
        j = i
        while j < len(slova) and not slova[j].get("zarovnano"):
            j += 1
        a = slova[i - 1]["end"] if i else slova[i]["start"]
        b = slova[j]["start"] if j < len(slova) else slova[j - 1]["end"]
        if b > a:  # jinak ponechat časy Whisperu
            krok = (b - a) / (j - i)
            for k in range(i, j):
                slova[k]["start"] = a + (k - i) * krok
                slova[k]["end"] = a + (k - i + 1) * krok
        i = j


def zarovnej_vyber(slova, audio, jazyk, log=_log):
    """Znovu zarovná jen vybraná slova (po ruční opravě textu) v jejich časovém rozsahu ± OKRAJ."""
    if not slova:
        return slova
    t0 = max(slova[0]["start"] - OKRAJ, 0.0)
    t1 = min(slova[-1]["end"] + OKRAJ, len(audio) / SR)
    casy = _usek(jazyk, log, audio[int(t0 * SR):int(t1 * SR)], slova, t0)
    for s, c in zip(slova, casy):
        if c is not None:
            s["start"], s["end"] = c
            s["zarovnano"] = True
    _dopocitej(slova)
    dorovnej_k_nastupu(slova, audio)
    for s in slova:
        s.pop("zarovnano", None)
    return docisti(slova)
