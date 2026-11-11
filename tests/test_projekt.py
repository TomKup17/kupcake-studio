# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Projekty .kupcake: poškozené a podvržené soubory, atomické ukládání, hledání videa."""
import _zaklad  # noqa: F401

import base64
import json
import tempfile
import unittest
from pathlib import Path

import projekt
from projekt import ChybaProjektu
from titulky import Slovo, Styl, Titulek, Znacka


def _data(tmp, **zmeny):
    d = projekt.sestav(tmp / "video.mp4", (1920, 1080, 12.5),
                       [Titulek(0.5, 1.5, "ahoj světe", [Slovo("ahoj", 0.5, 0.9), Slovo("světe", 1.0, 1.5)], True)],
                       [Znacka(2.0, "pozn")], Styl(velikost=0.12), [{"text": "ahoj", "start": 0.5, "end": 0.9}],
                       "cs", 0.04, True, (1.0, 2.0), b"<QtAdvancedDockingSystem/>", tmp / "p.kupcake", "1.0.0")
    d.update(zmeny)
    return d


class TestProjekt(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_proj_"))
        self.cesta = self.tmp / "p.kupcake"

    def _uloz(self, data):
        projekt.uloz(self.cesta, data)
        return self.cesta

    def test_tam_a_zpet(self):
        v = projekt.nacti(self._uloz(_data(self.tmp)))
        self.assertEqual(v["video"], self.tmp / "video.mp4")
        self.assertEqual(v["video_relativni"], "video.mp4")
        self.assertEqual(v["info"], (1920.0, 1080.0, 12.5))
        self.assertEqual(len(v["titulky"]), 1)
        self.assertEqual(v["titulky"][0].slova[1].text, "světe")
        self.assertTrue(v["titulky"][0].zamceno)
        self.assertEqual(v["znacky"][0].t, 2.0)
        self.assertEqual(v["styl"].velikost, 0.12)
        self.assertEqual(v["slova"], [{"text": "ahoj", "start": 0.5, "end": 0.9}])
        self.assertEqual((v["jazyk"], v["posun_zvuku"], v["zarovnano"]), ("cs", 0.04, True))
        self.assertEqual(v["smycka"], (1.0, 2.0))
        self.assertEqual(v["rozvrzeni"], b"<QtAdvancedDockingSystem/>")

    def test_neni_json_nebo_neni_projekt(self):
        for obsah in (b"{neni json", b"", b"[1,2,3]", b'"text"', b'{"jiny": 1}', b"\x00\x01\x02", b"\xff\xfe\x00"):
            self.cesta.write_bytes(obsah)
            with self.subTest(obsah=obsah), self.assertRaises(ChybaProjektu):
                projekt.nacti(self.cesta)

    def test_neexistujici_soubor(self):
        with self.assertRaises(ChybaProjektu):
            projekt.nacti(self.tmp / "neni.kupcake")

    def test_format(self):
        for f in ("abc", None, [], {}, 99, "99"):
            self.cesta.write_text(json.dumps({"kupcake.studio": f, "video": {"cesta": "x"}}), encoding="utf-8")
            with self.subTest(f=f), self.assertRaises(ChybaProjektu):
                projekt.nacti(self.cesta)

    def test_poskozene_casti(self):
        spatne = [
            {"video": "text"}, {"video": {}}, {"video": {"cesta": 5}}, {"video": {"cesta": "x", "relativni": 7}},
            {"video": {"cesta": "x", "info": "nesmysl"}}, {"video": {"cesta": "x", "info": [1, "a"]}},
            {"titulky": "ne"}, {"titulky": [{"start": "0", "end": 1, "text": "x"}]},
            {"titulky": [{"start": 0, "end": 1, "text": 5}]}, {"titulky": [{"start": 0, "end": 1}]},
            {"titulky": [{"start": 0, "end": 1, "text": "x", "slova": [["a", "b", 1]]}]},
            {"titulky": [{"start": True, "end": 1, "text": "x"}]},
            {"znacky": [{"t": "x"}]}, {"znacky": [{"text": "bez času"}]}, {"znacky": {"t": 1}},
            {"smycka": ["a", "b"]}, {"smycka": "1,2"},
            {"rozvrzeni": "ne base64 !!"}, {"rozvrzeni": 12},
            {"prepis": {"posun_zvuku": "hodně"}},
        ]
        for zmena in spatne:
            data = _data(self.tmp)
            data.update(zmena)
            self.cesta.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(zmena=zmena), self.assertRaises(ChybaProjektu):
                projekt.nacti(self.cesta)

    def test_nekonecne_casy(self):
        self.cesta.write_text(json.dumps(_data(self.tmp)).replace('"start": 0.5', '"start": 1e999', 1), encoding="utf-8")
        with self.assertRaises(ChybaProjektu):
            projekt.nacti(self.cesta)

    def test_mekke_casti_se_zahodi(self):
        """Nepodstatné části ve špatném tvaru se nahradí výchozími – projekt se otevře."""
        data = _data(self.tmp)
        data["prepis"] = {"slova": [{"text": 1}], "jazyk": 42, "zarovnano": "ano"}
        data["styl"] = {"velikost": "velká", "font": 3, "neznamy": 1}
        data["smycka"] = [1]  # neúplná smyčka = žádná smyčka
        v = projekt.nacti(self._uloz(data))
        self.assertEqual(v["slova"], [])
        self.assertIsNone(v["jazyk"])
        self.assertEqual(v["styl"], Styl())
        self.assertIsNone(v["smycka"])
        data["prepis"] = "text"
        v = projekt.nacti(self._uloz(data))
        self.assertEqual(v["slova"], [])

    def test_prilis_velky_soubor(self):
        with open(self.cesta, "wb") as f:
            f.seek(projekt.MAX_VELIKOST + 1)
            f.write(b"}")
        with self.assertRaises(ChybaProjektu):
            projekt.nacti(self.cesta)

    def test_atomicke_ulozeni_zachova_stary(self):
        self._uloz(_data(self.tmp))
        puvodni = self.cesta.read_bytes()
        with self.assertRaises(TypeError):
            projekt.uloz(self.cesta, {"kupcake.studio": 1, "x": object()})  # nejde serializovat
        self.assertEqual(self.cesta.read_bytes(), puvodni)
        self.assertFalse(self.cesta.with_name("p.kupcake.tmp").exists())

    def test_ulozeni_do_neexistujici_slozky(self):
        cesta = self.tmp / "nova" / "slozka" / "p.kupcake"
        projekt.uloz(cesta, _data(self.tmp))
        self.assertTrue(cesta.is_file())

    def test_najdi_video(self):
        (self.tmp / "video.mp4").write_bytes(b"x")
        v = projekt.nacti(self._uloz(_data(self.tmp)))
        self.assertEqual(projekt.najdi_video(v, self.cesta), self.tmp / "video.mp4")
        v["video"] = Path("C:/neexistuje/video.mp4")
        self.assertEqual(projekt.najdi_video(v, self.cesta), (self.tmp / "video.mp4").resolve())
        v["video_relativni"] = "..\\..\\..\\Windows\\System32\\neexistuje.mp4"
        self.assertIsNone(projekt.najdi_video(v, self.cesta))
        v["video"] = Path("\x00nesmysl")
        self.assertIsNone(projekt.najdi_video(v, self.cesta))

    def test_bom_a_unicode(self):
        self.cesta.write_text(json.dumps(_data(self.tmp), ensure_ascii=False), encoding="utf-8-sig")
        self.assertEqual(projekt.nacti(self.cesta)["titulky"][0].text, "ahoj světe")


if __name__ == "__main__":
    unittest.main()
