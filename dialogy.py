"""Menší dialogy: výběr jazyka řeči a možností přepisu (přesnost, odhad doby, zařízení)."""
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

import i18n
from i18n import t
from jazyky_reci import serazene

AUTO = "auto"
PRESNOSTI = ("large-v3", "turbo", "medium")   # Nejpřesnější, Rychlá, Úsporná
REZIMY = ("auto", "cpu")                       # přepis počítat na: automaticky / jen procesor


def moznosti_prepisu():
    """(přesné časování, oddělit hlas) – poslední volba z dialogu; přesné časování je ve výchozím stavu zapnuté."""
    s = i18n.nastaveni()
    return (str(s.value("prepis/presne", "true")).lower() == "true",
            str(s.value("prepis/oddelit_hlas", "false")).lower() == "true")


def presnost_prepisu():
    hodnota = i18n.nastaveni().value("prepis/model", "large-v3")
    return hodnota if hodnota in PRESNOSTI else "large-v3"


def rezim_prepisu():
    hodnota = i18n.nastaveni().value("prepis/zarizeni", "auto")
    return hodnota if hodnota in REZIMY else "auto"


def uloz_prepis(klic, hodnota):
    s = i18n.nastaveni()
    s.setValue(klic, hodnota)
    s.sync()


def fmt_odhad(s):
    if s < 55:
        return t("odhad.sekundy", s=max(int(round(s / 5) * 5), 5))
    return t("odhad.minuty", m=max(int(round(s / 60)), 1))


def popis_prepisu(model, delka, presne, hw=None):
    """„Přepis poběží na: … · odhad: asi 2 min“ (+ velikost modelu, když ještě není stažený)."""
    import hardware
    import model as modely
    hw = hw or hardware.zjisti()
    zarizeni, compute = hardware.volba(model, rezim_prepisu(), hw)
    text = t("prepis.bezi_na", zarizeni=hardware.popis(zarizeni, hw))
    if zarizeni == "cpu":  # bez NVIDIA / CUDA (nebo vynucený procesor) – říct to předem a jasně
        text = t("prepis.cpu_pomalejsi" if not hw.gpu or not hw.cuda else "prepis.cpu_vynuceno") + "\n" + text
    if delka:
        text += " · " + t("odhad.text", cas=fmt_odhad(hardware.odhad_s(delka, model, zarizeni, compute, presne,
                                                                        hw.vlakna)))
    if not modely.je_stazen(model):  # stažený, jen ještě neověřený model se nestahuje – jen ověří
        text += "\n" + t("presnost.stahne_se", velikost=f"{modely.velikost(model) / 1e9:.1f} GB")
    return text


def vyber_jazyk_reci(rodic, nazev_videa="", delka=0.0):
    """Zeptá se na jazyk řeči a možnosti přepisu. Vrátí kód jazyka, None (= rozpoznat automaticky), nebo False
    (zrušeno). Poslední volba se pamatuje a příště je předvybraná; možnosti čte moznosti_prepisu()."""
    dlg = QDialog(rodic)
    dlg.setWindowTitle(t("reci.titulek"))
    dlg.setMinimumWidth(420)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(10)
    popis = QLabel(t("reci.popis") + (f"\n{nazev_videa}" if nazev_videa else ""))
    popis.setWordWrap(True)
    lay.addWidget(popis)

    volba = QComboBox()
    volba.setMaxVisibleItems(18)
    volba.addItem(t("reci.auto"), AUTO)
    volba.insertSeparator(volba.count())
    oblibene, ostatni = serazene()
    for kod, nazev in oblibene:
        volba.addItem(nazev, kod)
    volba.insertSeparator(volba.count())
    for kod, nazev in ostatni:
        volba.addItem(nazev, kod)
    posledni = i18n.nastaveni().value("jazyk/prepis") or AUTO
    i = volba.findData(posledni)
    volba.setCurrentIndex(i if i >= 0 else 0)
    lay.addWidget(volba)

    presne_puv, hlas_puv = moznosti_prepisu()
    presne = QCheckBox(t("reci.presne"))
    presne.setToolTip(t("reci.presne_tip"))
    presne.setChecked(presne_puv)
    hlas = QCheckBox(t("reci.oddelit_hlas"))
    hlas.setToolTip(t("reci.oddelit_tip"))
    hlas.setChecked(hlas_puv)
    lay.addWidget(presne)
    lay.addWidget(hlas)

    # přesnost přepisu (model) s vysvětlením, zařízení a odhad doby
    import hardware
    hw = hardware.zjisti()
    lay.addSpacing(4)
    lay.addWidget(QLabel(t("presnost.nadpis")))
    model = QComboBox()
    for klic in PRESNOSTI:
        model.addItem(t(f"presnost.{klic}"), klic)
        model.setItemData(model.count() - 1, t(f"presnost.{klic}.popis"), 3)  # 3 = Qt.ToolTipRole
    model.setCurrentIndex(max(model.findData(presnost_prepisu()), 0))
    lay.addWidget(model)
    vysvetleni = QLabel()
    vysvetleni.setObjectName("stav")
    vysvetleni.setWordWrap(True)
    lay.addWidget(vysvetleni)
    info = QLabel()
    info.setObjectName("stav")
    info.setWordWrap(True)
    lay.addWidget(info)

    def obnov():
        klic = model.currentData()
        vysvetleni.setText(t(f"presnost.{klic}.popis"))
        info.setText(popis_prepisu(klic, delka, presne.isChecked(), hw))
    model.currentIndexChanged.connect(obnov)
    presne.toggled.connect(obnov)
    obnov()

    tlacitka = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    tlacitka.button(QDialogButtonBox.Ok).setText(t("reci.prepsat"))
    tlacitka.button(QDialogButtonBox.Ok).setObjectName("primary")  # hlavní akce (AI přepis) – oranžová
    tlacitka.button(QDialogButtonBox.Cancel).setObjectName("sekundarni")
    tlacitka.accepted.connect(dlg.accept)
    tlacitka.rejected.connect(dlg.reject)
    lay.addWidget(tlacitka)
    volba.setFocus()

    prijato = dlg.exec() == QDialog.Accepted
    kod = volba.currentData()
    volby = presne.isChecked(), hlas.isChecked()
    zvoleny_model = model.currentData()
    # uklidit v Qt hned po zavření – jinak dialog (cyklus odkazů přes signály) visí, dokud ho nenajde Python GC
    dlg.deleteLater()
    if not prijato:
        return False
    s = i18n.nastaveni()
    s.setValue("jazyk/prepis", kod)
    s.setValue("prepis/presne", "true" if volby[0] else "false")
    s.setValue("prepis/oddelit_hlas", "true" if volby[1] else "false")
    s.setValue("prepis/model", zvoleny_model)
    return None if kod == AUTO else kod
