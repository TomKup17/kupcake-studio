# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""FFmpeg a soubory: argumenty jako seznam bez shellu, jen místní soubory, zdroj se nepřepisuje, ASS escapování."""
import _zaklad  # noqa: F401

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import export
import titulky
from cesty import vstup_ffmpeg
from export import PrepisZdroje, Volby, je_stejny_soubor, sestav_prikaz


class TestVstupFFmpeg(unittest.TestCase):
    def test_jen_mistni_soubory_a_absolutni_cesta(self):
        tmp = Path(tempfile.mkdtemp())
        for jmeno in ("-evil.mp4", "http:video.mp4", "concat:a|b.mp4", "video s mezerou.mp4", "ü.mp4"):
            args = vstup_ffmpeg(tmp / jmeno)
            self.assertEqual(args[:3], ["-protocol_whitelist", "file", "-i"])
            self.assertTrue(Path(args[3]).is_absolute())
            self.assertFalse(args[3].startswith("-"))
            self.assertTrue(args[3].endswith(jmeno))
        args = vstup_ffmpeg(tmp / "x.mp4", ffprobe=True)
        self.assertEqual(args[:2], ["-protocol_whitelist", "file"])
        self.assertEqual(len(args), 3)


class TestPrikaz(unittest.TestCase):
    def test_seznam_bez_shellu(self):
        video = Path("C:/videa/zdroj; rm -rf x.mp4")
        for volby in (Volby(), Volby(co="pruhledne"), Volby(format="h265", preset="youtube", normalizace=True),
                      Volby(format="mov", rozsah="usek")):
            with mock.patch.object(export, "nvenc_dostupny", lambda k: False):
                cmd = sestav_prikaz(volby, video, Path("C:/out/vystup.mp4"), (1080, 1920, 10.0), 30.0, (1.0, 3.0))
            self.assertIsInstance(cmd, list)
            self.assertTrue(all(isinstance(a, str) for a in cmd))
            self.assertNotIn("-vendor", cmd)  # ProRes bez značky výrobce apl0 (výchozí značka kodéru FFmpeg)
            self.assertEqual(cmd[0], "ffmpeg")
            self.assertEqual(cmd[-1], str(Path("C:/out/vystup.mp4")))
            if volby.co != "pruhledne":
                i = cmd.index("-i")
                self.assertEqual(cmd[i - 2:i], ["-protocol_whitelist", "file"])
                self.assertEqual(cmd[i + 1], str(video.resolve()))
            # titulky vždy z pevné relativní cesty v datové složce, ne z uživatelské cesty
            self.assertTrue(any(a.startswith("subtitles=filename=tmp/titulky.ass") or
                                "subtitles=filename=tmp/titulky.ass" in a for a in cmd))

    def test_popen_bez_shellu(self):
        """Export spouští FFmpeg seznamem argumentů; shell=True se nikde nepoužije."""
        tmp = Path(tempfile.mkdtemp())
        video, vystup = tmp / "a.mp4", tmp / "b.mp4"
        video.write_bytes(b"x")
        volani = {}

        class FalesnyProces:
            stdout = iter(())
            returncode = 0

            def wait(self):
                pass

            def poll(self):
                return 0

        def popen(cmd, **kw):
            volani["cmd"], volani["kw"] = cmd, kw
            return FalesnyProces()
        with mock.patch.object(subprocess, "Popen", popen), mock.patch.object(export, "nvenc_dostupny", lambda k: False):
            export.Export().vypal(video, "[Script Info]\n", vystup, 1.0, info=(16, 16, 1.0))
        self.assertIsInstance(volani["cmd"], list)
        self.assertFalse(volani["kw"].get("shell", False))
        self.assertTrue((export.TMP_DIR / "titulky.ass").is_file())


class TestPrepisZdroje(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_exp_"))
        self.video = self.tmp / "Video.MP4"
        self.video.write_bytes(b"x")

    def test_stejny_soubor(self):
        self.assertTrue(je_stejny_soubor(self.video, self.tmp / "video.mp4"))  # jiná velikost písmen (Windows)
        self.assertTrue(je_stejny_soubor(self.video, self.tmp / "sub" / ".." / "Video.MP4"))
        self.assertFalse(je_stejny_soubor(self.video, self.tmp / "jine.mp4"))
        self.assertFalse(je_stejny_soubor(self.video, self.tmp / "neexistuje.mp4"))

    def test_export_odmitne_prepsat_zdroj(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("FFmpeg se nesmí spustit")):
            with self.assertRaises(PrepisZdroje):
                export.Export().vypal(self.video, "", self.tmp / "video.mp4", 1.0, info=(16, 16, 1.0))
        self.assertEqual(self.video.read_bytes(), b"x")


class TestVolby(unittest.TestCase):
    def test_z_dict_ignoruje_spatne_typy(self):
        v = Volby.z_dict({"format": 5, "nvenc": "ano", "slozka": "C:/x", "neznamy": 1, "co": "titulky"})
        self.assertEqual((v.format, v.nvenc, v.slozka, v.co), ("h264", True, "C:/x", "titulky"))
        self.assertEqual(Volby.z_dict(None), Volby())


class TestASS(unittest.TestCase):
    def test_escape_titulku(self):
        self.assertEqual(titulky._escape("{\\an5}x"), "\\{\\⁠an5\\}x")
        self.assertNotIn("\\N", titulky._escape("a\\Nb"))
        self.assertEqual(titulky._escape("a\nb"), "a\\Nb")
        ass = titulky.vytvor_ass([titulky.Titulek(0, 1, "{\\pos(0,0)}x")], titulky.Styl(velka_pismena=False), 100, 100)
        self.assertNotIn("{\\pos(0,0)}x", ass)
        self.assertIn("\\{\\⁠pos(0,0)\\}x", ass)

    def test_vtt_html(self):
        vtt = titulky.vytvor_vtt([titulky.Titulek(0, 1, "<b>a</b> --> c")], titulky.Styl(velka_pismena=False))
        self.assertNotIn("<b>", vtt)
        self.assertIn("&lt;b&gt;", vtt)


if __name__ == "__main__":
    unittest.main()
