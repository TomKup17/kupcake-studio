# kupcake.studio

[English](README.md) | **Čeština**

Aplikace značky iamtom.kup. Zobrazovaný název se píše vždy `kupcake.studio`, technický název
(soubory, složky) je `KupcakeStudio`. Dřívější pracovní názvy: Spellcast, tkStudio.

> **Název a logo:** název **kupcake.studio**, logo a ikona s cupcakem a značka iamtom.kup **nejsou
> součástí licence kódu** – nesmí se používat pro upravené verze ani jiné projekty bez souhlasu autora.
> **Oficiální verze je ke stažení jen z tohoto repozitáře** (Releases); instalátory z jiných zdrojů
> mohou být upravené. Bezpečnostní problém nahlas podle [SECURITY.md](SECURITY.md).

Automatické titulky z videa: přepis řeči (faster-whisper large-v3 na GPU), editor titulků
s časovou osou po slovech, živý náhled v přehrávači mpv a vypálení do videa přes FFmpeg (NVENC).

## Beta verze

Tohle je **veřejná testovací verze** (`1.0.0-beta.2`). Aplikace je funkční, ale **může obsahovat chyby**
a některé funkce se ještě mohou změnit. Při prvním spuštění se ukáže úvodní okno s tímto upozorněním –
pokračuje se až po zaškrtnutí „Rozumím“ (znovu se ukáže jen u nové hlavní verze, např. přechod na 1.0).

- Rozpracovanou práci průběžně ukládej (Ctrl+S); navíc se každé 2 minuty ukládá automaticky a po pádu
  aplikace nabídne obnovu.
- **Původní video se nikdy nepřepisuje** – export do stejného souboru aplikace zablokuje. Zálohy přesto doporučujeme.
- **Jak nahlásit chybu:** Nápověda → Nahlásit chybu / Zpětná vazba (nebo odkaz v úvodním okně). Když aplikace
  ukáže chybové okno, klikni na **„Zkopírovat hlášení“** a vlož ho do zprávy – obsahuje verzi, systém a výpis
  chyby, nikoli tvoje videa. Pomůže i popis kroků, které k chybě vedly, a log ze složky
  `%LOCALAPPDATA%\KupcakeStudio\logs`.

## Bez záruky

kupcake.studio je zdarma a **poskytuje se tak, jak je, bez jakékoli záruky** – výslovné ani předpokládané,
včetně záruky prodejnosti nebo vhodnosti pro určitý účel. Autor neodpovídá za škody vzniklé jejím používáním,
v rozsahu, který dovoluje zákon. Podrobně oddíly 15 a 16 licence
[GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) (plné znění v souboru [LICENSE](LICENSE)).
V aplikaci: O aplikaci → „Poskytováno bez záruky · GPL-3.0“. Úplné **podmínky použití** jsou v souboru
[TERMS.cs.md](TERMS.cs.md) (anglicky [TERMS.md](TERMS.md)); aplikace je ukazuje v okně O aplikaci
a v úvodním okně, instalátor na stránce s licencí.

## Soukromí

Vše se zpracovává **jen na tvém počítači** – přepis řeči, časování slov, oddělení hlasu, náhled, přehrávání
i export. Videa, zvuk, přepisy, titulky, projekty ani nastavení se **nikam neodesílají** a aplikace
**nesbírá žádná data**: žádná telemetrie, žádné účty, žádné analytické nástroje, žádné identifikátory.
Nemůžeme ale tvrdit, že aplikace nikdy nekomunikuje s internetem – připojí se přesně v těchto případech:

| Kdy | Kam | Co se posílá | Jak vypnout |
|---|---|---|---|
| **Kontrola nové verze** – 5 s po startu, nejvýš jednou za 24 h (ve zveřejněné verzi; dokud není v `links.py` vyplněný repozitář, kontrola neběží) | `api.github.com` (GitHub, Microsoft) | běžný HTTPS požadavek na seznam vydání; hlavička `User-Agent: kupcake.studio/<verze>`. GitHub jako každý server vidí tvoji IP adresu. Nic jiného. | Nastavení → **Kontrolovat nové verze** |
| **Stažení modelu** – jen po tvém souhlasu v dialogu (název, velikost, zdroj) při prvním použití dané přesnosti přepisu, jazyka časování nebo oddělení hlasu | `huggingface.co` (+ jeho CDN `*.hf.co`, `*.huggingface.co`); Demucs z `dl.fbaipublicfiles.com` (Meta) | HTTPS požadavek na konkrétní soubory modelu + `User-Agent` jako výše. Server vidí IP adresu a **který model** stahuješ (tedy např. že časuješ české video). Žádné video, zvuk ani text. | nedávat souhlas (přepis pak nejde, resp. proběhne bez daného kroku) |
| **Odkazy** – Nápověda → Nahlásit chybu, tlačítka v O aplikaci, „Stáhnout“ u nové verze | otevře se **tvůj prohlížeč** na stránce z `links.py`, resp. na stránce vydání na `github.com` | nic – jen se otevře stránka; aplikace sama **nikdy nestahuje ani nespouští instalátor** | kliknout jen, když chceš |

Co aplikace dělá navíc, aby nic „neuteklo“ samo:

- knihovny Hugging Face (`transformers`, `huggingface_hub`) běží vynuceně **offline** a s vypnutou telemetrií
  (`HF_HUB_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY` v `cesty.py`); modely stahuje jen `stahovani.py` a nikdy bez dotazu,
- stažení i přesměrování smí vést jen na HTTPS a jen na hostitele výše; každý soubor se ověří proti **SHA-256**
  z `manifest_modelu.py` – jiný soubor se smaže (viz [SECURITY.md](SECURITY.md)),
- FFmpeg a mpv smí číst **jen místní soubory** (`-protocol_whitelist file`, mpv bez youtube-dl, bez skriptů
  a konfigurace z profilu) – video, které je ve skutečnosti playlist s internetovými adresami, nic nestáhne,
- PyTorch, CTranslate2, faster-whisper, Demucs, onnxruntime ani Qt v aplikaci na síť nesahají (ověřeno auditem
  kódu, [docs/BEZPECNOSTNI_AUDIT.md](docs/BEZPECNOSTNI_AUDIT.md)).

Co zůstává jen na tvém disku (a co bys měl vědět, než to někomu pošleš):

- **log** `%LOCALAPPDATA%\KupcakeStudio\logs\kupcake.log` – průběh práce a chyby; může obsahovat **názvy a cesty
  tvých videí a projektů** a texty chyb FFmpeg; žádné přepisy ani obsah titulků,
- **hlášení chyby** („Zkopírovat hlášení“) – verze aplikace, verze Windows, procesor, grafická karta a ovladač,
  text chyby; cesty do tvého profilu jsou nahrazené `%LOCALAPPDATA%`, takže neobsahuje tvoje uživatelské jméno,
- **nastavení** `%APPDATA%\KupcakeStudio\aplikace.ini` – mj. seznam nedávných projektů (cesty), poslední volby
  exportu; **projekty `.kupcake`** – absolutní cesta k videu, přepis (slova s časy) a titulky.

Mimo aplikaci: Windows SmartScreen může při prvním spuštění nepodepsaného instalátoru sám kontaktovat Microsoft –
to je funkce Windows, ne aplikace.

## Systémové požadavky

| | Minimum | Doporučeno |
|---|---|---|
| Systém | Windows 10 nebo 11, 64bit | Windows 11 |
| Procesor | 4 jádra (x64) | 8 a více jader |
| Paměť | 8 GB RAM | 16 GB RAM |
| Grafická karta | – (přepis i export poběží na procesoru, výrazně pomaleji) | NVIDIA s 6 GB VRAM a víc, aktuální ovladač (CUDA 12) |
| Místo na disku | aplikace asi 7 GB + model 1,5–3 GB | 15 GB volného místa (víc modelů, exporty) |
| Internet | při prvním přepisu (stažení modelu) | – |

Orientační rychlost přepisu (60 s souvislé řeči): RTX 4070 SUPER asi 5 s, procesor i7-12700KF asi 50 s
(přesnost Nejpřesnější), s přesností Rychlá asi 1,5 s / 20 s.

## Instalace

1. Z **Releases** tohoto repozitáře (jinde se oficiální verze nešíří) stáhni **všechny** soubory instalátoru
   do jedné složky: `KupcakeStudio-Setup-<verze>.exe` a k němu části `KupcakeStudio-Setup-<verze>-1.bin`,
   `-2.bin`… GitHub dovolí soubory nejvýš do 2 GB, proto je instalátor rozdělený; bez částí `.bin` se
   nespustí. Velikost: dohromady asi **3,1 GB**, po instalaci asi **6,9 GB** (obsahuje PyTorch s CUDA, FFmpeg
   a mpv), k tomu při prvním přepisu model řeči **1,5–3,1 GB** podle zvolené přesnosti.
2. Volitelně ověř kontrolní součty – musí se shodovat se souborem `KupcakeStudio-Setup-<verze>.sha256`
   u vydání: `Get-FileHash .\KupcakeStudio-Setup-* -Algorithm SHA256` (PowerShell ve složce se staženými soubory).
3. Spusť `KupcakeStudio-Setup-<verze>.exe` – instaluje se **bez práv správce**, jen pro tebe
   (`%LOCALAPPDATA%\Programs\KupcakeStudio`).

**Windows SmartScreen:** instalátor zatím není digitálně podepsaný, proto Windows při prvním spuštění může
ukázat „Systém Windows ochránil váš počítač“. Klikni na **Další informace → Přesto spustit**. Udělej to jen
u souboru staženého z Releases tohoto repozitáře se shodným SHA-256.

**Odinstalace:** Nastavení → Aplikace → kupcake.studio. Odinstalátor se zeptá, jestli smazat i stažené modely
a nastavení; projekty `.kupcake` a exportovaná videa zůstanou vždy.

## Licence

Copyright (C) 2026 Tomáš Kupec

Zdrojový kód kupcake.studio je svobodný software pod licencí **GNU General Public License verze 3**
(jen verze 3, `GPL-3.0-only`) – plné znění v souboru [LICENSE](LICENSE). Každý zdrojový soubor nese řádek
s copyrightem a hlavičku `SPDX-License-Identifier: GPL-3.0-only`.

Dodatečné svolení (také v souboru [ADDITIONAL_PERMISSION.md](ADDITIONAL_PERMISSION.md)):

> Additional permission under GNU GPL version 3 section 7: If you modify this Program, or any covered work, by linking or combining it with the NVIDIA CUDA and cuDNN runtime libraries or the Intel Math Kernel Library (or modified versions of those libraries), containing parts covered by the terms of their respective licenses, the licensors of this Program grant you additional permission to convey the resulting work.

**Co pod GPL nespadá** – tyto části mají vlastní podmínky:

- **programy, knihovny, písma a modely třetích stran.** Každá má vlastní licenci. Seznam s přesnými verzemi
  je v [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md), plná znění ve složce `licenses/` (přibalená
  i v instalaci) a úplný seznam přibalených balíčků Pythonu v
  [licenses/PYTHON_PACKAGES.md](licenses/PYTHON_PACKAGES.md),
- zejména běhové knihovny **NVIDIA** (CUDA, cuDNN) a **Intel** (oneMKL, OpenMP). Jsou proprietární,
  **nejsou pod GPL** a smí se používat a šířit jen za podmínek vlastních licencí,
- **název kupcake.studio a logo** (viz poznámka nahoře na této stránce).

**Zdrojové kódy přibalených programů:** přesné verze a odkazy na zdrojový kód FFmpeg, mpv, FFmpeg uvnitř
PyAV, Qt, Qt-ADS a LAME jsou v
[THIRD_PARTY_LICENSES.md, oddíl 2](THIRD_PARTY_LICENSES.md#2-zdrojové-kódy-přibalených-programů).
Zdrojové kódy na požádání poskytnu.

**Model Meta MMS** (přesné časování slov v jazycích bez vlastního modelu) je CC BY-NC 4.0 – jen pro
nekomerční použití. Ve výchozím stavu je vypnutý; zapnout jde v Nastavení po potvrzení upozornění na licenci.

### Ochranné známky a patenty

ProRes, TikTok, Instagram, YouTube, DaVinci Resolve, Premiere, CapCut, NVIDIA a další zmíněné názvy
produktů jsou ochranné známky svých vlastníků. Jsou použité jen k popisu kompatibility; aplikace
kupcake.studio s nimi není spojená, není jimi schválená ani podporovaná. Kodeky H.264, H.265 a AAC mohou v některých
zemích podléhat patentovým licencím.

## Co umí (verze 1.0.0-beta.2)

- projekty `.kupcake` (Soubor → Uložit projekt, Ctrl+S / Ctrl+O, Nedávné projekty, dvojklik na soubor),
  upozornění na neuložené změny, automatické uložení každé 2 minuty a obnova po pádu (`projekt.py`),
- přepis řeči na GPU s časy jednotlivých slov, jazyk řeči automaticky nebo ručně (100 jazyků);
  během přepisu a exportu velká obrazovka s plnícím se cupcakem, skutečným průběhem, odhadem času
  a tlačítkem Zrušit (`prekryti.py`, průběh i na hlavním panelu Windows),
- funguje i bez grafické karty: `hardware.py` vybere GPU (float16 / int8_float16 podle volné VRAM) nebo procesor,
  při nedostatku VRAM přejde na procesor; přesnost přepisu large-v3 / large-v3-turbo / medium (`model.py`),
  odhad doby před přepisem; test bez GPU: `set KUPCAKE_CPU=1` a pak `run_dev.bat`,
- přesné časování: zarovnání slov ke zvuku (wav2vec2, `zarovnani.py`), volitelně oddělení hlasu od hudby
  (Demucs, `hlas.py`); posun a předstih titulků v Nastavení → Časování, Znovu zarovnat výběr (Ctrl+Shift+A),
- editor titulků, časová osa po slovech (skupiny, střih, mazání s posunem, smyčka, značky, J/K/L…;
  všechny zkratky ukáže **F1**),
- panel stylu s živým náhledem v přehrávači a pojmenovanými presety (`presety.py`, `presety.json`
  v nastavení); tečka u skupiny ukáže, že se liší od presetu,
- po exportu notifikace v rohu okna s tlačítkem Otevřít složku (`notifikace.py`),
- volně přesouvatelné a odpojitelné sekce s uloženými rozvrženími (viz níže),
- rozhraní v 5 jazycích,
- export přes panel s možnostmi (`export_panel.py`, příkazy FFmpeg v `export.py`): video s vypálenými
  titulky (H.264/H.265 přes NVENC nebo procesor, MOV ProRes), titulky jako SRT/VTT/ASS, průhledné titulky
  (ProRes 4444 s alfou), presety pro TikTok/Reels a YouTube, úsek videa, sjednocení hlasitosti,
- vzhled v barvách značky s cupcakem v logu a animací při práci (viz níže).

## Vzhled

Vše je v `theme.py` – jinde barvy nepiš natvrdo. Pozadí `#080808`, panely `#111214`, rámečky
`#1F2226`, text `#F2EFEA`, vedlejší text `#8A8F98`. Barvy značky mají dvě role, které se nemíchají:

- **modrá `#00B4FF`** (`theme.AKCENT`) – výběr a fokus: označená slova a řádky, aktivní pole, záložky,
  zaškrtávátka a přepínače,
- **oranžová `#FF6A00`** (`theme.AKCE`) – „teď“ a „akce“: přehrávací hlava, značky, smyčka, tlačítko
  Přehrát, posuvník a čas přehrávače, právě přehrávaný titulek, šipky číselných polí, magnet přichytávání,
  zámky na ose, linka sekce, ve které právě pracuješ, pulzující tečka loga při zpracování, notifikace
  a hlavní tlačítka (`objectName` `primary`: Exportovat video, Uložit preset). Jinde ne.

Kontrast: tmavý text na oranžové i oranžový text na pozadí 7 : 1 (`theme.kontrast()`). Hlavní tlačítka
jsou „pilulky“ (`primary` oranžové, `sekundarni` s obrysem), záhlaví panelů v JetBrains Mono velkými
písmeny s modrou tečkou.

Plocha videa je nativní okno (kreslí do ní mpv); `prehravac.py` proto nastavuje
`Qt.AA_DontCreateNativeWidgetSiblings`, jinak by Qt udělalo nativními i ovládací prvky vedle ní
a ty by při přesunu sekce zůstávaly na starém místě. Grafické efekty (`QGraphicsEffect`) nepoužívej –
záře se kreslí v `paint()`/`paintEvent`.

Cupcake (ikona, logo, animace) kreslí **`kupcake.py`** – jedna kresba pro všechno, vybraná varianta
je v `kupcake.VARIANTA`. `CupcakeAnimace` (třešnička poskakuje, kolem probliknou modré jiskřičky,
smyčka 1,2 s) je u stavového textu během přepisu a exportu, v prázdném náhledu a v O aplikaci.
Ikona: `python ikona/ikona.py nahledy` (návrhy v `icon_drafts/`), `python ikona/ikona.py export C`
→ `kupcake.ico`.

Seznam změn po verzích je v [CHANGELOG.md](CHANGELOG.md).

## Jak aplikace vzniká

kupcake.studio navrhuji, rozhoduji o tom, jak funguje a vypadá, řídím její vývoj a testuji ji já. Kód vzniká
s pomocí AI asistenta (Claude Code).

## Vývoj

- **`run_dev.bat`** – spustí kupcake.studio přímo ze zdrojového kódu. Změny v `.py` souborech stačí uložit
  a aplikaci spustit znovu, nic se nesestavuje. Okno konzole ukáže případné chyby.
  Video jde předat rovnou: `run_dev.bat video.mp4`.
- Verze ze zdrojáků i nainstalovaná verze sdílejí stejné nastavení a model.
- Závislosti jsou v **`requirements.txt`** (nové prostředí:
  `py -3.12 -m venv .venv` a `.venv\Scripts\python.exe -m pip install -r requirements.txt`).
- **libmpv** (přehrávač) v repozitáři není – `libmpv-2.dll` má přes 100 MB, víc, než GitHub dovolí. Stáhni
  archiv `mpv-dev-x86_64-<datum>-git-<hash>.7z` z
  [shinchiro/mpv-winbuild-cmake → Releases](https://github.com/shinchiro/mpv-winbuild-cmake/releases)
  a `libmpv-2.dll` z něj vybal do složky `mpv\`. Bez ní se aplikace ze zdrojáků spustí také, náhled
  ale ukáže jen jednotlivé snímky bez přehrávání (`nahled.py`); sestavení instalátoru ji potřebuje.
  Vydaný instalátor používá sestavení z 21. 10. 2026 (`mpv-dev-x86_64-20261021-git-e471496c56.7z`);
  když přibalíš jiné, uprav jeho verzi a odkaz na zdroj v `THIRD_PARTY_LICENSES.md`.
- **Seznam licencí:** po změně závislostí (nejlépe po sestavení) spusť
  `.venv\Scripts\python.exe licenses\prenes_licence.py` – znovu vytvoří
  `licenses/PYTHON_PACKAGES.md` a texty licencí v `licenses/python/` podle skutečného obsahu sestavení.
  `nastroje\podminky_txt.py` dělá z `TERMS.cs.md` stránku s podmínkami pro instalátor (spouští ho `build.bat`).
- **Bezpečnostní testy** ve složce `tests/` (stahování a přesměrování, integrita modelů, projekty, FFmpeg,
  aktualizace, soukromí; nic nestahují, nastavení uživatele se nedotknou):
  `.venv\Scripts\python.exe -m unittest discover -s tests -v` (funguje i `python -m pytest tests`).
  Výsledky a nálezy auditu: [docs/BEZPECNOSTNI_AUDIT.md](docs/BEZPECNOSTNI_AUDIT.md).

## Jak vydat novou verzi

1. Ověř změny přes `run_dev.bat`.
2. Spusť **`build.bat`** a na dotaz zadej novou verzi ve tvaru `X.Y.Z`
   (např. `1.0.1` – opravy, `1.1.0` – nové funkce). Enter ponechá současnou.
   Bez ptaní: `build.bat 1.0.1`.
3. Počkej asi 10 minut. Výsledek ve složce `dist`: **`KupcakeStudio-Setup-X.Y.Z.exe`**, části
   `KupcakeStudio-Setup-X.Y.Z-1.bin`, `-2.bin` (každá pod 2 GB) a `KupcakeStudio-Setup-X.Y.Z.sha256`
   s kontrolními součty všech souborů. `build.bat` je na konci vypíše.
4. Instalátor spusť – nainstaluje se přes starou verzi (i přes Spellcast a tkStudio). Nastavení a model zůstanou.
5. Do `CHANGELOG.md` dopiš, co je v nové verzi.
6. Změny nahraj na GitHub: `git add -A`, `git commit -m "Verze X.Y.Z"`, `git push`.
7. Na GitHubu: **Releases → Draft a new release**, tag **`vX.Y.Z`** (podle něj kontrola aktualizací pozná
   novou verzi), popis z `CHANGELOG.md` a do přílohy přetáhni **všechny** soubory z bodu 3. Beta verze
   (`1.0.0-beta.2`) označ **Set as a pre-release** – nabídnou se jen uživatelům bety, stabilní verze
   je nedostanou.

Číslo verze je jen v **`version.py`** – `build.bat` ho tam zapíše a odtud se propíše do aplikace
(O aplikaci), do `KupcakeStudio.exe` (Vlastnosti → Podrobnosti) i do názvu instalátoru.

## Jazyky

Rozhraní je v češtině, angličtině, němčině, španělštině a slovenštině (**Nastavení → Jazyk**,
přepne se hned). Poprvé se jazyk zvolí podle Windows, nepodporovaný jazyk = angličtina.

### Jak přidat nový jazyk

1. Zkopíruj `locales\en.json` (nebo `cs.json`) jako `locales\<kód>.json` – kód podle ISO 639-1,
   např. `pl.json` pro polštinu.
2. Nahoře uprav `"_jazyk"` na název jazyka v jeho vlastní podobě (`"Polski"`) a `"_poradi"`
   na pořadí v menu.
3. Přelož hodnoty (texty vpravo). **Klíče vlevo neměň** a ponech `{parametry}` ve složených
   závorkách, např. `"Smazáno slov: {n}"` → `"Usunięto słów: {n}"`. `&` v názvech menu označuje
   písmeno pro Alt+klávesu.
4. Hotovo – nový jazyk se objeví v menu sám, kód se neupravuje. Chybějící texty se zobrazí česky.
   Pro instalačku spusť `build.bat` (složka `locales` se přibalí automaticky).

Jazyk **řeči** pro přepis se volí zvlášť po otevření videa (výchozí je automatické rozpoznání,
poslední volba se pamatuje).

## Rozvržení sekcí

Sekce Titulky, Náhled, Nastavení a Časová osa jde chytit za záhlaví a přetáhnout jinam
(knihovna Qt Advanced Docking System, `doky.py`; vzhled v `theme.qss_doku()`):

- puštění na okraj jiné sekce = vedle ní, doprostřed = jako záložka, mimo okno = samostatné okno
  (i na druhý monitor; tlačítko ⧉ v záhlaví dělá totéž),
- dvojklik na záhlaví = sekce přes celé okno, další dvojklik vrátí rozvržení,
- **Zobrazení → Sekce** – zapnout/vypnout jednotlivé sekce (křížek v záhlaví sekci jen skryje),
- **Zobrazení → Uložená rozvržení** – pojmenovaná rozvržení (např. „Časování“, „Styl“),
- **Zobrazení → Zamknout rozvržení** a **Obnovit výchozí rozvržení**.

Rozvržení včetně samostatných oken se uloží při zavření a obnoví při dalším spuštění.
Licence knihoven třetích stran: `THIRD_PARTY_LICENSES.md` a složka `licenses`.

## Kde co je

| Co | Kde |
|---|---|
| Nainstalovaná aplikace | `%LOCALAPPDATA%\Programs\KupcakeStudio` (od 1.6 bez práv správce; do 1.5 `C:\Program Files\KupcakeStudio`) |
| Nastavení (uložený styl) | `%APPDATA%\KupcakeStudio\styl.json` |
| Jazyk rozhraní a řeči | `%APPDATA%\KupcakeStudio\aplikace.ini` |
| Rozvržení okna / uložená rozvržení | `%APPDATA%\KupcakeStudio\rozlozeni.ini`, `rozvrzeni_vlastni.ini` |
| Model řeči (~3 GB, stáhne se při prvním přepisu) | `%LOCALAPPDATA%\KupcakeStudio\models` |
| Modely přesného časování (~1,2 GB na jazyk) a Demucs | `…\models\zarovnani`, `…\models\demucs` |
| Dočasné soubory | `%LOCALAPPDATA%\KupcakeStudio\tmp` |

Při prvním spuštění se nastavení, rozvržení, styl a stažený model automaticky přesunou ze složek
`tkStudio` a `Spellcast` (`cesty.migruj_stara_data`; když existují obě, má přednost novější tkStudio);
značka `.migrace` v nastavení zajistí, že se to stane jen jednou.

Instalátor má pevné `AppId` (v `installer\KupcakeStudio.iss`) – **nikdy ho neměň**, jinak by se nová
verze nainstalovala vedle staré místo přes ni. Díky němu nová verze nahradí i nainstalovaný Spellcast nebo tkStudio
(starou složku, zástupce a položku v kontextové nabídce odstraní).

## Potřebné nástroje pro sestavení

- `.venv` s Pythonem 3.12 (už existuje)
- FFmpeg v PATH – přibaluje se do aplikace (`winget install Gyan.FFmpeg`)
- Inno Setup 6 – vytváří instalátor (`winget install JRSoftware.InnoSetup`)
