# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Stahování modelů: povolené adresy a přesměrování, integrita (SHA-256, velikost), navázání, značka .hotovo."""
import _zaklad  # noqa: F401  – izolace a sys.path

import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import stahovani
from stahovani import ChybaOvereni, Odmitnuto, over_url


class FalesnaOdpoved:
    """Náhrada za odpověď urllib: status, hlavičky a tělo po blocích; chyba_po = po kolika bajtech spadne spojení."""

    def __init__(self, data, status=200, hlavicky=None, chyba_po=None):
        self.data, self.status, self.headers = data, status, dict(hlavicky or {})
        self.chyba_po, self.precteno = chyba_po, 0
        self.tok = io.BytesIO(data)

    def read(self, n=-1):
        if self.chyba_po is not None and self.precteno >= self.chyba_po:
            raise ConnectionError("spojení přerušeno")
        if self.chyba_po is not None:
            n = min(n if n > 0 else len(self.data), self.chyba_po - self.precteno)
        blok = self.tok.read(n)
        self.precteno += len(blok)
        return blok

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestAdresy(unittest.TestCase):
    def test_povolene(self):
        for url in ("https://huggingface.co/Systran/x/resolve/abc/model.bin",
                    "https://dl.fbaipublicfiles.com/demucs/x.th", "https://huggingface.co:443/x"):
            self.assertEqual(over_url(url), url)

    def test_presmerovani_na_cdn(self):
        for url in ("https://cdn-lfs.hf.co/repos/x", "https://cdn-lfs-us-1.huggingface.co/x",
                    "https://cas-bridge.xethub.hf.co/x", "https://huggingface.co/x"):
            self.assertEqual(over_url(url, presmerovani=True), url)

    def test_cdn_neni_povolene_jako_start(self):
        with self.assertRaises(ChybaOvereni):
            over_url("https://cdn-lfs.hf.co/x")

    def test_zakazane(self):
        spatne = [
            "http://huggingface.co/x",                     # ne HTTPS
            "https://evil.example/x",                      # cizí doména
            "https://huggingface.co.evil.example/x",       # doména „začínající“ povoleným jménem
            "https://xhf.co/x", "https://hf.co/x",         # přípona bez tečky / jen holá doména CDN
            "https://127.0.0.1/x", "https://[::1]/x",      # localhost IP
            "https://10.0.0.1/x", "https://192.168.1.1/x", "https://169.254.169.254/latest/meta-data",
            "https://localhost/x", "https://foo.localhost/x",
            "https://huggingface.co:8443/x",               # jiný port (interní služba)
            "https://user:heslo@huggingface.co/x",         # přihlašovací údaje v adrese
            "ftp://huggingface.co/x", "file:///C:/Windows/x", "data:text/plain,x",
            "", "https://", "not a url", "https://[zzz/x", "https://huggingface.co:abc/x",
        ]
        for url in spatne:
            with self.subTest(url=url):
                with self.assertRaises(ChybaOvereni):
                    over_url(url)
                with self.assertRaises(ChybaOvereni):
                    over_url(url, presmerovani=True)

    def test_redirect_handler_odmitne_cizi(self):
        h = stahovani._JenHttps()
        req = mock.Mock()
        for url in ("http://huggingface.co/x", "https://evil.example/x", "https://10.1.1.1/x"):
            with self.assertRaises(ChybaOvereni):
                h.redirect_request(req, None, 302, "Found", {}, url)

    def test_redirect_handler_limit(self):
        self.assertLessEqual(stahovani._JenHttps.max_redirections, 5)

    def test_otevirac_neumi_http(self):
        for url in ("http://huggingface.co/x", "ftp://huggingface.co/x", "file:///C:/x"):
            with self.assertRaises((urllib.error.URLError, ValueError)):
                stahovani._otevirac.open(url, timeout=1)

    def test_otevri_odmitne_pred_pripojenim(self):
        with mock.patch.object(stahovani._otevirac, "open", side_effect=AssertionError("nemělo se připojit")):
            with self.assertRaises(ChybaOvereni):
                stahovani._otevri("https://evil.example/x")


class TestStahniSoubor(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_dl_"))
        self.data = os.urandom(3 * stahovani.BLOK + 12345)
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.cil = self.tmp / "model.bin"
        self.ukazatel = stahovani.Ukazatel(len(self.data), "model.stahuji", lambda p: None, lambda s: None)

    def _server(self, odpovedi):
        """Falešný _otevri: vrací připravené odpovědi (fronta); zaznamená požadované offsety."""
        self.pozadavky = []

        def otevri(url, od=0):
            self.pozadavky.append(od)
            return odpovedi.pop(0)(od)
        return mock.patch.object(stahovani, "_otevri", otevri)

    def test_stazeni_ok(self):
        with self._server([lambda od: FalesnaOdpoved(self.data, 200, {"Content-Length": str(len(self.data))})]):
            stahovani.stahni_soubor("https://huggingface.co/x", self.cil, len(self.data), self.sha, self.ukazatel)
        self.assertEqual(self.cil.read_bytes(), self.data)
        self.assertFalse(self.cil.with_name("model.bin.part").exists())

    def test_spatny_sha_smaze(self):
        jina = bytes(len(self.data))  # stejná velikost, jiný obsah
        with self._server([lambda od: FalesnaOdpoved(jina, 200, {"Content-Length": str(len(jina))})]):
            with self.assertRaises(ChybaOvereni):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, len(self.data), self.sha, self.ukazatel)
        self.assertFalse(self.cil.exists())
        self.assertFalse(self.cil.with_name("model.bin.part").exists())

    def test_jina_velikost_podle_hlavicky_se_odmitne_hned(self):
        o = FalesnaOdpoved(self.data + b"x", 200, {"Content-Length": str(len(self.data) + 1)})
        with self._server([lambda od: o]):
            with self.assertRaises(ChybaOvereni):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, len(self.data), self.sha, self.ukazatel)
        self.assertEqual(o.precteno, 0)  # nic se nečetlo
        self.assertFalse(self.cil.exists())

    def test_delsi_obsah_bez_hlavicky_se_odmitne(self):
        with self._server([lambda od: FalesnaOdpoved(self.data + b"navic", 200)]):
            with self.assertRaises(ChybaOvereni):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, len(self.data), self.sha, self.ukazatel)
        self.assertFalse(self.cil.exists())

    def test_kratsi_obsah_se_odmitne(self):
        with self._server([lambda od: FalesnaOdpoved(self.data[:-100], 200)]):
            with self.assertRaises(ChybaOvereni):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, len(self.data), self.sha, self.ukazatel)
        self.assertFalse(self.cil.exists())

    def test_prerusene_a_navazani(self):
        n = len(self.data)
        polovina = n // 2

        def prvni(od):
            return FalesnaOdpoved(self.data, 200, {"Content-Length": str(n)}, chyba_po=polovina)

        def druha(od):
            self.assertEqual(od, polovina)
            return FalesnaOdpoved(self.data[od:], 206, {"Content-Range": f"bytes {od}-{n - 1}/{n}"})
        with self._server([prvni, druha]):
            with self.assertRaises(ConnectionError):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, n, self.sha, self.ukazatel)
            cast = self.cil.with_name("model.bin.part")
            self.assertTrue(cast.exists())
            self.assertEqual(cast.stat().st_size, polovina)
            self.assertFalse(self.cil.exists())  # neúplný soubor se nikdy nevydává za hotový
            stahovani.stahni_soubor("https://huggingface.co/x", self.cil, n, self.sha, self.ukazatel)
        self.assertEqual(self.pozadavky, [0, polovina])
        self.assertEqual(self.cil.read_bytes(), self.data)

    def test_navazani_s_jinym_celkem_se_odmitne(self):
        n = len(self.data)
        self.cil.with_name("model.bin.part").write_bytes(self.data[:1000])
        with self._server([lambda od: FalesnaOdpoved(b"", 206, {"Content-Range": f"bytes 1000-{n + 9}/{n + 10}"})]):
            with self.assertRaises(ChybaOvereni):
                stahovani.stahni_soubor("https://huggingface.co/x", self.cil, n, self.sha, self.ukazatel)
        self.assertFalse(self.cil.with_name("model.bin.part").exists())

    def test_server_neumi_range(self):
        n = len(self.data)
        self.cil.with_name("model.bin.part").write_bytes(b"nesmysl")
        with self._server([lambda od: FalesnaOdpoved(self.data, 200, {"Content-Length": str(n)})]):
            stahovani.stahni_soubor("https://huggingface.co/x", self.cil, n, self.sha, self.ukazatel)
        self.assertEqual(self.cil.read_bytes(), self.data)

    def test_part_vetsi_nez_cil_se_zahodi(self):
        n = len(self.data)
        self.cil.with_name("model.bin.part").write_bytes(self.data + b"x" * 10)
        with self._server([lambda od: FalesnaOdpoved(self.data, 200, {"Content-Length": str(n)})]):
            stahovani.stahni_soubor("https://huggingface.co/x", self.cil, n, self.sha, self.ukazatel)
        self.assertEqual(self.pozadavky, [0])
        self.assertEqual(self.cil.read_bytes(), self.data)


class TestZnackaAOvereni(unittest.TestCase):
    """Falešný malý „model“ v manifestu: ověření, značka s otiskem, změna souboru, změna metadat."""
    REPO = "test/maly-model"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_repo_"))
        self.soubory = {"config.json": b'{"a": 1}\n', "model.bin": os.urandom(70000)}
        manifest = {self.REPO: {"revize": "abc123", "soubory": {
            f: (len(d), hashlib.sha256(d).hexdigest()) for f, d in self.soubory.items()}}}
        self.p_manifest = mock.patch.dict(stahovani.HUGGINGFACE, manifest)
        self.p_manifest.start()
        self.p_souhlas = mock.patch.object(stahovani, "_souhlas", lambda popis, velikost, zdroj: False)  # nic nestahovat
        self.p_souhlas.start()
        self.p_sit = mock.patch.object(stahovani, "_otevri", side_effect=AssertionError("nemělo se připojit"))
        self.p_sit.start()
        for f, d in self.soubory.items():
            (self.tmp / f).write_bytes(d)

    def tearDown(self):
        self.p_manifest.stop()
        self.p_souhlas.stop()
        self.p_sit.stop()

    def test_bez_znacky_se_overi_a_zapise_otisk(self):
        self.assertFalse(stahovani.je_pripraveno(self.REPO, self.tmp))
        stahovani.priprav_repo(self.REPO, self.tmp, "test")
        znacka = json.loads((self.tmp / stahovani.ZNACKA).read_text())
        self.assertEqual(znacka["revize"], "abc123")
        self.assertEqual(set(znacka["soubory"]), set(self.soubory))
        self.assertTrue(stahovani.je_pripraveno(self.REPO, self.tmp))

    def test_stara_znacka_bez_otisku_vynuti_overeni(self):
        (self.tmp / stahovani.ZNACKA).write_text(json.dumps({"repo": self.REPO, "revize": "abc123"}))
        self.assertFalse(stahovani.je_pripraveno(self.REPO, self.tmp))
        stahovani.priprav_repo(self.REPO, self.tmp, "test")
        self.assertTrue(stahovani.je_pripraveno(self.REPO, self.tmp))

    def test_podvrzena_znacka_neobejde_kontrolu(self):
        """Útočník (nebo chyba disku) změní obsah souboru a zapíše značku „ověřeno“ – soubor se stejně zkontroluje."""
        stahovani.priprav_repo(self.REPO, self.tmp, "test")
        spatny = bytes(len(self.soubory["model.bin"]))
        (self.tmp / "model.bin").write_bytes(spatny)  # stejná velikost, jiný obsah → jiný čas změny
        self.assertFalse(stahovani.je_pripraveno(self.REPO, self.tmp))
        # i když si otisk ve značce „opraví“ na nový čas změny – ověření SHA-256 ho odhalí
        znacka = json.loads((self.tmp / stahovani.ZNACKA).read_text())
        znacka["soubory"]["model.bin"] = stahovani._otisk(self.tmp / "model.bin")
        (self.tmp / stahovani.ZNACKA).write_text(json.dumps(znacka))
        self.assertTrue(stahovani.je_pripraveno(self.REPO, self.tmp))  # otisk sedí – ale:
        os.utime(self.tmp / "model.bin")  # jakákoli další změna otisku → nové ověření
        self.assertFalse(stahovani.je_pripraveno(self.REPO, self.tmp))
        with self.assertRaises(Odmitnuto):  # ověření selže → nabídne stažení → odmítnuto (test nic nestahuje)
            stahovani.priprav_repo(self.REPO, self.tmp, "test")
        self.assertFalse((self.tmp / "model.bin").exists())  # poškozený soubor je pryč
        self.assertFalse((self.tmp / stahovani.ZNACKA).exists())

    def test_jina_revize_v_manifestu(self):
        stahovani.priprav_repo(self.REPO, self.tmp, "test")
        with mock.patch.dict(stahovani.HUGGINGFACE[self.REPO], {"revize": "nova"}):
            self.assertFalse(stahovani.je_pripraveno(self.REPO, self.tmp))

    def test_chybejici_soubor_vyzaduje_souhlas(self):
        (self.tmp / "model.bin").unlink()
        with self.assertRaises(Odmitnuto):
            stahovani.priprav_repo(self.REPO, self.tmp, "test")

    def test_kopie_z_cache_overuje(self):
        cache = self.tmp / "cache"
        cache.mkdir()
        cil = self.tmp / "cil"
        for f, d in self.soubory.items():
            (cache / f).write_bytes(d)
        self.assertTrue(stahovani.kopiruj_overene(cache, self.REPO, cil))
        self.assertTrue(stahovani.je_pripraveno(self.REPO, cil))
        (cache / "model.bin").write_bytes(bytes(len(self.soubory["model.bin"])))
        cil2 = self.tmp / "cil2"
        self.assertFalse(stahovani.kopiruj_overene(cache, self.REPO, cil2))
        self.assertFalse((cil2 / "model.bin").exists())


class TestDemucs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kupcake_demucs_"))
        self.data = os.urandom(5000)
        self.demucs = {"url": "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/test-1234.th",
                       "velikost": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()}
        self.p = mock.patch.dict(stahovani.DEMUCS, self.demucs)
        self.p.start()
        self.p_souhlas = mock.patch.object(stahovani, "_souhlas", lambda *a: False)
        self.p_souhlas.start()

    def tearDown(self):
        self.p.stop()
        self.p_souhlas.stop()

    def test_overeny_soubor_a_znacka(self):
        soubor = self.tmp / "test-1234.th"
        soubor.write_bytes(self.data)
        with mock.patch.object(stahovani, "_otevri", side_effect=AssertionError("síť")):
            self.assertEqual(stahovani.priprav_demucs(self.tmp, "test"), soubor)
            self.assertEqual(stahovani.priprav_demucs(self.tmp, "test"), soubor)  # podruhé bez hashování
        znacka = json.loads((self.tmp / stahovani.ZNACKA).read_text())
        self.assertEqual(znacka["sha256"], self.demucs["sha256"])
        self.assertIn("test-1234.th", znacka["soubory"])

    def test_podvrzeny_soubor_se_smaze_a_nestahne_bez_souhlasu(self):
        soubor = self.tmp / "test-1234.th"
        soubor.write_bytes(bytes(len(self.data)))
        (self.tmp / stahovani.ZNACKA).write_text(json.dumps({"sha256": self.demucs["sha256"]}))  # stará značka
        with mock.patch.object(stahovani, "_otevri", side_effect=AssertionError("síť")):
            with self.assertRaises(Odmitnuto):
                stahovani.priprav_demucs(self.tmp, "test")
        self.assertFalse(soubor.exists())

    def test_stazeni_demucs(self):
        n = len(self.data)
        with mock.patch.object(stahovani, "_souhlas", lambda *a: True), \
                mock.patch.object(stahovani, "_otevri",
                                  lambda url, od=0: FalesnaOdpoved(self.data, 200, {"Content-Length": str(n)})):
            soubor = stahovani.priprav_demucs(self.tmp, "test")
        self.assertEqual(soubor.read_bytes(), self.data)
        self.assertTrue((self.tmp / stahovani.ZNACKA).exists())

    def test_nepovolena_adresa_v_manifestu(self):
        with mock.patch.dict(stahovani.DEMUCS, {"url": "https://evil.example/x.th"}):
            with self.assertRaises(ChybaOvereni):
                stahovani.priprav_demucs(self.tmp, "test")


if __name__ == "__main__":
    unittest.main()
