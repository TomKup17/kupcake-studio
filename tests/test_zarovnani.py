# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Přesné časování: vícejazyčný model MMS (jen nekomerční licence) je ve výchozím stavu vypnutý; jazyky bez
vlastního modelu pak čistě zůstávají na časech z přepisu. Model Whisper turbo pod novou adresou repozitáře
nevynutí nové stažení."""
import _zaklad  # noqa: F401  – izolace a sys.path

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import i18n
import model
import stahovani
import zarovnani


class TestMMS(unittest.TestCase):
    def setUp(self):
        zarovnani.nastav_mms(False)
        self.addCleanup(zarovnani.nastav_mms, False)

    def test_vychozi_je_vypnuto(self):
        self.assertFalse(zarovnani.POUZIT_MMS)
        i18n.nastaveni().remove(zarovnani.KLIC_MMS)  # nikdy nenastaveno = výchozí
        self.assertFalse(zarovnani.mms_zapnuto())

    def test_jazyky_s_vlastnim_modelem(self):
        for jazyk in ("cs", "sk", "en", "de", "es", "fr", "it", "pl"):
            self.assertTrue(zarovnani.ma_model(jazyk))
            self.assertNotEqual(zarovnani.repo_pro(jazyk), zarovnani.MMS)

    def test_ostatni_jazyky_bez_mms(self):
        for jazyk in ("ja", "uk", "hu", None, ""):
            self.assertFalse(zarovnani.ma_model(jazyk))
            with self.assertRaises(zarovnani.BezModelu):
                zarovnani.repo_pro(jazyk)
        self.assertTrue(issubclass(zarovnani.BezModelu, LookupError))

    def test_zapnuti_v_nastaveni(self):
        zarovnani.nastav_mms(True)
        self.assertTrue(zarovnani.mms_zapnuto())
        self.assertTrue(zarovnani.ma_model("ja"))
        self.assertEqual(zarovnani.repo_pro("ja"), zarovnani.MMS)
        self.assertNotEqual(zarovnani.repo_pro("cs"), zarovnani.MMS)  # vlastní model má přednost
        zarovnani.nastav_mms(False)
        self.assertFalse(zarovnani.ma_model("ja"))

    def test_zarovnani_bez_modelu_nic_nestahuje(self):
        """Bez MMS se pro neznámý jazyk nenačte žádný model ani nezačne stahování."""
        with mock.patch.object(stahovani, "priprav_repo", side_effect=AssertionError("nemělo se stahovat")), \
                mock.patch.object(stahovani, "je_pripraveno", side_effect=AssertionError("nemělo se ptát")):
            with self.assertRaises(zarovnani.BezModelu):
                zarovnani.zarovnavac("ja")

    def test_dotaz_na_stazeni_mms_uvadi_licenci(self):
        i18n.nastav("cs")
        popisy = []
        with mock.patch.object(stahovani, "je_pripraveno", return_value=False), \
                mock.patch.object(stahovani, "priprav_repo", lambda repo, cil, popis, **kw: popisy.append(popis)):
            zarovnani._stahni(zarovnani.MMS, lambda s: None)
            zarovnani._stahni(zarovnani.MODELY["cs"], lambda s: None)
        self.assertIn("CC BY-NC 4.0", popisy[0])
        self.assertIn("nekomerční", popisy[0])
        self.assertNotIn("CC BY-NC", popisy[1])

    def test_prepis_preskoci_zarovnani_bez_chyby(self):
        """prepis.py: jazyk bez modelu není „selhání“ – ohlásí se klidnou zprávou a zarovnání se nespustí."""
        zdroj = (Path(zarovnani.__file__).parent / "prepis.py").read_text(encoding="utf-8")
        self.assertIn('not zarovnani.ma_model(vys["jazyk"])', zdroj)
        self.assertIn('"log.zarovnani_bez_modelu"', zdroj)
        i18n.nastav("cs")
        zprava = i18n.t("log.zarovnani_bez_modelu", jazyk="ja")
        self.assertIn("ja", zprava)
        self.assertNotIn("selhal", zprava)


class TestModelTurbo(unittest.TestCase):
    STARE, NOVE = "mobiuslabsgmbh/faster-whisper-large-v3-turbo", "dropbox-dash/faster-whisper-large-v3-turbo"

    def test_nova_adresa_stejna_slozka(self):
        self.assertEqual(model.repo("turbo"), self.NOVE)
        self.assertEqual(model.slozka("turbo").name, "faster-whisper-large-v3-turbo")  # složka se nezměnila
        self.assertIn(self.NOVE, stahovani.HUGGINGFACE)
        self.assertNotIn(self.STARE, stahovani.HUGGINGFACE)
        self.assertEqual(stahovani.HUGGINGFACE[self.NOVE]["revize"], "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf")

    def test_stazeny_model_se_znackou_stareho_jmena_zustava_pripraveny(self):
        """Značka .hotovo z dřívější verze nese staré jméno repozitáře – model se kvůli tomu znovu nestahuje."""
        tmp = Path(tempfile.mkdtemp(prefix="kupcake_turbo_"))
        soubory = {"config.json": b"{}\n", "model.bin": os.urandom(4096)}
        manifest = {self.NOVE: {"revize": "abc", "soubory": {
            f: (len(d), hashlib.sha256(d).hexdigest()) for f, d in soubory.items()}}}
        for f, d in soubory.items():
            (tmp / f).write_bytes(d)
        with mock.patch.dict(stahovani.HUGGINGFACE, manifest), \
                mock.patch.object(stahovani, "_otevri", side_effect=AssertionError("nemělo se stahovat")):
            otisky = {f: stahovani._otisk(tmp / f) for f in soubory}
            (tmp / stahovani.ZNACKA).write_text(json.dumps({"repo": self.STARE, "revize": "abc", "soubory": otisky}))
            self.assertTrue(stahovani.je_pripraveno(self.NOVE, tmp))
            self.assertEqual(stahovani.priprav_repo(self.NOVE, tmp, "test"), tmp)

    def test_cache_huggingface_i_pod_starym_jmenem(self):
        tmp = Path(tempfile.mkdtemp(prefix="kupcake_hf_"))
        revize = stahovani.HUGGINGFACE[self.NOVE]["revize"]
        snapshot = tmp / "hub" / f"models--{self.STARE.replace('/', '--')}" / "snapshots" / revize
        snapshot.mkdir(parents=True)
        with mock.patch.dict(os.environ, {"HF_HOME": str(tmp)}):
            self.assertEqual(model._najdi_v_cache(self.NOVE), snapshot)
            self.assertIsNone(model._najdi_v_cache("Systran/faster-whisper-medium"))


if __name__ == "__main__":
    unittest.main()
