"""Ikona kupcake.studio: PNG náhledy variant a export do .ico. Kresba cupcaku je v kupcake.py.

  python ikona/ikona.py nahledy        -> icon_drafts/kupcake_varianta_*.svg + .png
  python ikona/ikona.py export <A|B|C> -> kupcake.ico (16–256 px), ikona/kupcake.svg, kupcake_256.png

U 16 a 24 px je motiv zjednodušený na siluetu s třešničkou (kupcake.MALE).
Vybranou variantu zapiš i do kupcake.VARIANTA – podle ní se kreslí logo a animace v aplikaci.
"""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))
import kupcake  # noqa: E402

VELIKOSTI = [16, 24, 32, 48, 64, 128, 256]
VARIANTY = {
    "A": ("Kreslený klasik", "tmavé kreslené obrysy, tmavý košíček se světlými proužky"),
    "B": ("Světlá linka", "kresba světlou linkou, průhledný košíček – nejvíc „animovaný“ styl"),
    "C": ("Točená poleva", "vyšší poleva ve dvou patrech, světlý košíček s tmavými proužky"),
}


def svg_pro(var, n):
    return kupcake.svg(var, n)


def vykresli(svg_text, n):
    img = QImage(n, n, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg_text.encode())).render(p, QRectF(0, 0, n, n))
    p.end()
    return img


def png_bytes(img):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def nahled(var, cil):
    """Náhledový list: velká ikona, popis, skutečné velikosti na tmavém i světlém pruhu, 16/24 zvětšené."""
    W, H = 900, 420
    list_ = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    list_.fill(QColor("#111214"))
    p = QPainter(list_)
    p.drawImage(24, 24, vykresli(svg_pro(var, 256), 256))
    nazev, popis_varianty = VARIANTY[var]
    p.setPen(QColor(kupcake.SVETLA))
    p.setFont(QFont("Segoe UI", 15, QFont.DemiBold))
    p.drawText(300, 46, f"Varianta {var} – {nazev}")
    p.setPen(QColor("#8A8F98"))
    p.setFont(QFont("Segoe UI", 9))
    p.drawText(300, 66, popis_varianty)
    for i, (pozadi, popis) in enumerate((("#202020", "hlavní panel – tmavý"), ("#F3F3F3", "hlavní panel – světlý"))):
        y = 84 + i * 90
        p.fillRect(300, y, 576, 76, QColor(pozadi))
        x = 316
        for n in (64, 48, 32, 24, 16):
            p.drawImage(x, y + (76 - n) // 2, vykresli(svg_pro(var, n), n))
            x += n + 22
        p.setPen(QColor("#8A8F98"))
        p.drawText(640, y + 44, popis)
    p.drawText(300, 292, "16 px a 24 px zvětšené (silueta s třešničkou):")
    x = 300
    for n in (16, 24):
        p.drawImage(x, 304, vykresli(svg_pro(var, n), n).scaled(96, 96, Qt.IgnoreAspectRatio, Qt.FastTransformation))
        x += 130
    p.end()
    list_.save(str(cil))


def export_ico(var):
    obrazky = [(n, png_bytes(vykresli(svg_pro(var, n), n))) for n in VELIKOSTI]
    # ICO: hlavička + adresář + PNG data (Windows Vista+ podporuje PNG ve všech velikostech)
    data = struct.pack("<HHH", 0, 1, len(obrazky))
    offset = 6 + 16 * len(obrazky)
    adresar, telo = b"", b""
    for n, png in obrazky:
        adresar += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(png), offset + len(telo))
        telo += png
    (KOREN / "kupcake.ico").write_bytes(data + adresar + telo)
    (KOREN / "ikona" / "kupcake.svg").write_text(svg_pro(var, 256), encoding="utf-8")
    for n in kupcake.MALE:
        (KOREN / "ikona" / f"kupcake_{n}.svg").write_text(svg_pro(var, n), encoding="utf-8")
    vykresli(svg_pro(var, 256), 256).save(str(KOREN / "ikona" / "kupcake_256.png"))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv[:1])
    if sys.argv[1] == "nahledy":
        slozka = KOREN / "icon_drafts"
        slozka.mkdir(exist_ok=True)
        for var in VARIANTY:
            (slozka / f"kupcake_varianta_{var}.svg").write_text(svg_pro(var, 256), encoding="utf-8")
            nahled(var, slozka / f"kupcake_varianta_{var}.png")
        print("náhledy:", slozka)
    elif sys.argv[1] == "export":
        export_ico(sys.argv[2])
        print("ikona:", KOREN / "kupcake.ico")
