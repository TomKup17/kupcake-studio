# kupcake.studio – Podmínky použití

[English](TERMS.md) | **Čeština**

Poslední změna: 11. 11. 2026

Tyto podmínky platí pro aplikaci kupcake.studio. Instalací nebo používáním aplikace s nimi souhlasíš.

## 1. Kdo aplikaci poskytuje

kupcake.studio poskytuje **Tomáš Kupec (iamtom.kup)**.
Kontakt: <https://tomkup.cz> nebo [GitHub Issues](https://github.com/TomKup17/kupcake-studio/issues).

## 2. Cena a licence

Aplikace je **zdarma**. Její zdrojový kód je zveřejněný pod licencí **GNU General Public License verze 3**
(`GPL-3.0-only`, soubor `LICENSE`, s dodatečným svolením v souboru `ADDITIONAL_PERMISSION.md`). Za podmínek
této licence ji smíš používat, zkoumat, upravovat a šířit.

Aplikace obsahuje i programy a knihovny třetích stran (například FFmpeg, mpv, Qt, PyTorch a běhové knihovny
NVIDIA a Intel). Každá má vlastní licenci, seznam je v souboru `THIRD_PARTY_LICENSES.md`; knihovny NVIDIA,
Intel a Microsoft jsou proprietární a pod GPL nespadají. Název kupcake.studio a logo nejsou součástí licence kódu.

## 3. Bez záruky

Aplikace se poskytuje **tak, jak je, bez jakékoli záruky**, v rozsahu, v jakém to zákon dovoluje. Jde
o testovací verzi (beta): může obsahovat chyby a funkce se mohou měnit. Ukládej si práci, měj zálohy videí
a výsledek si před zveřejněním zkontroluj.

V rozsahu, v jakém to zákon dovoluje, poskytovatel neodpovídá za škodu způsobenou používáním aplikace nebo
tím, že ji používat nejde. Nic v těchto podmínkách nevylučuje ani neomezuje odpovědnost a práva, která podle
zákona vyloučit nebo omezit nelze (například zákonná práva spotřebitele).

## 4. Přepis může být nepřesný

Titulky vznikají automatickým rozpoznáním řeči. Přepis i časování **mohou obsahovat chyby**: přeslechnutá nebo
chybějící slova, špatně zapsaná jména, čísla a interpunkci, text v místech, kde nikdo nemluví. Titulky si před
použitím vždy přečti. Aplikace se nehodí tam, kde by chyba mohla způsobit škodu (například právní, zdravotní
nebo bezpečnostní texty), pokud výsledek nezkontroluje člověk.

## 5. Za obsah odpovídáš ty

O tom, jaká videa, hudbu, hlasy a písma zpracuješ, rozhoduješ ty. **Odpovídáš za to, že k nim máš práva** –
autorská a související práva k videím a hudbě, souhlas lidí, kteří jsou vidět nebo slyšet, a licence
k vlastním písmům, pokud je použiješ pro titulky. Aplikace nic z toho nekontroluje. Tvoje videa, titulky
a projekty zůstávají tvoje.

## 6. Modely

Modely řeči nejsou součástí instalátoru. Aplikace je stahuje až po tvém souhlasu přímo ze serverů Hugging Face
a Meta. Mají vlastní licence (`THIRD_PARTY_LICENSES.md`, oddíl 6):

- Whisper (přepis) – MIT; wav2vec2 (přesné časování slov) – Apache 2.0; Demucs (oddělení hlasu) – MIT,
- **Meta MMS** (přesné časování slov v dalších jazycích) – **CC BY-NC 4.0, jen pro nekomerční použití**.
  Ve výchozím stavu je vypnutý. Když ho v Nastavení zapneš, potvrzuješ, že ho používáš jen nekomerčně;
  za dodržení této licence odpovídáš ty.

## 7. Kdy se aplikace připojuje k internetu

Videa, zvuk, přepisy a titulky se zpracovávají **jen na tvém počítači** a nikam se neodesílají. Aplikace nemá
telemetrii, účty ani analytické nástroje. K internetu se připojí jen v těchto případech:

- **kontrola nové verze** – jednou denně se zeptá GitHubu (`api.github.com`) na seznam vydání; jde to vypnout
  v Nastavení → Kontrolovat nové verze,
- **stažení modelu** – jen po tvém souhlasu, z `huggingface.co` (a jeho CDN) a `dl.fbaipublicfiles.com`,
- **odkazy** – když klikneš na odkaz, stránka se otevře v tvém prohlížeči.

V těchto případech server vidí tvoji IP adresu, stejně jako u každé webové stránky. Podrobnosti jsou v README,
oddíl Soukromí.

## 8. Ochranné známky třetích stran

ProRes (Apple), TikTok, Instagram, YouTube, DaVinci Resolve, Premiere (Adobe), CapCut, NVIDIA, CUDA a další
názvy jsou ochranné známky svých vlastníků. Jsou použité jen k popisu kompatibility. Aplikace kupcake.studio
s těmito společnostmi **není spojená, není jimi schválená ani podporovaná**.

## 9. Rozhodné právo

Tyto podmínky se řídí právem **České republiky**. Pokud jsi spotřebitel, nepřicházíš tím o ochranu, kterou ti
dávají kogentní předpisy země, kde bydlíš.

## 10. Změny

Podmínky se mohou s novou verzí aplikace změnit. Aktuální znění je vždy v repozitáři
<https://github.com/TomKup17/kupcake-studio> a v aplikaci (O aplikaci → Podmínky použití).
