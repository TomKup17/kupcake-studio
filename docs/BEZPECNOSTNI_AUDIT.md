# Bezpečnostní audit kupcake.studio 1.0.0-beta.1

Datum: 1. 11. 2026 · Rozsah: celý zdrojový kód aplikace (Windows, PySide6), závislosti, instalátor, síťová
komunikace a soukromí. Každý nález byl ověřen přímo v aktuálním kódu; opravy jsou implementované a pokryté
testy ve složce `tests/` (70 testů, všechny procházejí). Audit neobsahuje penetrační test sestaveného
instalátoru ani fuzzing FFmpeg/mpv.

Legenda závažnosti: **Critical** (vzdálené spuštění kódu bez interakce), **High** (spuštění kódu / únik dat
při běžném použití), **Medium** (vyžaduje nepravděpodobné podmínky nebo omezený dopad), **Low** (obrana do
hloubky, robustnost). Každá položka je označena jako *ověřený problém*, *potenciální riziko* nebo *doporučení*.

## 1. Shrnutí

Aplikace je napsaná s rozmyslem: žádný `shell=True`, žádný `pickle` pro vlastní data, modely jen přes HTTPS
s pevnou revizí a SHA-256, FFmpeg/mpv omezené na místní soubory, instalátor bez práv správce. **Žádný nález
nebyl Critical ani High.** Nejvýznamnější ověřené problémy (Medium) byly: přesměrování při stahování bez kontroly
cílového hostitele, jednorázová (neopakovatelná) kontrola integrity uložených modelů obejitelná změnou značky,
plné `torch.load` Demucsu a nekontrolovaná adresa ze stránky vydání GitHubu. Vše je opraveno.

Stav po auditu: **vhodné pro veřejnou betu.** Zbývající rizika jsou vlastní každé desktopové aplikaci tohoto
typu (zpracování nedůvěryhodných videí v FFmpeg/mpv, nepodepsaný instalátor, žádná izolace procesu) – viz
oddíl 7. Testy prošly, ale „testy procházejí“ neznamená „aplikace je bezpečná“; znamená to, že ověřené
vlastnosti popsané níže platí pro tuto verzi kódu.

## 2. Co bylo prověřeno

| Oblast | Soubory | Výsledek |
|---|---|---|
| Stahování modelů, přesměrování, integrita | `stahovani.py`, `manifest_modelu.py`, `model.py`, `nastroje/vytvor_manifest.py` | 4 nálezy opraveny (3.1–3.4) |
| Načítání AI modelů | `hlas.py`, `zarovnani.py`, `prepis.py` | 1 nález opraven (3.5), zbytek v pořádku |
| Aktualizace (GitHub Releases) | `aktualizace.py`, `main.py` | jen oznamuje a odkazuje – zachováno; 2 nálezy opraveny (3.6, 3.7) |
| Externí procesy | `export.py`, `nahled.py`, `prepis.py`, `titulky.py`, `hlas.py`, `main.py`, `cesty.py` | v pořádku (seznam argumentů, `-protocol_whitelist file`, bez shellu) |
| Přehrávač | `prehravac.py` | v pořádku (`config=no`, `load_scripts=no`, `ytdl=no`, `load_unsafe_playlists=no`, `protocol_whitelist=[file]`) |
| Projekty a nastavení | `projekt.py`, `presety.py`, `titulky.Styl`, `export.Volby`, `doky.platny_stav` | 2 nálezy opraveny (3.8, 3.9) |
| Soukromí a síť | všechny moduly, proměnné prostředí HF, závislosti | 2 nálezy opraveny (3.10, 3.11); dokumentace v README přepsána |
| Logy a hlášení chyb | `logy.py`, `hardware.py` | 1 nález opraven (3.12) |
| Závislosti | `requirements.txt`, `.venv`, `KupcakeStudio.spec`, `build.bat` | 1 nález opraven (3.13), doporučení v oddílu 8 |
| Instalátor | `installer/KupcakeStudio.iss` | v pořádku; doporučení (podpis) |
| Texty, ASS/SRT/VTT | `titulky.py` | v pořádku (escapování ověřeno testem) |

Nepoužívá se: `pickle` (vlastní data), `eval`/`exec`, `shell=True`, `os.system`, `requests`, `torch.hub`,
`trust_remote_code`. Jediné dva síťové klienty v kódu aplikace jsou `stahovani.py` a `aktualizace.py`
(oba `urllib` přes HTTPS). `nastroje/vytvor_manifest.py` je nástroj vývojáře, do aplikace se nepřibaluje.

## 3. Nálezy a opravy

### 3.1 Přesměrování při stahování bez kontroly hostitele – Medium, ověřený problém, opraveno
`_JenHttps.redirect_request` kontrolovalo jen schéma `https`. Server (nebo kdokoli, kdo by dokázal odpovědět
za huggingface.co) mohl přesměrovat na libovolný HTTPS hostitel včetně interních adres. Dopad omezoval fakt,
že stažený soubor se stejně ověřuje SHA-256 (podvržený obsah se smaže) – šlo tedy spíš o SSRF do vnitřní sítě
a únik `User-Agent`/požadavku než o spuštění kódu.
**Oprava:** `stahovani.over_url()` – každá adresa i každé přesměrování musí být `https`, bez uživatele/hesla,
port 443, hostitel ze seznamu `HOSTY` (start) resp. `HOSTY_PRESMEROVANI` (CDN Hugging Face `*.hf.co`,
`*.huggingface.co`). IP adresy (včetně privátních a `169.254.169.254`), `localhost`, `*.localhost`, cizí domény
i „podobné“ domény (`huggingface.co.evil.example`, `xhf.co`) se odmítnou **před připojením**. Opener nemá
handlery pro `http`, `ftp`, `file`, `data`; přesměrování nejvýš 5; SSL kontext výslovně
`ssl.create_default_context()` (ověření certifikátu i názvu). DNS rebinding: hostitel mimo seznam se nikdy
nekontaktuje a povolený hostitel musí předložit platný certifikát, takže podvržená DNS odpověď nestačí.
Testy: `tests/test_stahovani.py::TestAdresy` (14 zakázaných tvarů, povolené CDN, limit přesměrování).

### 3.2 Integrita uložených modelů obejitelná změnou metadat – Medium, ověřený problém, opraveno
Značka `.hotovo` nesla jen revizi; `je_pripraveno()` pak kontrolovalo jen velikosti souborů. Kdo mohl zapsat
do `%LOCALAPPDATA%\KupcakeStudio\models` (jiný program běžící pod stejným uživatelem, chyba disku, ruční
„oprava“), mohl model vyměnit za jiný stejné velikosti a aplikace ho načetla bez ověření. U Demucsu se
navíc kontrolovala jen existence značky, ne její obsah.
**Oprava:** značka nese otisk (velikost + čas změny v ns) každého ověřeného souboru; změna otisku vynutí nové
ověření SHA-256, při neshodě se soubor smaže a nabídne stažení (po souhlasu). Plné hashování při každém startu
(3 GB ≈ 10 s) se nedělá záměrně – otisk je kompromis mezi bezpečností a výkonem. Poznámka: útočník se
stejnými právy, jako má uživatel, může přepsat i samotnou aplikaci; tahle ochrana míří na poškození a
„náhodné“ záměny, ne na plně kompromitovaný účet. Po aktualizaci se už stažené modely **jednou** znovu
ověří (stará značka bez otisků); dialog před přepisem už u takového modelu nehlásí „stáhne se“ (`model.je_stazen`).
Testy: `TestZnackaAOvereni`, `TestDemucs` (podvržená značka, změna obsahu se stejnou velikostí, stará značka).

### 3.3 Soubor jiné velikosti se stahoval celý – Low, ověřený problém, opraveno
Při neshodě velikosti se chyba zjistila až po stažení (až 3 GB) při `_over()`. Nově se porovná
`Content-Length` / `Content-Range` s manifestem a soubor jiné velikosti se odmítne hned (nic se nečte).
Zároveň: neúplný `.part` se nikdy nevydává za hotový soubor; navázání s jiným celkem se zahodí; `.part`
větší než cíl se zahodí; server bez podpory `Range` → od začátku. Testy: `TestStahniSoubor` (9 případů
včetně přerušení uprostřed a navázání).

### 3.4 Adresa Demucsu z manifestu bez kontroly – Low, obrana do hloubky, opraveno
`priprav_demucs` používal `DEMUCS["url"]` přímo; `_otevri` ji sice kontrolovalo, ale až po zápisu značky
a dotazu na souhlas. Nově `over_url()` hned na začátku. Test: `TestDemucs::test_nepovolena_adresa_v_manifestu`.

### 3.5 Demucs: `torch.load(..., weights_only=False)` – Medium, ověřený problém, opraveno
Soubor `.th` Demucsu je pickle slovníku `{klass, args, kwargs, state, training_args}`; autoři nevydávají
safetensors a `demucs.states.load_model` potřebuje odkaz na třídu modelu. Plné `torch.load` spustí libovolný
kód v souboru. Dopad omezovalo to, že se načítá jen soubor s ověřeným SHA-256 z pevného manifestu.
**Oprava (`hlas.nacti_balicek`):** načtení **výhradně** omezeným unpicklerem (`weights_only=True`) uvnitř
`torch.serialization.safe_globals(povolene_tridy())`. Oficiální soubor `955717e8-8726e21a.th` byl stažen
(přes `stahovani.priprav_demucs`, SHA-256 sedí) a jeho pickle rozebrán nástrojem `pickletools` bez spuštění:
obsahuje jen GLOBAL odkazy `demucs.htdemucs.HTDemucs`, `fractions.Fraction` (kwargs `segment`),
`numpy.core.multiarray.scalar` + `numpy.dtype` (float64 v `training_args`), a torch/`collections.OrderedDict`,
které torch povoluje sám. Přesně tyto čtyři typy (plus skalár pod novým názvem `numpy._core…` z numpy 2 a
`numpy.dtypes.Float64DType`, který vzniká při sestavení dtype) jsou povolené – žádná funkce, která by
spouštěla kód. Skutečný soubor se takto načte beze zbytku a model se sestaví (HTDemucs, 4 zdroje,
42 M parametrů). Jakýkoli jiný objekt (`os.system`, `eval`, `__reduce__`) unpickler odmítne; plné
`torch.load` (`weights_only=False`) už v kódu není. Pořadí je: SHA-256 → omezené načtení.
Testy: `tests/test_hlas.py` (tvar oficiálního souboru, 4 podvržené balíčky, seznam povolených typů; test na
skutečném souboru běží, je-li nastaveno `KUPCAKE_SKUTECNE_LOCALAPPDATA` – nic nestahuje).
Ostatní modely: wav2vec2 pro cs/en/MMS jsou `safetensors`; de/es/fr/it/pl/sk jsou `pytorch_model.bin`, které
transformers 5.22 načítá s `weights_only=True` (nově předáno výslovně); Whisper je formát CTranslate2 (ne pickle).

### 3.6 Adresa stránky vydání z GitHub API bez kontroly – Medium, ověřený problém, opraveno
`html_url` z odpovědi API se předával rovnou do `QDesktopServices.openUrl`. Při podvržené odpovědi (kompromitace
GitHubu, chybná TLS validace, proxy s vlastní CA) by tlačítko „Stáhnout“ otevřelo cizí stránku. Nově
`aktualizace.stranka_vydani()` přijme jen `https://github.com/<repozitář>/…`, jinak stránku Releases.
Dál: odpověď nejvýš 2 MB, jen HTTP 200, odpověď musí být seznam, přesměrování jen na `api.github.com`
(HTTPS), bez `http/ftp/file/data`. Princip „jen oznámit a odkázat, nikdy nestahovat ani nespouštět“ je zachován
a ověřen (`tests/test_aktualizace.py`).

### 3.7 Nekontrolované hodnoty nastavení v kontrole aktualizací – Low, robustnost, opraveno
`float(nastaveni.value("aktualizace/posledni"))` by při ručně poškozeném INI spadl (nezachycená výjimka
v hlavním vlákně). Nově ošetřeno; nesmyslná hodnota = kontrola proběhne.

### 3.8 Poškozený projekt mohl shodit aplikaci – Medium, ověřený problém, opraveno
`int(data["kupcake.studio"])` stálo mimo `try` – projekt s `"kupcake.studio": "abc"` skončil nezachycenou
výjimkou (dialog chyby místo hlášky „poškozený projekt“). Hodnoty `smycka`, `slova`, `jazyk`, `info`,
`rozvrzeni` se nepřeváděly na typ a mohly selhat až později uvnitř GUI (např. smyčka jako text). Nově
`projekt.nacti()` převádí každou hodnotu přes `_cislo`/`_text`/`_seznam` (odmítá bool místo čísla, NaN,
nekonečno), nepodstatné části ve špatném tvaru nahradí výchozími (projekt se otevře), podstatné skončí
`ChybaProjektu`; limit velikosti 64 MB. Žádná změna formátu – staré projekty se načtou beze změny.
Testy: `tests/test_projekt.py` (24 poškozených variant, BOM, round-trip).

### 3.9 Atomické ukládání: dočasný soubor bez fsync a bez úklidu – Low, robustnost, opraveno
`uloz()` zapisoval `.tmp` a přejmenoval, ale bez `fsync` (po pádu systému mohl být nový soubor prázdný) a při
chybě serializace nechával `.tmp` ležet. Nově: serializace nejdřív v paměti, `flush` + `fsync`, při chybě
úklid; starý projekt zůstane netknutý (test).

### 3.10 Proměnné prostředí Hugging Face nastavené pozdě – Low, potenciální riziko, opraveno
`HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` se nastavovaly v `zarovnani.py`, ale `huggingface_hub` si je čte při
importu – a `prepis.py` (faster-whisper → huggingface_hub) se importuje dřív, v pozadí hned po startu.
V praxi nic nestahovalo (všechny volání jdou s místní cestou), ale záruka byla jen „náhodná“. Nově se
`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY`, `HF_HUB_DISABLE_IMPLICIT_TOKEN`
(nehledat token uživatele v `~/.cache/huggingface`) a `DO_NOT_TRACK` nastavují v `cesty.py`, který každý modul
importuje jako první. Test `tests/test_soukromi.py` ověřuje, že `huggingface_hub.constants` to vidí.

### 3.11 Dokumentace soukromí byla neúplná – Low, ověřený problém, opraveno
Původní oddíl README říkal pravdu, ale nezmiňoval: CDN Hugging Face, že server vidí IP adresu a **který**
model se stahuje (prozrazuje jazyk/volbu), kontrolu 5 s po startu, že odkazy otevírají prohlížeč, co je v logu
(cesty k videím) a v hlášení chyby (hardware), ani SmartScreen. Oddíl je přepsán jako tabulka „kdy – kam –
co se posílá – jak vypnout“. Ověřeno: **žádná telemetrie, žádný analytický nástroj, žádné odesílání
videí, zvuku, přepisů ani názvů souborů** nikam. Texty v aplikaci (`oaplikaci.soukromi`, `uvitani.text`) jsou
pravdivé a nebylo třeba je měnit.

### 3.12 Hlášení chyby obsahovalo uživatelské jméno – Low, ověřený problém, opraveno
„Zkopírovat hlášení“ přidávalo cestu k logu `C:\Users\<jméno>\AppData\…` a tracebacky s cestami. Nově
`logy.bez_profilu()` nahrazuje cesty do profilu za `%LOCALAPPDATA%` / `%APPDATA%` / `%USERPROFILE%` v celém
hlášení. Samotný log na disku se nemění (zůstává místní).

### 3.13 `build.bat` instaloval PyInstaller bez verze – Low, dodavatelský řetězec, opraveno
Chybějící PyInstaller se doinstalovával jako „nejnovější z PyPI“, mimo připnuté `requirements.txt`. Nově
`pyinstaller==6.22.3`.

## 4. Co bylo ověřeno a je v pořádku (beze změny)

- **Externí procesy:** všech 11 volání `subprocess` je se seznamem argumentů, bez shellu, s `CREATE_NO_WINDOW`;
  vstupy přes `cesty.vstup_ffmpeg()` (absolutní cesta – název začínající `-` ani `protokol:` se nevyloží jako
  přepínač, `-protocol_whitelist file` – HLS/concat playlist uvnitř „videa“ nic nestáhne). Titulky pro export
  jdou vždy z pevné cesty `tmp/titulky.ass` v datové složce, ne z uživatelské cesty. Výstup exportu: přípona
  vynucená podle formátu, zdrojové video se nikdy nepřepíše (tři nezávislé kontroly, test), přepsání jiného
  souboru se v panelu oznámí. `explorer /select,` jako seznam. Testy: `tests/test_export.py`.
- **mpv:** bez konfigurace a skriptů z profilu, bez youtube-dl, jen `file` protokol, okno mpv nepřijímá vstup.
- **FFmpeg:** přibalený FFmpeg 9.0 (gyan.dev); vyhledané 2026 CVE (VobSub, TY, RTP/ASF demuxery) uvádějí jako
  postižené verze do 8.1.2, 9.0 by měla být mimo, ale přesný stav potvrzený nebyl. Platí obecně: FFmpeg
  zpracovává nedůvěryhodné soubory a je největší reálnou plochou útoku (oddíl 7).
- **Projekt/nastavení:** `Styl.z_dict`, `Volby.z_dict`, `Presety` ignorují neznámé klíče a špatné typy;
  rozvržení QtAds se před obnovou validuje jako XML a jen se známými sekcemi (`doky.platny_stav`) – QtAds
  jinak na vadném XML padá.
- **Příkazová řádka / kontextová nabídka:** `sys.argv[1]` se otevře jen, když je to existující soubor; podle
  přípony jako projekt nebo video; nic se nevykonává.
- **ASS/SRT/VTT:** `{`, `}`, `\` se escapují (U+2060 za zpětným lomítkem), VTT HTML entity – ověřeno testem.
- **Instalátor:** `PrivilegesRequired=lowest`, pevné AppId, odinstalace staré verze jen přes její
  vlastní odinstalátor z HKLM (zapisuje správce), `[Run]` jen aplikace samotná, žádné stahování.
- **Logy:** rotace 4 × 1 MB, bez obsahu titulků; obsahují cesty k videím (zdokumentováno).
- **Qt:** `QTextBrowser.setOpenExternalLinks(True)` jen pro přibalený CHANGELOG a licence.

## 5. Soukromí a síť – výsledná mapa

| Doména | Kdy | Data | Lze vypnout |
|---|---|---|---|
| `api.github.com` | 5 s po startu, max. 1×/24 h, jen když je `links.GITHUB_REPO` vyplněný (teď prázdný = vypnuto) | GET seznam vydání, `User-Agent: kupcake.studio/<verze>`, IP adresa | Nastavení → Kontrolovat nové verze |
| `huggingface.co`, `*.hf.co`, `*.huggingface.co` | první použití modelu, po souhlasu | GET souborů modelu, `User-Agent`, IP; **název modelu** (= přesnost / jazyk) | odmítnout dialog |
| `dl.fbaipublicfiles.com` | první oddělení hlasu, po souhlasu | GET váhy Demucsu, `User-Agent`, IP | odmítnout dialog |
| `github.com`, `tomkup.cz`, Instagram, TikTok | jen po kliknutí uživatele | otevře se prohlížeč | – |

Závislosti, které by mohly komunikovat samy, a proč nekomunikují: `huggingface_hub`/`transformers` (OFFLINE +
telemetrie vypnutá, všechna volání `local_files_only=True`), `faster-whisper` (dostává místní složku, nikdy
název modelu), `torch`/`demucs` (`torch.hub` se nepoužívá), `onnxruntime` (žádná telemetrie v pip balíčku),
`mpv` (`ytdl=no`, `protocol_whitelist=[file]`), FFmpeg (`-protocol_whitelist file`), Qt (žádná síť).
`truststore`, `httpx2`, `httpcore2` jsou závislosti huggingface_hub 2.4 (autor Tom Christie, legitimní
nástupce `httpx`) a aplikace je nevolá.

## 6. Změněné a nové soubory

Změněno: `stahovani.py` (allowlist adres, otisky ve značce, kontrola délky), `aktualizace.py` (validace
adresy a odpovědi), `projekt.py` (typová kontrola, fsync), `hlas.py` (omezený unpickler), `zarovnani.py`
(výslovné `weights_only=True`), `model.py` + `dialogy.py` (`je_stazen` – správný text před přepisem),
`cesty.py` (proměnné HF), `logy.py` (`bez_profilu`), `build.bat` (připnutý PyInstaller), `README.md`
(Soukromí, Vývoj), `SECURITY.md`, `CHANGELOG.md`.
Nové: `tests/_zaklad.py`, `tests/conftest.py`, `tests/test_stahovani.py` (27), `tests/test_aktualizace.py`
(16), `tests/test_projekt.py` (12), `tests/test_export.py` (8), `tests/test_hlas.py` (4), `tests/test_soukromi.py`
(3), `docs/BEZPECNOSTNI_AUDIT.md`. Beze změny GUI, workflow, formátu projektů a manifestu modelů.

Spuštění testů: `.venv\Scripts\python.exe -m unittest discover -s tests -v` → `Ran 70 tests … OK`
(2,4 s; `test_hlas` načítá PyTorch). Testy běží v izolované dočasné složce (APPDATA/LOCALAPPDATA), nic
nestahují, síť je nahrazená falešnými odpověďmi. `pyflakes` na změněných souborech bez nových hlášení.

## 7. Zbývající rizika (neopraveno, s důvodem)

- **Zpracování nedůvěryhodných videí v FFmpeg/mpv (potenciální riziko, Medium):** jakákoli chyba v demuxeru
  či dekodéru může vést ke spuštění kódu s právy uživatele. Aplikace to nemůže vyloučit; zmírnění = aktuální
  FFmpeg/libmpv při každém vydání a `-protocol_whitelist file`. Sandboxování procesu FFmpeg (Windows
  AppContainer / job object) by byla nová složitost nad rámec bety.
- **Nepodepsaný instalátor (doporučení, Medium):** SmartScreen varuje a uživatel nemá jak poznat podvrh jinak
  než SHA-256 z Releases. Podpis kódu (OV/EV certifikát, nebo aspoň Sigstore/`gh attestation`) je největší
  zbývající krok pro důvěryhodnost distribuce.
- **Stejná práva jako uživatel:** modely, nastavení i aplikace sama leží v profilu uživatele; jiný program
  pod stejným účtem je může změnit. Otisky ve značce to zmírňují, ne řeší. Integrita samotné instalace
  (`_internal\*.dll`, `.pyd`) se nekontroluje – řeší až podpis instalátoru a případný self-check.
- **`requirements.txt` bez hashů:** verze jsou připnuté, ale `pip` neověřuje hash balíčků. Hash-pinning
  (`pip-compile --generate-hashes`) je doporučený, ale PyTorch z vlastního indexu a 66 balíčků = větší změna,
  kterou je třeba ověřit při příštím sestavení (ne „bezhlavě“ teď).
- **Kontrola aktualizací hlásí novou verzi jen na základě dat z GitHubu:** podvržená odpověď může nanejvýš
  zobrazit falešnou notifikaci a otevřít stránku Releases repozitáře – uživatel tam nic podvrženého nenajde,
  pokud není kompromitován sám repozitář/účet (doporučení: 2FA, chráněné větve, podpis vydání).
- **Instalátor Inno Setup:** `[Run]` spouští aplikaci po instalaci (běžné); `CloseApplications=yes`;
  kontextová nabídka registruje `"…\KupcakeStudio.exe" "%1"` – v pořádku. Neověřeno chováním, jen čtením.

## 8. Závislosti

Všech 66 balíčků je připnuto na přesnou verzi (`requirements.txt`), včetně nepřímých. Kontrola vůči známým
zranitelnostem (web, 1. 11. 2026):

| Balíček | Verze | Stav |
|---|---|---|
| torch | 2.11.0+cu128 | ≥ 2.10.0 – opravuje CVE-2026-24747 (poškození paměti ve `weights_only` unpickleru) i CVE-2025-32434 |
| transformers | 5.22.1 | ≥ 5.3.0 – opravuje CVE-2026-4372 (RCE přes `config.json` → cizí repo) a CVE-2026-1839; navíc aplikace běží offline, takže cesta přes Hub neexistuje |
| FFmpeg (přibalený) | 9.0 | 2026 CVE uvádějí postižené verze ≤ 8.1.2; sledovat a přibalovat aktuální build |
| PySide6 / Qt | 6.12.0 | přesná verze vyžadovaná PySide6-QtAds; WebEngine je v `.venv` jako závislost metabalíčku, **do sestavení se nepřibaluje** (`excludes` ve spec, ověřeno v `dist`) |
| faster-whisper / CTranslate2 | 1.2.1 / 4.8.4 | žádné známé CVE nalezeny; model není pickle |
| demucs, julius, einops | 4.1.0 | model pickle – řešeno v 3.5 |
| onnxruntime | 1.31.1 | používá jen Silero VAD přibalený ve faster-whisper (místní soubor) |
| pyinstaller | 6.22.3 | připnuto i v `build.bat` |

Nástroj `pip-audit` není v `.venv` nainstalován (neinstalováno bez vyžádání). Doporučený postup před vydáním:
`.venv\Scripts\python.exe -m pip install pip-audit` a `.venv\Scripts\python.exe -m pip_audit -r requirements.txt`.
Nepotřebné balíčky: `PySide6-WebEngine`, `PySide6-Pdf` (závislosti metabalíčku PySide6; v sestavení chybí –
v pořádku), `typer`/`rich`/`shellingham`/`annotated-doc` (CLI Demucsu a huggingface_hub, aplikace je nevolá).
Žádné „bezhlavé“ aktualizace nebyly provedeny – verze zůstávají, jak jsou odzkoušené.

## 9. Další doporučení (nad rámec auditu)

1. Podepsat instalátor a `KupcakeStudio.exe` (code signing) a zveřejnit `.sha256` u každého vydání (už se
   generuje v `build.bat`).
2. Při změně modelu Demucs (nová adresa v manifestu) znovu rozebrat pickle `pickletools` a upravit
   `hlas.povolene_tridy()` – jiný soubor s jinými typy se omezeným unpicklerem nenačte (záměrně).
3. Přidat `pip-audit` do postupu vydání a zvážit hash-pinning `requirements.txt`.
4. Při každém vydání přibalit aktuální FFmpeg a libmpv (největší plocha útoku jsou vstupní videa).
5. Na GitHubu: zapnout soukromé hlášení zranitelností (Security → Report a vulnerability – SECURITY.md na něj
   odkazuje), 2FA, ochranu větve `main`, Dependabot/pip-audit.
6. Spouštět `tests/` před každým sestavením (např. v `build.bat` před PyInstallerem).
7. Zvážit zobrazení domény v dialogu souhlasu i pro CDN (dnes „huggingface.co“ – pravdivé, soubory ale fyzicky
   přijdou z `*.hf.co`); README to už vysvětluje.

## 10. Závěrečné zhodnocení

Ověřené problémy: 10 (3.1–3.4, 3.5, 3.6, 3.8, 3.11, 3.12, 3.13), všechny Medium nebo Low, všechny opravené
a pokryté testy. Potenciální rizika: 3 (oddíl 7), zdokumentovaná s důvodem, proč nejsou řešena v betě.
Doporučení: 7 (oddíl 9). Kód aplikace neobsahuje telemetrii ani skryté síťové požadavky; veškerá síťová
komunikace je vyjmenovaná v oddílu 5 a odpovídá tomu, co říká README. Aplikace je v tomto stavu vhodná
pro veřejnou betu s tím, že největší zbývající rizika (nepodepsaný instalátor, FFmpeg jako parser
nedůvěryhodných souborů) jsou rizika distribuce a platformy, ne chyby v kódu.
