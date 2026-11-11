# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Logy a zachytávání chyb.

- Log do %LOCALAPPDATA%\\KupcakeStudio\\logs\\kupcake.log s rotací (4 × 1 MB, tedy nejvýš ~4 MB).
- Každá nezachycená výjimka (hlavní vlákno, vlákna na pozadí) se zapíše do logu a uživatel dostane
  srozumitelnou hlášku s tlačítkem „Zkopírovat hlášení“ (verze, systém, chyba) – aplikace běží dál.
- Varování a chyby Qt jdou také do logu.
"""
import logging
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

from cesty import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_SOUBOR = LOG_DIR / "kupcake.log"
MAX_BAJTU, ZALOH = 1_000_000, 3
log = logging.getLogger("kupcake")
_most = None


def nastav():
    """Volá se jednou při startu (main), před vytvořením oken."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in log.handlers):
        soubor = RotatingFileHandler(LOG_SOUBOR, maxBytes=MAX_BAJTU, backupCount=ZALOH, encoding="utf-8")
        soubor.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(threadName)s: %(message)s"))
        log.addHandler(soubor)
        if sys.stderr is not None:  # vývoj (run_dev.bat) – i do konzole
            konzole = logging.StreamHandler()
            konzole.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            log.addHandler(konzole)
    from version import VERZE
    log.info("=== kupcake.studio %s spuštěno ===", VERZE)
    sys.excepthook = _vyjimka
    threading.excepthook = lambda a: _vyjimka(a.exc_type, a.exc_value, a.exc_traceback)
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
        urovne = {QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
                  QtMsgType.QtFatalMsg: logging.CRITICAL}
        qInstallMessageHandler(lambda typ, kontext, zprava: log.log(urovne.get(typ, logging.DEBUG), "Qt: %s", zprava))
    except ImportError:
        pass


def hlaseni(zprava, detail=""):
    """Text pro „Zkopírovat hlášení“: verze a systém + chyba."""
    try:
        import hardware
        system = hardware.info_o_systemu()
    except Exception as e:  # hlášení musí jít sestavit vždycky
        system = f"(informace o systému nejdou zjistit: {e})"
    return f"{system}\n\nChyba: {zprava}\n\n{detail}".strip() + f"\n\nLog: {bez_profilu(str(LOG_SOUBOR))}"


def bez_profilu(text):
    """Cesta do profilu uživatele (C:\\Users\\jmeno\\…) → %LOCALAPPDATA% / %APPDATA% / %USERPROFILE%: hlášení
    chyby, které uživatel někam vloží, tak neprozradí jeho uživatelské jméno."""
    import os
    for promenna in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        hodnota = os.environ.get(promenna)
        if hodnota:
            text = text.replace(hodnota, f"%{promenna}%").replace(hodnota.replace("\\", "/"), f"%{promenna}%")
    return text


def srozumitelne(chyba, text):
    """Známé příčiny selhání přeloží do lidské řeči (plný text zůstane v podrobnostech a logu)."""
    import errno
    import urllib.error

    from i18n import t
    nizke = text.lower()
    if getattr(chyba, "errno", None) == errno.ENOSPC or "no space left" in nizke or "not enough space" in nizke \
            or "disk full" in nizke:
        return t("chyba.misto")
    if isinstance(chyba, (urllib.error.URLError, ConnectionError, TimeoutError)) or "getaddrinfo" in nizke \
            or "urlopen error" in nizke or "connection" in nizke and "refused" in nizke:
        return t("chyba.offline", chyba=text[-300:])
    if "does not contain any stream" in nizke or "matches no streams" in nizke:
        return t("chyba.bez_zvuku")
    return text[-1500:]


def _vyjimka(typ, hodnota, tb):
    if issubclass(typ, KeyboardInterrupt):
        sys.__excepthook__(typ, hodnota, tb)
        return
    detail = "".join(traceback.format_exception(typ, hodnota, tb))
    log.error("Nezachycená výjimka:\n%s", detail)
    if _most is not None:  # z jakéhokoli vlákna – dialog se ukáže v hlavním (signál je ve frontě)
        _most.chyba.emit(f"{typ.__name__}: {hodnota}", detail)


def zapni_dialogy(okno):
    """Po vytvoření hlavního okna: nezachycené výjimky ukážou dialog (most do hlavního vlákna)."""
    global _most
    from PySide6.QtCore import QObject, Signal

    class Most(QObject):
        chyba = Signal(str, str)

    _most = Most(okno)
    _most.chyba.connect(lambda zprava, detail: ukaz_chybu(okno, zprava, detail))


_otevreno = [False]


def ukaz_chybu(rodic, zprava, detail="", uvod=None):
    """Srozumitelná chybová hláška: co se stalo, že aplikace běží dál, a „Zkopírovat hlášení“."""
    if _otevreno[0]:  # další chyba během otevřené hlášky – jen do logu
        return
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout)

    from i18n import t
    _otevreno[0] = True
    text = bez_profilu(hlaseni(zprava, detail))  # i v tracebacku: žádné uživatelské jméno z cest
    dlg = QDialog(rodic)
    dlg.setWindowTitle(t("chyba.titulek"))
    dlg.setMinimumWidth(560)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(10)
    popis = QLabel(uvod or t("chyba.neocekavana"))
    popis.setWordWrap(True)
    lay.addWidget(popis)
    kratce = QLabel(zprava[:600])
    kratce.setWordWrap(True)
    kratce.setObjectName("stav")
    kratce.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(kratce)
    podrobnosti = QPlainTextEdit(text)
    podrobnosti.setReadOnly(True)
    podrobnosti.setMinimumHeight(160)
    podrobnosti.hide()
    lay.addWidget(podrobnosti)
    radek = QHBoxLayout()
    vice = QPushButton(t("chyba.podrobnosti"))
    vice.setObjectName("sekundarni")
    vice.clicked.connect(lambda: (podrobnosti.setVisible(not podrobnosti.isVisible()), dlg.adjustSize()))
    kopirovat = QPushButton(t("chyba.kopirovat"))
    kopirovat.setObjectName("primary")

    def zkopiruj():
        QGuiApplication.clipboard().setText(text)
        kopirovat.setText(t("chyba.zkopirovano"))
        QTimer.singleShot(2500, kopirovat, lambda: kopirovat.setText(t("chyba.kopirovat")))
    kopirovat.clicked.connect(zkopiruj)
    zavrit = QPushButton(t("oaplikaci.zavrit"))
    zavrit.setObjectName("sekundarni")
    zavrit.clicked.connect(dlg.accept)
    radek.addWidget(vice)
    radek.addStretch(1)
    radek.addWidget(kopirovat)
    radek.addWidget(zavrit)
    lay.addLayout(radek)
    try:
        dlg.exec()
    finally:
        _otevreno[0] = False
        dlg.deleteLater()
