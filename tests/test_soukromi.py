# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Soukromí: knihovny Hugging Face jsou offline a bez telemetrie; hlášení chyby neobsahuje uživatelské jméno."""
import _zaklad  # noqa: F401

import os
import unittest


class TestProstredi(unittest.TestCase):
    def test_hf_offline_a_bez_telemetrie(self):
        for promenna in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY",
                         "HF_HUB_DISABLE_IMPLICIT_TOKEN"):
            self.assertEqual(os.environ.get(promenna), "1", promenna)

    def test_huggingface_hub_vidi_offline(self):
        try:
            from huggingface_hub import constants
        except ImportError:
            self.skipTest("huggingface_hub není nainstalován")
        self.assertTrue(constants.HF_HUB_OFFLINE)
        self.assertTrue(constants.HF_HUB_DISABLE_TELEMETRY)


class TestHlaseni(unittest.TestCase):
    def test_bez_profilu(self):
        import logy
        local = os.environ["LOCALAPPDATA"]
        text = logy.bez_profilu(f"Log: {local}\\KupcakeStudio\\logs\\kupcake.log a {local.replace(chr(92), '/')}/x")
        self.assertNotIn(local, text)
        self.assertIn("%LOCALAPPDATA%\\KupcakeStudio\\logs\\kupcake.log", text)
        self.assertNotIn(os.environ["LOCALAPPDATA"], logy.hlaseni("chyba", "detail"))


if __name__ == "__main__":
    unittest.main()
