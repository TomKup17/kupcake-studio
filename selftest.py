"""Samokontrola sestavené aplikace: KupcakeStudio.exe --selftest <video> <protokol.txt>

Ověří, že build obsahuje vše potřebné (rozhraní, dokování, jazyky, fonty, ikony, licence, přepis na GPU,
časovou osu, přehrávač a export) a výsledek zapíše do protokolu. Nastavení uživatele nepoužívá ani
nemění – vše běží v dočasné složce. Návratový kód 0 = vše prošlo.
"""
import shutil
import tempfile
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QByteArray, QPoint, QSettings, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import cesty
import i18n
import theme


class Selftest:
    def __init__(self, m, video, protokol):
        self.m, self.video, self.protokol = m, Path(video), Path(protokol)
        self.radky, self.chyby = [], 0
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_selftest_"))
        # vlastní nastavení jen pro test
        m.NASTAVENI_DIR = self.tmp
        m.STYL_SOUBOR = self.tmp / "styl.json"
        i18n.nastaveni = lambda: QSettings(str(self.tmp / "aplikace.ini"), QSettings.IniFormat)
        i18n.nastav("cs")
        # poškozené uložené rozvržení (jako po nekompatibilní starší verzi) – aplikace musí použít výchozí
        s = QSettings(str(self.tmp / "rozlozeni.ini"), QSettings.IniFormat)
        s.setValue("verze", str(m.ROZLOZENI_VERZE))
        s.setValue("dok/stav", QByteArray(b"<QtAdvancedDockingSystem><nesmysl"))
        s.sync()
        self.kroky = [self.staticke, self.okno, self.jazyky, self.prepis, self.osa, self.prehravac,
                      self.sekce_nahled, self.dokovani, self.styly, self.export]
        self.w = None

    def zapis(self, nazev, ok, detail=""):
        self.radky.append(f"[{'OK ' if ok else 'CHYBA'}] {nazev}{' – ' + str(detail) if detail else ''}")
        if not ok:
            self.chyby += 1

    def kontrola(self, nazev, fn):
        try:
            ok, detail = fn()
        except Exception:
            ok, detail = False, traceback.format_exc().strip().splitlines()[-1]
        self.zapis(nazev, ok, detail)
        return ok

    def cekej(self, podminka, limit, hotovo):
        """Neblokující čekání: hotovo() se zavolá, až platí podminka() nebo vyprší limit (s)."""
        konec = time.monotonic() + limit

        def tik():
            if podminka() or time.monotonic() > konec:
                hotovo()
            else:
                QTimer.singleShot(200, tik)
        tik()

    def dalsi(self):
        if not self.kroky:
            return self.konec()
        krok = self.kroky.pop(0)
        try:
            krok()
        except Exception:
            self.zapis(krok.__name__, False, traceback.format_exc().strip().splitlines()[-1])
            QTimer.singleShot(0, self.dalsi)

    # ---------- kroky ----------
    def staticke(self):
        rodiny = set(QFontDatabase.families())
        for pismo in ("Inter", "JetBrains Mono", "Montserrat"):
            self.kontrola(f"písmo {pismo}", lambda p=pismo: (any(r.startswith(p) for r in rodiny), ""))
        self.kontrola("ikony", lambda: (not theme.ikona("sekce_osa.svg").isNull()
                                         and len(list((cesty.APP_DIR / "ikony").glob("*.svg"))) > 10,
                                         f"{len(list((cesty.APP_DIR / 'ikony').glob('*.svg')))} SVG"))
        lic = sorted(p.name for p in (cesty.APP_DIR / "licenses").glob("*.txt"))
        self.kontrola("licence", lambda: (len(lic) >= 5 and (cesty.APP_DIR / "THIRD_PARTY_LICENSES.md").is_file(),
                                          ", ".join(lic)))
        self.kontrola("FFmpeg", lambda: (bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe")),
                                         shutil.which("ffmpeg")))
        self.kontrola("libmpv", lambda: ((cesty.APP_DIR / "mpv" / "libmpv-2.dll").is_file(), ""))
        self.kontrola("PySide6-QtAds", lambda: (__import__("PySide6QtAds") is not None, ""))
        QTimer.singleShot(0, self.dalsi)

    def okno(self):
        self.w = self.m.Okno()
        self.w.zobraz()
        self.kontrola("hlavní okno a sekce", lambda: (
            sorted(self.w.dok.sekce) == ["nahled", "nastaveni", "osa", "titulky"] and self.w.isVisible(),
            ", ".join(d.windowTitle() for d in self.w.dok.sekce.values())))
        QTimer.singleShot(500, self.dalsi)

    def jazyky(self):
        nazvy = {}
        for kod, _ in i18n.dostupne():
            i18n.nastav(kod)
            titulek = self.w.dok.sekce["osa"].windowTitle()
            nazvy[kod] = (titulek, i18n.t("menu.soubor"), i18n._qt_preklad is not None or kod == "en")
        i18n.nastav("cs")
        ok = (len(nazvy) >= 5 and len({v[0] for v in nazvy.values()}) == len(nazvy)
              and all("." not in v[1] for v in nazvy.values()) and all(v[2] for v in nazvy.values()))
        self.zapis("jazyky rozhraní", ok, "; ".join(f"{k}: {v[0]}" for k, v in nazvy.items()))
        QTimer.singleShot(0, self.dalsi)

    def prepis(self):
        import model
        if not model.je_pripraven():
            self.zapis("přepis", False, "model řeči není stažený – test přepisu přeskočen")
            self.kroky = [k for k in self.kroky if k not in (self.osa, self.export)]
            self.w.otevri(self.video, "cs")  # bez modelu by se začal stahovat – jen načtení videa
            return QTimer.singleShot(0, self.dalsi)
        zacatek = time.monotonic()
        self.w.otevri(self.video, "cs")
        # překrytí s cupcakem: viditelné, průběh dojde do konce a nikdy necouvá, fáze se hlásí
        prekryti, prubeh, faze = self.w.prekryti.isVisible(), [], []
        self.w.uloha.progress.connect(prubeh.append)
        self.w.uloha.faze.connect(faze.append)

        def hotovo():
            self.kontrola("překrytí s cupcakem a průběhem", lambda: (
                prekryti and bool(prubeh) and max(prubeh) >= 0.99
                and all(b >= a - 1e-6 for a, b in zip(prubeh, prubeh[1:])) and "prepis" in faze,
                f"hlášení průběhu {len(prubeh)}, fáze: {', '.join(dict.fromkeys(faze))}"))
            self.kontrola("přepis", lambda: (bool(self.w.titulky), f"titulků {len(self.w.titulky)}, "
                                             f"{time.monotonic() - zacatek:.0f} s, "
                                             f"{getattr(self.w, 'zarizeni_prepisu', '')}"))
            self.kontrola("nečitelné uložené rozvržení → výchozí", lambda: (
                all(not d.isClosed() for d in self.w.dok.sekce.values()), "všechny sekce vidět"))
            import torch
            import zarovnani
            self.kontrola("přesné časování (wav2vec2)", lambda: (
                self.w.zarovnano, f"PyTorch {torch.__version__}, {zarovnani.zarizeni()}"))
            self.kontrola("oddělení hlasu (Demucs)", lambda: (
                __import__("demucs.apply").apply is not None and __import__("julius") is not None, "knihovna načtena"))
            self.dalsi()
        self.cekej(lambda: not self.w.zaneprazdneno() and bool(self.w.titulky), 600, hotovo)

    def osa(self):
        def hotovo():
            o = self.w.osa
            self.kontrola("časová osa", lambda: (len(o.slova) > 0 and o.vlna is not None,
                                                 f"slov {len(o.slova)}, vlna {'ano' if o.vlna is not None else 'ne'}"))
            self.dalsi()
        self.cekej(lambda: self.w.osa.vlna is not None, 60, hotovo)

    def prehravac(self):
        p = self.w.prehravac
        if not p:
            self.zapis("přehrávač", False, "mpv se nenačetl")
            return QTimer.singleShot(0, self.dalsi)
        p.skoc(0.0)
        p.prepni()

        def hotovo():
            t = p.t
            p.prepni()
            self.zapis("přehrávač mpv", t > 0.5, f"po 1,5 s přehrávání t = {t:.2f} s")
            self.dalsi()
        QTimer.singleShot(1500, hotovo)

    def sekce_nahled(self):
        """Náhled přesouvaný na všechny strany, jako záložka, plovoucí, maximalizovaný: tlačítko Přehrát
        musí být jediné, v sekci a bez vlastního nativního okna; nativní okno plochy videa na místě."""
        import ctypes
        from ctypes import wintypes

        import PySide6QtAds as ads
        from prehravac import PlayTlacitko
        d, w = self.w.dok, self.w
        dw = d.sekce["nahled"]
        p = w.prehravac
        if not p:
            self.zapis("přesouvání sekce Náhled", False, "chybí přehrávač")
            return QTimer.singleShot(0, self.dalsi)

        def kotvi(oblast, k):
            return lambda: d.m.addDockWidget(oblast, dw, d.sekce[k].dockAreaWidget())

        kroky = [("vlevo", kotvi(ads.LeftDockWidgetArea, "titulky")),
                 ("vpravo", kotvi(ads.RightDockWidgetArea, "nastaveni")),
                 ("nahoře", kotvi(ads.TopDockWidgetArea, "osa")),
                 ("dole", kotvi(ads.BottomDockWidgetArea, "osa")),
                 ("záložka", kotvi(ads.CenterDockWidgetArea, "nastaveni")),
                 ("plovoucí", dw.setFloating),
                 ("zpět", kotvi(ads.RightDockWidgetArea, "titulky")),
                 ("maximalizace", lambda: d.prepni_maximalizaci(dw)),
                 ("obnovení", lambda: d.prepni_maximalizaci(dw)),
                 ("výchozí", w.vychozi_rozlozeni)]
        chyby = []

        def zkontroluj(nazev):
            tlacitka = {id(x) for x in QApplication.allWidgets() if isinstance(x, PlayTlacitko)}
            nativni = [x for x in (p.btn_play, p.posuvnik, p.lbl_cas) if x.internalWinId()]
            r = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(wintypes.HWND(int(p.plocha.winId())), ctypes.byref(r))
            k = p.plocha.devicePixelRatioF()
            o = p.plocha.mapToGlobal(QPoint(0, 0))
            na_miste = abs(r.left - o.x() * k) <= 2 and abs(r.top - o.y() * k) <= 2
            if len(tlacitka) != 1 or nativni or not dw.isAncestorOf(p.btn_play) or not na_miste:
                chyby.append(nazev)

        def krok():
            if not kroky:
                self.zapis("přesouvání sekce Náhled", not chyby,
                           f"10 poloh, jedno tlačítko Přehrát na místě{'; chyby: ' + ', '.join(chyby) if chyby else ''}")
                return QTimer.singleShot(300, self.dalsi)
            nazev, fn = kroky.pop(0)
            fn()
            QTimer.singleShot(500, lambda: (zkontroluj(nazev), krok()))
        krok()

    def styly(self):
        """Presety a tečky „liší se od presetu“ ve skupinách Nastavení."""
        w = self.w
        pole = w.panel.prvky["velikost"]
        pole.setValue(pole.value() + 1.5)
        tecka_po_zmene = not w.panel.skupiny["text"].tecka.isHidden()
        w.presety.uloz("Selftest", w.styl)
        w._obnov_presety()
        bez_tecek = all(s.tecka.isHidden() for s in w.panel.skupiny.values())
        ulozeno = (self.tmp / "presety.json").is_file()
        w.pouzij_preset("")
        vychozi = abs(w.styl.velikost - type(w.styl)().velikost) < 1e-9
        self.zapis("styly a presety", tecka_po_zmene and bez_tecek and ulozeno and vychozi,
                   "tečka po změně, preset uložen, výchozí preset obnoven")
        QTimer.singleShot(0, self.dalsi)

    def dokovani(self):
        dw = self.w.dok.sekce["nahled"]
        dw.setFloating()

        def hotovo():
            ok = dw.isInFloatingContainer() and self.w.prehravac is not None
            try:
                self.w.prehravac.mpv.pause
            except Exception:
                ok = False
            self.w.dok.obnov(self.w._vychozi_stav)
            self.zapis("dokování (Náhled v samostatném okně)", ok and not dw.isInFloatingContainer())
            self.dalsi()
        QTimer.singleShot(800, hotovo)

    def export(self):
        from export import Export
        from titulky import video_info, vytvor_ass
        W, H, delka = self.w.info
        vystup = self.tmp / "selftest_export.mp4"
        zacatek = time.monotonic()

        def kontrola():
            Export().vypal(self.video, vytvor_ass(self.w.titulky, self.w.styl, W, H), vystup, delka, lambda p: None)
            info = video_info(vystup)
            return (vystup.stat().st_size > 0 and abs(info[2] - delka) < 0.5,
                    f"{vystup.stat().st_size // 1024} kB, {info[0]}×{info[1]}, {info[2]:.2f} s, "
                    f"{time.monotonic() - zacatek:.1f} s")
        def pruhledne():
            import json as _json
            import subprocess
            import export as ex
            from titulky import vyrez, vytvor_srt
            v = ex.Volby(co="pruhledne")
            f = self.tmp / "selftest_pruhledne.mov"
            ex.Export().vypal(self.video, vytvor_ass(vyrez(self.w.titulky, 0, 2), self.w.styl, W, H), f, 2.0,
                              volby=v, info=self.w.info, fps_zdroj=self.w.fps, rozsah=(0.0, 2.0))
            data = _json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,pix_fmt",
                                               "-of", "json", str(f)], capture_output=True, text=True,
                                              creationflags=ex.NO_WINDOW).stdout)["streams"][0]
            srt = vytvor_srt(self.w.titulky, self.w.styl)
            return (data["codec_name"] == "prores" and data["pix_fmt"].startswith("yuva") and srt.startswith("1\n"),
                    f"{data['codec_name']} {data['pix_fmt']}, SRT {srt.count('-->')} titulků")
        self.kontrola("průhledné titulky (ProRes 4444) a SRT", pruhledne)
        import export as ex_
        if self.kontrola(f"export (FFmpeg, {ex_.kodek(ex_.Volby())})", kontrola):
            self.w.export_hotov(vystup)
            self.kontrola("notifikace „Export dokončen“", lambda: (self.w.notifikace.isVisible(), ""))
            self.w.notifikace.skryj()
        QTimer.singleShot(0, self.dalsi)

    def konec(self):
        self.radky.insert(0, f"{cesty.NAZEV} {cesty.VERZE} – samokontrola ({'vše OK' if not self.chyby else f'chyb: {self.chyby}'})")
        self.protokol.write_text("\n".join(self.radky) + "\n", encoding="utf-8")
        if self.w:
            self.w.neulozeno = False  # test nic neukládá – zavřít bez dotazu na neuložený projekt
            self.w.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        QApplication.instance().exit(1 if self.chyby else 0)


def spust(m, video, protokol):
    test = Selftest(m, video, protokol)
    QTimer.singleShot(0, test.dalsi)
    return test
