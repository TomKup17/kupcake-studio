# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Úpravy titulků a slov na časové ose (seskupení, řezy, mazání, vkládání, schránka).

Každá funkce nejdřív všechno ověří (a při problému vyhodí Chyba se srozumitelnou zprávou),
teprve potom mění data. Vrací nový seznam titulků; objekty Slovo se přesouvají, ne kopírují,
takže výběr na časové ose zůstane zachovaný.
"""
from i18n import t as tr  # `t` je tu často proměnná (titulek)
from titulky import MIN_SLOVO, Slovo, Titulek, prepocitej_text


class Chyba(Exception):
    pass


def _novy(slova, konec=None, zamceno=False):
    t = Titulek(slova[0].start, konec if konec is not None else slova[-1].end, "", list(slova), zamceno)
    prepocitej_text(t)
    return t


def vsechna_slova(titulky):
    return [s for t in titulky for s in t.slova]


def titulek_slova(titulky, slovo):
    return next(t for t in titulky if any(s is slovo for s in t.slova))


def _hlidej_zamek(titulky, slova, co="upravit"):
    for s in slova:
        if titulek_slova(titulky, s).zamceno:
            raise Chyba(tr("uprava.zamceno", slovo=s.text))


def _id(slova):
    return {id(s) for s in slova}


# ---------- skupiny ----------
def rozdel_skupinu(titulky, vybrana):
    """Každé označené slovo se stane samostatným titulkem; neoznačené sousedy zůstanou spolu."""
    if not vybrana:
        raise Chyba(tr("uprava.oznac_oddelit"))
    _hlidej_zamek(titulky, vybrana, "rozdělit")
    ids, nove = _id(vybrana), []
    for t in titulky:
        if not any(id(s) in ids for s in t.slova):
            nove.append(t)
            continue
        casti, cur = [], []
        for s in t.slova:
            if id(s) in ids:
                if cur:
                    casti.append(cur)
                    cur = []
                casti.append([s])
            else:
                cur.append(s)
        if cur:
            casti.append(cur)
        for i, c in enumerate(casti):
            nove.append(_novy(c, t.end if i == len(casti) - 1 else None))
    if len(nove) == len(titulky):
        raise Chyba(tr("uprava.uz_samostatna"))
    return nove


def seskup(titulky, vybrana):
    """Označená sousední slova se spojí do jednoho titulku (krajní titulky se případně rozdělí)."""
    if len(vybrana) < 2:
        raise Chyba(tr("uprava.oznac_dve"))
    slova = vsechna_slova(titulky)
    index = {id(s): i for i, s in enumerate(slova)}
    idx = sorted(index[id(s)] for s in vybrana)
    if idx[-1] - idx[0] + 1 != len(idx):
        raise Chyba(tr("uprava.nesousedni"))
    a, b = idx[0], idx[-1]
    rozsah = slova[a:b + 1]
    dotcene = {id(titulek_slova(titulky, s)) for s in rozsah}
    if all(len(t.slova) == len(rozsah) for t in titulky if id(t) in dotcene) and len(dotcene) == 1:
        raise Chyba(tr("uprava.uz_jeden"))
    _hlidej_zamek(titulky, rozsah, "seskupit")
    t_b = titulek_slova(titulky, slova[b])
    konec_skupiny = t_b.end if t_b.slova[-1] is slova[b] else None
    nove, vlozeno = [], False
    for t in titulky:
        if not t.slova or id(t) not in dotcene:
            nove.append(t)
            continue
        pred = [s for s in t.slova if index[id(s)] < a]
        za = [s for s in t.slova if index[id(s)] > b]
        if pred:
            nove.append(_novy(pred))
        if not vlozeno:
            nove.append(_novy(rozsah, konec_skupiny))
            vlozeno = True
        if za:
            nove.append(_novy(za, t.end))
    return nove


def rozdel_u_slova(titulky, slovo):
    """Titulek se rozdělí na dva: slova před označeným a od označeného dál."""
    t = titulek_slova(titulky, slovo)
    i = next(i for i, s in enumerate(t.slova) if s is slovo)
    if i == 0:
        raise Chyba(tr("uprava.prvni_slovo", slovo=slovo.text))
    _hlidej_zamek(titulky, [slovo], "rozdělit")
    nove = []
    for x in titulky:
        if x is t:
            nove += [_novy(t.slova[:i]), _novy(t.slova[i:], t.end)]
        else:
            nove.append(x)
    return nove


# ---------- řez a spojení ----------
def _rozdel_text(text, podil):
    tokeny = text.split()
    if len(tokeny) > 1:
        k = min(max(round(len(tokeny) * podil), 1), len(tokeny) - 1)
        return " ".join(tokeny[:k]), " ".join(tokeny[k:])
    k = min(max(round(len(text) * podil), 1), len(text) - 1)
    return text[:k], text[k:]


def rozriznout(titulky, cas):
    """Řez v místě playheadu: uvnitř slova ho rozdělí na dvě slova, jinak rozdělí titulek."""
    for t in titulky:
        for i, s in enumerate(t.slova):
            if s.start + MIN_SLOVO <= cas <= s.end - MIN_SLOVO:
                if len(s.text) < 2:
                    raise Chyba(tr("uprava.kratke", slovo=s.text))
                _hlidej_zamek(titulky, [s], "rozříznout")
                levy, pravy = _rozdel_text(s.text, (cas - s.start) / (s.end - s.start))
                nove = Slovo(pravy, round(cas, 3), s.end)
                s.text, s.end = levy, round(cas, 3)
                t.slova.insert(i + 1, nove)
                prepocitej_text(t)
                return list(titulky)
    for t in titulky:
        if t.slova and t.start < cas < t.end:
            levy = [s for s in t.slova if (s.start + s.end) / 2 < cas]
            if levy and len(levy) < len(t.slova):
                _hlidej_zamek(titulky, t.slova[:1], "rozříznout")
                return [x for y in titulky for x in ([_novy(levy), _novy(t.slova[len(levy):], t.end)]
                                                     if y is t else [y])]
    raise Chyba(tr("uprava.neni_co_riznout"))


def spoj_slova(titulky, vybrana):
    """Dvě a více sousedních slov jednoho titulku → jeden box."""
    if len(vybrana) < 2:
        raise Chyba(tr("uprava.spojit_dve"))
    t = titulek_slova(titulky, vybrana[0])
    if any(titulek_slova(titulky, s) is not t for s in vybrana):
        raise Chyba(tr("uprava.spojit_jeden_titulek"))
    ids = _id(vybrana)
    idx = [i for i, s in enumerate(t.slova) if id(s) in ids]
    if idx[-1] - idx[0] + 1 != len(idx):
        raise Chyba(tr("uprava.spojit_sousedni"))
    _hlidej_zamek(titulky, vybrana, "spojit")
    prvni, posledni = t.slova[idx[0]], t.slova[idx[-1]]
    prvni.text = " ".join(t.slova[i].text for i in idx)
    prvni.end = posledni.end
    del t.slova[idx[0] + 1:idx[-1] + 1]
    prepocitej_text(t)
    return list(titulky)


# ---------- mazání ----------
def smaz(titulky, vybrana, s_posunem=False):
    """Smaže slova (prázdné titulky zmizí). S posunem se následující slova posunou o smazaný čas."""
    if not vybrana:
        raise Chyba(tr("uprava.oznac_smazat"))
    _hlidej_zamek(titulky, vybrana, "smazat")
    ids = _id(vybrana)
    smazane = sorted((s.start, s.end) for s in vybrana)

    def posun(x):
        return sum(b - a for a, b in smazane if b <= x + 1e-6) if s_posunem else 0.0

    if s_posunem:
        posunute = [s for s in vsechna_slova(titulky) if id(s) not in ids and posun(s.start) > 0]
        _hlidej_zamek(titulky, posunute, "posunout")
    nove = []
    for t in titulky:
        zbyla = [s for s in t.slova if id(s) not in ids]
        if t.slova and not zbyla:
            continue
        konec = t.end - posun(t.end)
        for s in zbyla:
            d = posun(s.start)
            s.start, s.end = round(s.start - d, 3), round(s.end - d, 3)
        if len(zbyla) != len(t.slova):
            t.slova = zbyla
            prepocitej_text(t)
        t.end = konec
        nove.append(t)
    return nove


# ---------- vkládání a schránka ----------
def kopiruj(titulky, vybrana):
    """Do schránky: skupiny slov (podle titulků) s časy relativně k prvnímu slovu."""
    if not vybrana:
        raise Chyba(tr("uprava.oznac_kopirovat"))
    ids, t0, skupiny = _id(vybrana), min(s.start for s in vybrana), []
    for t in titulky:
        sk = [(s.text, s.start - t0, s.end - t0) for s in t.slova if id(s) in ids]
        if sk:
            skupiny.append(sk)
    return skupiny


def vloz(titulky, schranka, cas, delka_videa):
    """Vloží slova ze schránky od času `cas`. Uvnitř titulku je přidá do něj, jinak vznikne nový titulek."""
    if not schranka:
        raise Chyba(tr("uprava.prazdna_schranka"))
    nova = [[Slovo(tx, round(cas + a, 3), round(cas + b, 3)) for tx, a, b in sk] for sk in schranka]
    vse = [s for sk in nova for s in sk]
    if delka_videa and vse[-1].end > delka_videa + 1e-6:
        raise Chyba(tr("uprava.za_koncem"))
    for s in vsechna_slova(titulky):
        for n in vse:
            if s.start < n.end - 1e-6 and n.start < s.end - 1e-6:
                raise Chyba(tr("uprava.obsazeno", slovo=s.text))
    hostitel = next((t for t in titulky if t.slova and t.slova[0].start < vse[0].start
                     and vse[-1].end < t.slova[-1].end), None)
    if hostitel:
        if hostitel.zamceno:
            raise Chyba(tr("uprava.hostitel_zamceny"))
        hostitel.slova = sorted(hostitel.slova + vse, key=lambda s: s.start)
        prepocitej_text(hostitel)
        return list(titulky), vse
    nove = list(titulky) + [_novy(sk) for sk in nova]
    nove.sort(key=lambda t: t.slova[0].start if t.slova else t.start)
    return nove, vse


def volne_misto(titulky, cas, delka_videa, chtene=0.5):
    """Délka volného místa od `cas` (pro nové slovo), nebo vyhodí Chyba."""
    slova = vsechna_slova(titulky)
    if any(s.start - 1e-6 <= cas < s.end - 1e-6 for s in slova):
        raise Chyba(tr("uprava.na_slove"))
    dalsi = min((s.start for s in slova if s.start >= cas), default=delka_videa or cas + chtene)
    delka = min(chtene, dalsi - cas)
    if delka < MIN_SLOVO:
        raise Chyba(tr("uprava.bez_mista"))
    return round(delka, 3)


def prepni_zamek(titulky, vybrana):
    dotcene = []
    for s in vybrana:
        t = titulek_slova(titulky, s)
        if t not in dotcene:
            dotcene.append(t)
    if not dotcene:
        raise Chyba(tr("uprava.oznac_zamek"))
    zamknout = not all(t.zamceno for t in dotcene)
    for t in dotcene:
        t.zamceno = zamknout
    return zamknout, len(dotcene)
