# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Licenční dokumenty a podmínky použití: hlavičky ve zdrojových souborech, dodatečné svolení, podmínky
v aplikaci i v instalátoru, seznam licencí třetích stran a texty rozhraní ve všech jazycích."""
import _zaklad  # noqa: F401  – izolace a sys.path

import json
import re
import unittest
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
SVOLENI = ("Additional permission under GNU GPL version 3 section 7: If you modify this Program, or any covered "
           "work, by linking or combining it with the NVIDIA CUDA and cuDNN runtime libraries or the Intel Math Kernel "
           "Library (or modified versions of those libraries), containing parts covered by the terms of their "
           "respective licenses, the licensors of this Program grant you additional permission to convey the "
           "resulting work.")
VYNECHAT = {".venv", "build", "dist", "__pycache__", ".git"}


def cti(soubor):
    return (KOREN / soubor).read_text(encoding="utf-8")


def zdrojove_soubory():
    for cesta in KOREN.rglob("*"):
        if cesta.is_file() and cesta.suffix in (".py", ".bat", ".spec", ".iss") \
                and not (set(cesta.relative_to(KOREN).parts) & VYNECHAT):
            yield cesta


class TestLicenceKodu(unittest.TestCase):
    def test_hlavicka_ve_vsech_zdrojovych_souborech(self):
        soubory = list(zdrojove_soubory())
        self.assertGreater(len(soubory), 50)
        for cesta in soubory:
            zacatek = cesta.read_text(encoding="utf-8-sig")[:400]
            with self.subTest(soubor=str(cesta.relative_to(KOREN))):
                self.assertIn("Copyright (C) 2026 Tomáš Kupec", zacatek)
                self.assertIn("SPDX-License-Identifier: GPL-3.0-only", zacatek)

    def test_license(self):
        text = cti("LICENSE")
        self.assertTrue(text.startswith("Copyright (C) 2026 Tomáš Kupec\nSPDX-License-Identifier: GPL-3.0-only\n"))
        self.assertIn("GNU GENERAL PUBLIC LICENSE", text)
        self.assertIn("Version 3, 29 June 2007", text)
        self.assertIn("END OF TERMS AND CONDITIONS", text)

    def test_dodatecne_svoleni_doslova(self):
        for soubor in ("ADDITIONAL_PERMISSION.md", "README.md", "README.cs.md"):
            with self.subTest(soubor=soubor):
                self.assertIn(SVOLENI, " ".join(cti(soubor).replace("> ", "").split()))

    def test_readme_rika_co_neni_pod_gpl(self):
        for soubor, slova in (("README.md", ("GPL-3.0-only", "NVIDIA", "Intel", "not under the GPL", "trademarks",
                                             "patent", "Claude Code", "Earlier working names")),
                              ("README.cs.md", ("GPL-3.0-only", "NVIDIA", "Intel", "nejsou pod GPL", "ochranné známky",
                                                "patentovým", "Claude Code", "Dřívější pracovní názvy"))):
            text = cti(soubor)
            for slovo in slova:
                with self.subTest(soubor=soubor, slovo=slovo):
                    self.assertIn(slovo, text)


class TestPodminky(unittest.TestCase):
    def test_obe_jazykove_verze(self):
        en, cs = cti("TERMS.md"), cti("TERMS.cs.md")
        self.assertEqual(len(re.findall(r"(?m)^## ", en)), len(re.findall(r"(?m)^## ", cs)))
        for text in (en, cs):
            for slovo in ("Tomáš Kupec (iamtom.kup)", "https://tomkup.cz", "github.com/TomKup17/kupcake-studio/issues",
                          "GPL-3.0-only", "CC BY-NC 4.0", "api.github.com", "ProRes"):
                self.assertIn(slovo, text)
            self.assertNotIn("IČO", text)
        self.assertIn("to the extent permitted by law", en)
        self.assertIn("v rozsahu, v jakém to zákon dovoluje", cs)
        self.assertIn("Czech Republic", en)
        self.assertIn("České republiky", cs)
        # knihovny NVIDIA: jen s aplikací, za podmínek licencí NVIDIA
        self.assertIn("You may use these libraries only together with this app", en)
        self.assertIn("Tyto knihovny smíš používat jen spolu s touto aplikací", cs)

    def test_stranka_instalatoru_odpovida_podminkam(self):
        import sys
        sys.path.insert(0, str(KOREN / "nastroje"))
        import podminky_txt
        ulozene = (KOREN / "installer" / "PODMINKY.txt").read_bytes()
        self.assertEqual(ulozene, podminky_txt.vytvor(), "spusť nastroje\\podminky_txt.py – TERMS.cs.md se změnil")
        self.assertTrue(ulozene.startswith(b"\xef\xbb\xbf"))  # UTF-8 s BOM (Inno Setup)
        text = ulozene[3:].decode("utf-8")
        self.assertNotIn("\n", text.replace("\r\n", ""))        # jen CRLF
        for znacka in ("**", "`", "](", "## "):
            self.assertNotIn(znacka, text)                        # prostý text, žádný Markdown
        self.assertIn("Podmínky použití", text)

    def test_instalator(self):
        data = (KOREN / "installer" / "KupcakeStudio.iss").read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))        # .iss musí zůstat UTF-8 s BOM
        text = data[3:].decode("utf-8")
        self.assertIn("LicenseFile=PODMINKY.txt", text)
        self.assertIn("8E1F3C52-6A4D-4B8E-9C7A-3D2E5F1A7B90", text)  # AppId se nemění
        self.assertIn("nastroje\\podminky_txt.py", cti("build.bat"))

    def test_pribaleno_v_aplikaci(self):
        spec = cti("KupcakeStudio.spec")
        for soubor in ("TERMS.md", "TERMS.cs.md", "ADDITIONAL_PERMISSION.md", "LICENSE", "THIRD_PARTY_LICENSES.md",
                       '("licenses", "licenses")'):
            self.assertIn(soubor, spec)

    def test_texty_v_aplikaci(self):
        import i18n
        import o_aplikaci
        i18n.nastav("cs")
        self.assertIn("Podmínky použití", o_aplikaci.text_podminek())
        i18n.nastav("sk")
        self.assertIn("Podmínky použití", o_aplikaci.text_podminek())  # slovensky se ukážou české
        i18n.nastav("en")
        podminky = o_aplikaci.text_podminek()
        self.assertIn("Terms of Use", podminky)
        self.assertNotIn("](TERMS", podminky)                    # přepínač jazyka se v aplikaci neukazuje
        licence = o_aplikaci.text_licence()
        self.assertIn("Additional permission under GNU GPL version 3 section 7", licence)
        self.assertIn("FFmpeg", licence)
        # odkazy na soubory projektu vedou na GitHub, odkazy na oddíly stránky jsou obyčejný text
        self.assertNotRegex(licence, r"\]\((?!https?://)[^)]*\)")
        self.assertIn("https://github.com/TomKup17/kupcake-studio/blob/main/LICENSE", licence)
        i18n.nastav("cs")


class TestSeznamLicenci(unittest.TestCase):
    def test_tretí_strany(self):
        text = cti("THIRD_PARTY_LICENSES.md")
        for slovo in ("mpv v0.41.0-1227-ge471496c5", "9.0.2", "libx264", "libx265", "Silero VAD", "lameenc", "LAME",
                      "hf-xet", "Python", "OpenSSL", "SQLite", "libffi", "expat", "Intel oneAPI Math Kernel Library",
                      "Intel OpenMP", "Microsoft Visual C++", "dropbox-dash/faster-whisper-large-v3-turbo",
                      "Zdrojové kódy přibalených programů", "Zdrojové kódy na požádání poskytnu",
                      "qt-everywhere-src-6.12.0", "Qt-Advanced-Docking-System/tree/v5.1.1", "lame-4.0.tar.gz",
                      "pyav-ffmpeg/tree/9.0.2-1", "mpv-winbuild-cmake/releases/tag/20261021", "nejsou pod GPL"):
            with self.subTest(slovo=slovo):
                self.assertIn(slovo, text)
        self.assertNotIn("LGPL v2.1+ (mpv)", text)               # toto sestavení mpv je GPL
        self.assertNotIn("uroman-MIT.txt", text)                 # licence uromanu není čistá MIT
        for soubor in re.findall(r"`((?:python/)?[A-Za-z0-9_.+-]+\.txt)`", text):
            with self.subTest(soubor=soubor):
                self.assertTrue((KOREN / "licenses" / soubor).is_file(), f"chybí licenses/{soubor}")

    def test_seznam_balicku_pythonu(self):
        text = cti("licenses/PYTHON_PACKAGES.md")
        radky = re.findall(r"(?m)^\| ([^|]+) \| ([^|]+) \| ([^|]+) \| `(python/[^`]+)` \|$", text)
        self.assertGreater(len(radky), 40)
        for nazev, verze, licence, soubor in radky:
            with self.subTest(balicek=nazev):
                obsah = (KOREN / "licenses" / soubor).read_text(encoding="utf-8")
                self.assertTrue(obsah.startswith(f"{nazev} {verze}\nLicence: {licence}\n"))
                self.assertGreater(len(obsah), 400, "chybí plné znění licence")
        nazvy = {r[0].lower() for r in radky}
        for balicek in ("torch", "pyside6", "av", "lameenc", "hf-xet", "faster-whisper", "numpy", "python-mpv"):
            self.assertIn(balicek, nazvy)


class TestTextyRozhrani(unittest.TestCase):
    NOVE = ("mms.nastaveni", "mms.upozorneni", "stahovani.zarovnani_mms", "log.zarovnani_bez_modelu",
            "varovani.zarovnat_bez_modelu", "reci.presne_bez_modelu", "oaplikaci.podminky", "oaplikaci.podminky_chybi")

    def test_vsech_pet_jazyku(self):
        jazyky = {j: json.loads(cti(f"locales/{j}.json")) for j in ("cs", "sk", "en", "de", "es")}
        for jazyk, texty in jazyky.items():
            self.assertEqual(set(texty), set(jazyky["cs"]), jazyk)
            for klic in self.NOVE:
                self.assertTrue(texty.get(klic), f"{jazyk}: {klic}")
            self.assertIn("GitHub", texty["uvitani.text"])          # věta o kontrole nových verzí
            self.assertIn("CC BY-NC 4.0", texty["mms.upozorneni"])
            self.assertIn("CC BY-NC 4.0", texty["stahovani.zarovnani_mms"])
            self.assertIn("{model}", texty["stahovani.zarovnani_mms"])
            self.assertIn("{jazyk}", texty["log.zarovnani_bez_modelu"])
            self.assertIn("GPL-3.0-only", texty["oaplikaci.licence_text"])
            self.assertIn("NVIDIA", texty["oaplikaci.licence_text"])
        for soubor in ("cs", "sk", "en", "de", "es"):                # zápis: CRLF, odsazení 2 mezery
            data = (KOREN / "locales" / f"{soubor}.json").read_bytes()
            self.assertEqual(data, (json.dumps(jazyky[soubor], ensure_ascii=False, indent=2) + "\n")
                             .replace("\n", "\r\n").encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
