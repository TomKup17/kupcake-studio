# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Načítání modelu Demucs: omezený unpickler přijme tvar oficiálního souboru a odmítne pickle s cizím kódem.
(Načítá PyTorch a Demucs – trvá několik sekund.) Je-li oficiální soubor stažený, ověří se i na něm."""
import _zaklad  # noqa: F401  – izolace a sys.path

import os
import pickle
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


class TestNacteniDemucs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import torch
        from demucs.htdemucs import HTDemucs
        cls.np, cls.torch, cls.HTDemucs = np, torch, HTDemucs
        cls.tmp = Path(tempfile.mkdtemp(prefix="kupcake_th_"))

    def _uloz(self, balicek, jmeno):
        cesta = self.tmp / jmeno
        self.torch.save(balicek, cesta)
        return cesta

    def test_tvar_oficialniho_souboru(self):
        """Stejný tvar jako demucs.states.serialize_model: třída modelu, argumenty, stav, parametry tréninku
        (včetně Fraction a numpy float64, které oficiální soubor obsahuje)."""
        import hlas
        balicek = {"klass": self.HTDemucs, "args": (), "kwargs": {"sources": ["drums", "bass", "other", "vocals"],
                                                                    "audio_channels": 2, "channels": 48, "depth": 4,
                                                                    "segment": Fraction(39, 5)},
                   "state": {"w": self.torch.zeros(2, 3, dtype=self.torch.half), "b": self.torch.ones(1)},
                   "training_args": {"dset": {"samplerate": 44100}, "epochs": 360, "name": "htdemucs",
                                     "lr": self.np.float64(0.0003)}}
        nacteno = hlas.nacti_balicek(self._uloz(balicek, "ok.th"))
        self.assertIs(nacteno["klass"], self.HTDemucs)
        self.assertEqual(nacteno["kwargs"]["segment"], Fraction(39, 5))
        self.assertEqual(nacteno["state"]["w"].shape, (2, 3))
        self.assertEqual(float(nacteno["training_args"]["lr"]), 0.0003)

    def test_cizi_kod_se_odmitne(self):
        import hlas

        class Zlo:
            def __reduce__(self):
                return (os.system, ("echo pwned",))
        for balicek in ({"klass": os.system, "args": ("echo pwned",), "kwargs": {}, "state": {}},
                        {"klass": self.HTDemucs, "args": (Zlo(),), "kwargs": {}, "state": {}},
                        {"klass": self.HTDemucs, "args": (), "kwargs": {}, "state": {"x": Zlo()}},
                        {"klass": self.HTDemucs, "args": (), "kwargs": {"f": eval}, "state": {}}):
            cesta = self._uloz(balicek, "zlo.th")
            with self.subTest(balicek=list(balicek)), self.assertRaises(pickle.UnpicklingError):
                hlas.nacti_balicek(cesta)

    def test_povolene_tridy(self):
        import hlas
        povolene = hlas.povolene_tridy()
        self.assertEqual(povolene[:2], [self.HTDemucs, Fraction])
        self.assertIn(("numpy.core.multiarray.scalar"), [p[1] for p in povolene if isinstance(p, tuple)])
        self.assertIn(self.np.dtype, povolene)
        self.assertIn(self.np.dtypes.Float64DType, povolene)
        self.assertEqual(len(povolene), 6)
        for p in povolene:  # nic, co by spouštělo kód
            obj = p[0] if isinstance(p, tuple) else p
            self.assertNotIn(obj, (eval, exec, os.system, __import__))

    def test_oficialni_soubor_pokud_je_stazen(self):
        """Skutečný model htdemucs (jen když už je stažený v %LOCALAPPDATA% uživatele – test nic nestahuje)."""
        import hlas
        from manifest_modelu import DEMUCS
        skutecne = Path(os.environ.get("KUPCAKE_SKUTECNE_LOCALAPPDATA", "")) if os.environ.get(
            "KUPCAKE_SKUTECNE_LOCALAPPDATA") else None
        cesta = (skutecne / "KupcakeStudio" / "models" / "demucs" / DEMUCS["url"].rsplit("/", 1)[1]) if skutecne else None
        if not cesta or not cesta.is_file():
            self.skipTest("oficiální soubor Demucs není k dispozici (nastav KUPCAKE_SKUTECNE_LOCALAPPDATA)")
        from demucs.states import load_model
        model = load_model(hlas.nacti_balicek(cesta))
        self.assertEqual(model.sources, ["drums", "bass", "other", "vocals"])


if __name__ == "__main__":
    unittest.main()
