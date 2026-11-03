"""Kontrola aktualizací: jen oznámení a odkaz, žádné stahování; podvržené odpovědi API se neprojeví."""
import _zaklad  # noqa: F401

import io
import json
import threading
import unittest
import urllib.error
from unittest import mock

import aktualizace
import links


class FalesnaOdpoved(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _api(data, status=200):
    telo = data if isinstance(data, bytes) else json.dumps(data).encode()
    return mock.patch.object(aktualizace._otevirac, "open", lambda req, timeout=0: FalesnaOdpoved(telo, status))


class TestVerze(unittest.TestCase):
    def test_porovnani(self):
        self.assertTrue(aktualizace.je_novejsi("1.0.1", "1.0.0"))
        self.assertTrue(aktualizace.je_novejsi("v1.0.0", "1.0.0-beta.2"))
        self.assertTrue(aktualizace.je_novejsi("1.0.0-beta.2", "1.0.0-beta.1"))
        self.assertFalse(aktualizace.je_novejsi("1.0.0-beta.1", "1.0.0"))
        self.assertFalse(aktualizace.je_novejsi("0.9.9", "1.0.0"))
        for nesmysl in ("", "abc", "1.0", None, 5, "1.0.0; rm -rf", "x" * 100):
            self.assertFalse(aktualizace.je_novejsi(nesmysl, "1.0.0"))
            self.assertIsNone(aktualizace._rozloz(nesmysl))


class TestStrankaVydani(unittest.TestCase):
    def test_jen_github_repozitar(self):
        repo = "uzivatel/kupcake-studio"
        ok = f"https://github.com/{repo}/releases/tag/v1.0.1"
        self.assertEqual(aktualizace.stranka_vydani(repo, ok), ok)
        zaloha = f"https://github.com/{repo}/releases"
        for spatne in ("http://github.com/uzivatel/kupcake-studio/releases/tag/v1", "https://evil.example/x",
                       "https://github.com/jiny/repo/releases", "https://github.com.evil.example/uzivatel/kupcake-studio/",
                       "https://user@github.com/uzivatel/kupcake-studio/x", "javascript:alert(1)", "", None, 42,
                       "https://github.com:8443/uzivatel/kupcake-studio/x", "https://[zz/"):
            self.assertEqual(aktualizace.stranka_vydani(repo, spatne), zaloha)


class TestNejnovejsi(unittest.TestCase):
    REPO = "uzivatel/kupcake-studio"

    def test_bezna_odpoved(self):
        with _api([{"tag_name": "v1.0.0-beta.3", "prerelease": True, "draft": False,
                    "html_url": f"https://github.com/{self.REPO}/releases/tag/v1.0.0-beta.3"}]):
            self.assertEqual(aktualizace.nejnovejsi(self.REPO, predbezne=True),
                             ("1.0.0-beta.3", f"https://github.com/{self.REPO}/releases/tag/v1.0.0-beta.3"))
            self.assertIsNone(aktualizace.nejnovejsi(self.REPO, predbezne=False))

    def test_podvrzena_adresa_se_nahradi(self):
        with _api([{"tag_name": "9.9.9", "html_url": "https://evil.example/instalator.exe"}]):
            self.assertEqual(aktualizace.nejnovejsi(self.REPO, predbezne=False),
                             ("9.9.9", f"https://github.com/{self.REPO}/releases"))

    def test_nesmyslne_odpovedi(self):
        for data in ({"message": "rate limit"}, "text", [1, 2, "x", None], [{"tag_name": "nesmysl"}],
                     [{"tag_name": "1.0.0", "draft": True}], b"{neni json", b"\xff\xfe"):
            with self.subTest(data=data), _api(data):
                self.assertIsNone(aktualizace.nejnovejsi(self.REPO, predbezne=True))

    def test_chybovy_stav_http(self):
        with _api([], status=500):
            self.assertIsNone(aktualizace.nejnovejsi(self.REPO))

    def test_prilis_velka_odpoved(self):
        with _api(b"[" + b" " * (aktualizace.MAX_ODPOVED + 10) + b"]"):
            self.assertIsNone(aktualizace.nejnovejsi(self.REPO))

    def test_sitova_chyba(self):
        with mock.patch.object(aktualizace._otevirac, "open", side_effect=urllib.error.URLError("offline")):
            self.assertIsNone(aktualizace.nejnovejsi(self.REPO))

    def test_spatny_repozitar(self):
        for repo in ("", "jen", "../x", "a/b/c", "a/../b", "a b/c"):
            with mock.patch.object(aktualizace._otevirac, "open", side_effect=AssertionError("nemělo se ptát")):
                self.assertIsNone(aktualizace.nejnovejsi(repo))

    def test_presmerovani_jen_na_api(self):
        h = aktualizace._JenApi()
        for url in ("http://api.github.com/x", "https://evil.example/x", "https://github.com/x"):
            with self.assertRaises(urllib.error.URLError):
                h.redirect_request(mock.Mock(), None, 302, "Found", {}, url)

    def test_otevirac_jen_https(self):
        with self.assertRaises((urllib.error.URLError, ValueError)):
            aktualizace._otevirac.open("http://api.github.com/x", timeout=1)


class FalesneNastaveni(dict):
    def value(self, klic, vychozi=None):
        return self.get(klic, vychozi)

    def setValue(self, klic, hodnota):
        self[klic] = hodnota

    def sync(self):
        pass


class TestNaPozadi(unittest.TestCase):
    def _spust(self, nastaveni, vysledek):
        hotovo = []
        udalost = threading.Event()
        puvodni = threading.Thread.start

        def start(self_):
            puvodni(self_)
            self_.join(5)
            udalost.set()
        with mock.patch.object(links, "GITHUB_REPO", "uzivatel/kupcake-studio"), \
                mock.patch.object(aktualizace, "nejnovejsi", lambda: vysledek), \
                mock.patch.object(threading.Thread, "start", start):
            aktualizace.zkontroluj_na_pozadi(nastaveni, lambda v, u: hotovo.append((v, u)))
        return hotovo

    def test_vypnuto(self):
        self.assertEqual(self._spust(FalesneNastaveni({"aktualizace/zapnuto": "false"}), ("9.9.9", "u")), [])

    def test_nedavno_kontrolovano(self):
        import time
        n = FalesneNastaveni({"aktualizace/posledni": time.time()})
        self.assertEqual(self._spust(n, ("9.9.9", "u")), [])

    def test_vadna_hodnota_posledni_kontroly(self):
        n = FalesneNastaveni({"aktualizace/posledni": "nesmysl"})
        self.assertEqual(self._spust(n, ("9.9.9", "https://github.com/x")), [("9.9.9", "https://github.com/x")])
        self.assertIsInstance(n["aktualizace/posledni"], float)

    def test_preskocena_a_starsi(self):
        self.assertEqual(self._spust(FalesneNastaveni({"aktualizace/preskocit": "9.9.9"}), ("9.9.9", "u")), [])
        self.assertEqual(self._spust(FalesneNastaveni(), ("0.0.1", "u")), [])
        self.assertEqual(self._spust(FalesneNastaveni(), None), [])

    def test_bez_repozitare_nic(self):
        with mock.patch.object(links, "GITHUB_REPO", ""), \
                mock.patch.object(threading.Thread, "start", side_effect=AssertionError("vlákno")):
            aktualizace.zkontroluj_na_pozadi(FalesneNastaveni(), lambda v, u: None)


if __name__ == "__main__":
    unittest.main()
