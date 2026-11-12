# Změny

## Neuvydáno – změny po 1.0.0-beta.2

- Soubor `LICENSE` je znovu nezměněný text GNU GPL v3, aby GitHub licenci repozitáře rozpoznal. Copyright
  a označení `GPL-3.0-only` zůstávají v README, v `ADDITIONAL_PERMISSION.md` a v hlavičkách zdrojových souborů.

## 1.0.0-beta.2 – 2026-11-12

### Licence a dokumentace
- `THIRD_PARTY_LICENSES.md` přepsán podle skutečného obsahu instalátoru: přesné verze všech součástí, opravené
  údaje (mpv je sestavení pod GPL s kodéry x264 a x265; FFmpeg 9.0.2; Qt-ADS 5.1.1; licence uromanu) a doplněné
  součásti – knihovny uvnitř PyAV (FFmpeg, x264, x265, libvpx, dav1d, SVT-AV1, Opus, WebP, VMAF, libvpl),
  Silero VAD, lameenc a LAME, hf-xet, Python, OpenSSL, SQLite, libffi, expat, Intel oneMKL a OpenMP,
  běhové knihovny Microsoft Visual C++.
- Nový oddíl „Zdrojové kódy přibalených programů“: přesná verze a odkaz na zdrojový kód pro FFmpeg, mpv,
  FFmpeg uvnitř PyAV, Qt, PySide6, Qt-ADS a LAME; zdrojové kódy na požádání poskytnu.
- Úplný seznam balíčků Pythonu v instalátoru (55): `licenses/PYTHON_PACKAGES.md` s názvem, verzí a licencí,
  plná znění v `licenses/python/`. Generuje ho rozšířený `licenses/prenes_licence.py` z metadat balíčků podle
  skutečného obsahu sestavení (bez nové závislosti).
- Copyright (C) 2026 Tomáš Kupec a upřesnění licence kódu na `GPL-3.0-only`: `LICENSE`, README, hlavičky
  `SPDX-License-Identifier` ve všech vlastních zdrojových souborech.
- `ADDITIONAL_PERMISSION.md`: dodatečné svolení podle čl. 7 GPLv3 pro spojení s běhovými knihovnami NVIDIA CUDA
  a cuDNN a s Intel Math Kernel Library. Výslovně uvedeno, že knihovny NVIDIA a Intel, název a logo nejsou pod
  GPL a mají vlastní podmínky.
- README: ochranné známky třetích stran, poznámka o patentech kodeků H.264, H.265 a AAC, odstavec o tom, jak
  aplikace vzniká.

### Podmínky použití
- Nové podmínky použití `TERMS.md` (anglicky) a `TERMS.cs.md` (česky): kdo aplikaci poskytuje, licence a cena,
  bez záruky v rozsahu, v jakém to zákon dovoluje, nepřesnost přepisu, odpovědnost za obsah, licence modelů,
  připojení k internetu, ochranné známky třetích stran, rozhodné právo.
- V aplikaci: O aplikaci → Podmínky použití a odkaz v úvodním okně. Úvodní okno nově říká i to, že aplikace
  jednou denně zjišťuje novou verzi na GitHubu a že to jde vypnout v Nastavení.
- Instalátor má stránku s podmínkami použití (`installer\PODMINKY.txt`, dělá ho `nastroje\podminky_txt.py`).
- Podmínky uvádějí, že knihovny NVIDIA se používají jen spolu s aplikací a za podmínek licencí NVIDIA.

### Přesné časování
- Vícejazyčný model MMS (licence CC BY-NC 4.0, jen nekomerční použití) je ve výchozím stavu **vypnutý**. Zapnout
  jde v Nastavení → „Přesné časování i pro další jazyky“ po potvrzení upozornění na licenci; licenci uvádí
  i dotaz na stažení modelu.
- Jazyky bez vlastního modelu (jiné než cs, sk, en, de, es, fr, it, pl) zůstávají bez MMS na časech z přepisu –
  bez chybové hlášky; dialog před přepisem to řekne předem a „Znovu zarovnat výběr“ jen upozorní.
- Model Whisper large-v3-turbo se stahuje z nové adresy repozitáře (`dropbox-dash/faster-whisper-large-v3-turbo`,
  dříve `mobiuslabsgmbh/…`). Revize i kontrolní součty jsou stejné, už stažený model se znovu nestahuje.

### Ostatní
- Export ProRes a ProRes 4444 už nezapisuje do snímků značku výrobce `apl0` (zůstává výchozí značka kodéru
  FFmpeg). Kodek, profil, kvalita i průhlednost jsou beze změny.
- Úklid: neutrální komentáře u výchozího stylu v `titulky.py`; staré návrhy ikon z dřívějších pracovních názvů
  už nejsou v repozitáři.
- Testy: 92 (nově licenční dokumenty a podmínky použití, model MMS, adresa modelu turbo).

## 1.0.0-beta.1 – 2026-11-01

První veřejná BETA (navazuje na interní verze 1.0–1.6 níže).

### Upozornění pro betu
- Úvodní okno při prvním spuštění: co znamená BETA, bez záruky (GPL-3.0), původní videa se nepřepisují,
  zpracování jen na počítači; odkazy Licence a Nahlásit chybu. Začít se odemkne až po „Rozumím“, souhlas se
  uloží a znovu se okno ukáže jen u nové hlavní verze (např. beta → 1.0).
- Export nikdy nepřepíše zdrojové video – kontrola v panelu exportu, před spuštěním i přímo v exportu
  (i stejný soubor pod jiným zápisem cesty nebo velikostí písmen).
- O aplikaci: řádek „Poskytováno bez záruky · GPL-3.0“ otevře text licence. README: Beta verze, Bez záruky, Soukromí.

### GitHub
- Zdrojový kód na https://github.com/TomKup17/kupcake-studio; odkaz GitHub v O aplikaci, Nahlásit chybu
  vede na GitHub Issues, kontrola aktualizací sleduje Releases tohoto repozitáře.
- Instalátor je rozdělený na `Setup.exe` a části `-1.bin`, `-2.bin` (GitHub bere soubory jen do 2 GB);
  `.sha256` obsahuje součty všech částí. Chybí-li část vedle instalátoru, řekne to srozumitelně.
- `libmpv-2.dll` (přes 100 MB) není v repozitáři – návod ke stažení v README → Vývoj.

### Projekty
- Rozpracovaná práce se ukládá do projektu `.kupcake` (čitelný JSON): video, titulky se slovy, zámky,
  značky, styl, časování, smyčka a rozvržení sekcí. Soubor → Uložit projekt (Ctrl+S), Uložit jako
  (Ctrl+Shift+S), Otevřít projekt nebo video (Ctrl+O), Nedávné projekty; projekt jde i přetáhnout do okna
  nebo otevřít dvojklikem (instalátor registruje příponu .kupcake).
- Video přesunuté i s projektem do jiné složky se najde (relativní cesta); jinak se aplikace zeptá, kde je.
- Upozornění na neuložené změny (Uložit / Zahodit / Zrušit) při zavření i otevírání jiného videa; „•“ v titulku.
- Automatické ukládání každé 2 minuty; když aplikace spadne, po dalším spuštění nabídne obnovu.

### Chyby a logy
- Nečekané chyby (i ve vláknech na pozadí) se zachytí: srozumitelná hláška, aplikace běží dál, tlačítko
  „Zkopírovat hlášení“ (verze, systém, chyba) a podrobnosti. Selhání přepisu / exportu stejně.
- Log `%LOCALAPPDATA%\KupcakeStudio\logs\kupcake.log` s rotací (4 × 1 MB).
- Známé příčiny lidsky: plný disk, bez internetu, video bez zvuku.
- Před exportem a stahováním modelu se kontroluje volné místo na disku.
- Video bez zvukové stopy: místo chyby hláška a editor pro ruční titulky.
- Bez NVIDIA / CUDA: dialog před přepisem jasně řekne, že přepis poběží na procesoru a bude pomalejší.

### Beta, aktualizace, soukromí
- Verze `1.0.0-beta.1`, nenápadný štítek BETA vedle loga, Nápověda → Nahlásit chybu / Zpětná vazba
  (odkaz v `links.py`).
- Kontrola nové verze přes GitHub Releases (repozitář v `links.py`): nejvýš jednou za den, na pozadí,
  nabídka Stáhnout / Přeskočit tuto verzi; vypnutí v Nastavení.
- O aplikaci a README: vše běží lokálně, nic se neodesílá (kromě stažení modelů a kontroly aktualizací).

### Bezpečnostní audit (docs/BEZPECNOSTNI_AUDIT.md)
- Stahování modelů: přesměrování jen na huggingface.co / `*.hf.co` / dl.fbaipublicfiles.com (dřív jen „HTTPS“),
  odmítnutí IP adres, localhost, jiných portů a přihlašovacích údajů v adrese; soubor jiné velikosti se odmítne
  už podle hlavičky serveru; značka `.hotovo` nese otisk ověřených souborů – změněný model se znovu ověří
  (po aktualizaci se už stažené modely jednou znovu zkontrolují SHA-256, nic se nestahuje).
- Demucs: model se načítá výhradně omezeným unpicklerem PyTorch (`weights_only=True`; povolené jen typy, které
  oficiální soubor skutečně obsahuje – HTDemucs, Fraction, numpy float64), plné `torch.load` už se nepoužívá.
- Kontrola aktualizací: odkaz z odpovědi API se použije jen na github.com v repozitáři aplikace, odpověď
  omezená na 2 MB, přesměrování jen na api.github.com.
- Projekty: přísnější kontrola typů při načítání (poškozený projekt = hláška, ne pád), zápis s fsync.
- Knihovny Hugging Face offline a bez telemetrie už od startu (`cesty.py`); hlášení chyby bez uživatelského jména.
- Nová složka `tests/` (70 testů: stahování, integrita, projekty, FFmpeg, aktualizace, Demucs, soukromí);
  README → Soukromí přepsán podle skutečného chování (tabulka: kdy, kam, co se posílá).

### Ostatní
- Licence GPL-3.0 v souboru `LICENSE`. Odinstalace: „Smazat i stažené modely a nastavení?“ (projekty a videa
  zůstanou). Úklid: odstraněné nepoužívané texty a kód.
- Instalátor vedle sebe vytvoří `.sha256` s kontrolním součtem.

### Okno O aplikaci
- Nové okno (Nápověda → O aplikaci nebo klik na logo v záhlaví) jako překryvná karta: animovaný cupcake,
  logo, verze a datum sestavení (`version.py` – `DATUM` zapisuje build.bat), popis a autor.
- Tlačítka Instagram a TikTok (oranžová), web a GitHub (s obrysem) s jednobarevnými ikonami značek
  (Simple Icons, CC0); adresy v `links.py`, GitHub se ukáže, až bude vyplněný.
- Co je nového (sekce aktuální verze z CHANGELOG.md), Licence (GPL-3.0 – nový soubor `LICENSE` – a knihovny
  z THIRD_PARTY_LICENSES.md) a Kopírovat informace o systému (verze, Windows, procesor, grafická karta,
  ovladač, CUDA) pro hlášení chyb.
- Po 5. úspěšném exportu se jednou (nikdy během práce) ukáže nenápadná připomínka „Líbí se ti kupcake.studio?“
  s Instagramem, TikTokem a „Už nezobrazovat“; vypnout jde i v Nastavení.

### Přehlednější Nastavení
- Každá kategorie (hlavička i rozbalený obsah) má vlastní pozadí, které se střídá A, B, A, B… podle pořadí
  (`rozvrzeni.obnov_stridani`) – funguje i po přidání nebo přeházení kategorií. Rozbalená kategorie má vlevo
  oranžový proužek 3 px přes celou výšku a výraznější (bílou) hlavičku. Barvy v `theme.py`
  (`SKUPINA_POZADI_A`, `SKUPINA_POZADI_B`, `SKUPINA_PROUZEK`, `SKUPINA_HLAVA_ROZBALENA`).

### Úvodní splash screen
- Hned po spuštění se uprostřed obrazovky ukáže cupcake (`assets/splash/cupcake.png`), pod ním
  „kupcake.studio“ a menším písmem „by iamtom.kup“ – tmavá karta bez rámečku a lišty, bez vlastní položky
  na hlavním panelu. Fade-in 0,4 s, celkem 3 s (`splash.DELKA_S`), fade-out 0,4 s, pak hlavní okno.
- Klik nebo Esc splash přeskočí. Hlavní okno se staví už během splashe a knihovny pro přepis se načítají
  na pozadí – po splashi se na nic nečeká.
- Bez obrázku se ukáže jen text. Složka `assets` se přibaluje do instalátoru.

## 1.6.0 – 2026-10-31

### Slabší počítače
- **Rozpoznání hardwaru** (`hardware.py`): NVIDIA karta a volná VRAM přes ovladač (NVML), procesor z registru.
  Výchozí výpočet: ≥ 6 GB volné VRAM → large-v3 float16, 4–6 GB → int8_float16, méně nebo bez NVIDIA →
  procesor (int8). Přesné časování a Demucs běží na stejném zařízení.
- Když grafické kartě dojde paměť, přepis (i přesné časování) automaticky doběhne na procesoru a místo
  chyby se ukáže srozumitelné upozornění s radou.
- **Přesnost přepisu** (Nastavení → Přesnost přepisu, i v dialogu před přepisem): Nejpřesnější (large-v3),
  Rychlá (large-v3-turbo, asi 3× rychlejší), Úsporná (medium) – každá s krátkým vysvětlením. Model se stáhne
  při prvním výběru (se souhlasem, průběhem a kontrolou SHA-256).
- **Přepis počítat na:** Automaticky / Jen procesor. V menu Nastavení řádek „Přepis běží na: …“.
- Dialog před přepisem ukáže, na čem přepis poběží, a **odhad doby** podle délky videa, modelu a hardwaru
  (změřeno: large-v3 na GPU 12× rychleji než reálný čas, na i7-12700KF 1,2×; turbo 39× / 3,1×).
- Export bez NVENC: panel to oznámí jedním řádkem a použije x264 na procesoru.
- Pro test bez grafické karty: proměnná prostředí `KUPCAKE_CPU=1` (přepis, časování i export na procesoru),
  `KUPCAKE_VRAM_GB=4.5` předstírá méně volné VRAM.

### Bezpečnost
- **Stahování modelů** (Whisper, zarovnání slov, Demucs) jen se souhlasem: před každým stažením se aplikace
  zeptá (co, velikost, odkud). Odmítnutí přepis zruší, u zarovnání / Demucsu přepis pokračuje bez nich.
- Jen HTTPS z oficiálních zdrojů (huggingface.co, dl.fbaipublicfiles.com), i přesměrování jen na HTTPS;
  modely v **pevné revizi** a každý soubor ověřený **SHA-256** (`manifest_modelu.py`, `stahovani.py`,
  generuje `nastroje/vytvor_manifest.py`). Nesedící soubor se smaže a ukáže se srozumitelná chyba.
  Už stažené modely se po aktualizaci jednou ověří (bez stahování).
- Demucs se už nestahuje přes torch.hub (ten ověřoval jen 8 znaků součtu) a načte se až po ověření;
  transformers / huggingface_hub běží offline – na síť nesmí samy.
- FFmpeg a ffprobe čtou vstupní video jen jako místní soubor (`-protocol_whitelist file`, absolutní cesta) –
  podvržený soubor, který je ve skutečnosti playlist s adresami, nic nestáhne; název začínající „-“ se
  nevyloží jako přepínač. mpv nenačítá konfiguraci ani skripty z profilu, nepoužívá youtube-dl.
  Průzkumník („Otevřít složku“) se volá se seznamem argumentů. Ověřeno na názvech s mezerami, apostrofem,
  „uvozovkami“, diakritikou, `&`, `%`, závorkami.
- **Opraveno escapování titulků v ASS:** text „\N“ v titulku dřív zalomil řádek a složené závorky se měnily
  na kulaté – teď se obojí vykreslí doslova. SRT/VTT: prázdný řádek v textu neukončí titulek, VTT escapuje
  `<`, `>`, `&` (a tím i `-->`).
- Poškozené soubory nastavení (styl, presety, rozvržení, volby exportu) aplikaci neshodí – použije se výchozí.
- `requirements.txt`: připnuté přesné verze všech 66 balíčků včetně nepřímých závislostí.
- Nový `SECURITY.md` (jak nahlásit bezpečnostní problém), `.gitignore` (videa, sestavení, .venv, nastavení),
  v README poznámka o názvu a logu a o oficiálním zdroji.
- **Instalátor bez práv správce** (`PrivilegesRequired=lowest`): instaluje se jen pro aktuálního uživatele do
  `%LOCALAPPDATA%\Programs\KupcakeStudio`. Starou instalaci pro všechny uživatele (do 1.5) nabídne
  odinstalovat (jednou potvrzení správce); nastavení a modely zůstanou.

### Možnosti exportu
- Exportovat (i Ctrl+E) otevře panel „● EXPORT“ uprostřed ztlumené aplikace (stejné ztlumení jako obrazovka
  zpracování). Esc, ✕ nebo klik mimo kartu = Zrušit.
- **Co exportovat:** video s titulky · jen titulky jako soubor (SRT, VTT, ASS) · průhledné titulky
  (MOV ProRes 4444 s alfa kanálem – pro DaVinci Resolve, Premiere, CapCut).
- **Rychlé presety:** Originál · TikTok / Reels / Shorts 1080 × 1920 · YouTube 1920 × 1080 · Vlastní
  (odemkne rozlišení a snímkovou frekvenci). Když poměr stran videa nesedí, panel nabídne přidat okraje,
  nebo ponechat původní poměr.
- **Nastavení:** formát MP4 H.264 / MP4 H.265 / MOV ProRes; rozlišení Originál, 4K, 1080p, 720p (jen nižší
  než zdroj); kvalita Vysoká / Standardní / Malý soubor; snímky Originál, 30, 60; zvuk AAC 192 kb/s nebo
  bez zvuku, volitelně sjednocení hlasitosti na −14 LUFS; rozsah celé video nebo jen smyčka / výběr na ose;
  grafická karta (NVENC), pokud je k dispozici.
- **Soubor:** název (video + `_titulky`) a složka s Procházet…, výchozí je složka zdrojového videa;
  upozornění, když soubor už existuje.
- Dole shrnutí (formát · rozlišení · snímky · délka · odhad velikosti), „Po dokončení otevřít složku“,
  Zrušit a oranžové Exportovat. Po exportu naváže obrazovka s cupcakem a průběhem.
- Aplikace si pamatuje poslední nastavení exportu (`aplikace.ini`, skupina `export`).
- Titulky se do videa vykreslují v rozlišení výstupu, takže jsou ostré i po zmenšení nebo s okraji.

## 1.5.0 – 2026-10-31

### Sestavení a licence
- Do instalátoru přibalena plná znění licencí všech knihoven (PyTorch, transformers, Demucs, uroman,
  faster-whisper, CTranslate2, PySide6/Qt LGPL v3, FFmpeg GPL v3, NVIDIA…) – složka `licenses/`,
  doplňuje je `licenses/prenes_licence.py`. Opravena licence uromanu (MIT s uvedením autora, ne Apache 2.0).
- `requirements.txt` doplněn o `huggingface_hub` (aplikace ho používá přímo při stahování modelů).
- Selftest (`KupcakeStudio.exe --selftest`) navíc ověří obrazovku zpracování s průběhem, přesouvání sekce
  Náhled do 10 poloh, presety, notifikaci po exportu a návrat k výchozímu rozvržení po nečitelném uloženém.
- `styl.json` a `presety.json` se načtou i s BOM (soubor upravený v Poznámkovém bloku se dřív tiše ignoroval).

### Obrazovka zpracování s cupcakem
- Během přepisu (příprava audia, přepis, zarovnání časů) i exportu překryje aplikaci velká obrazovka:
  rozhraní se ztlumí (#080808, 70 %) a uprostřed se cupcake z ikony plní zdola nahoru – nejdřív košíček,
  pak poleva; nevyplněná část je tlumená silueta, hranici náplně tvoří pomalu se vlnící hladina.
- Pod cupcakem procenta (JetBrains Mono), aktuální fáze a odhad zbývajícího času; tlačítko **Zrušit**
  (i Esc) se zeptá na potvrzení. Zrušený přepis nechá video otevřené bez titulků, zrušený export smaže
  rozpracovaný soubor.
- Náplň odpovídá skutečnému průběhu: fáze s vahou (model při prvním použití, audio 5 %, přepis 70 %,
  zarovnání 20 %, dočištění 5 %); přepis podle konce posledního segmentu vůči délce videa, export podle
  času z FFmpeg. Mezi hlášeními se náplň plynule dorovná (60 fps) a nikdy necouvne.
- Při 100 % dopadne oranžová třešnička s odskokem, probliknou modré jiskřičky a překrytí se během
  400 ms rozplyne nad připraveným editorem.
- Průběh se ukazuje i na ikoně v hlavním panelu Windows.
- Oddělení hlasu (Demucs) hlásí průběh po minutách zvuku.

### Časová osa – oranžová pro orientaci
- Přehrávací hlava je oranžová (#FF6A00), čára 2 px s jemnou září; v měřítku má úchyt (štítek se špičkou),
  za který jde chytit a táhnout (kurzor ↔), a vedle něj časový kód na oranžovém štítku s tmavým textem.
- Značky (markery) a úsek smyčky v měřítku jsou oranžové (smyčka poloprůhledně, přes stopy jen nádech).
- Právě přehrávané slovo má pod sebou tenkou oranžovou linku.
- Výběr slov zůstává modrý, barvy skupin i samostatných slov se nemění. Barvy jsou v `theme.py`
  (`OSA_HLAVA`, `OSA_ZNACKA`, `OSA_SMYCKA`, `OSA_PRAVE_HRAJE`).

### Číselná pole
- Šipky nahoru/dolů jsou dobře vidět: ostré oranžové trojúhelníky (SVG, 9 px) na tlačítkách širokých
  19 px, oddělených od hodnoty i od sebe tenkou linkou.
- Najetí myší tlačítko zesvětlí a šipku rozzáří, stisk krátce podbarví oranžovou; na minimu/maximu
  nebo u vypnutého pole je šipka šedá. Držení tlačítka hodnotu plynule mění. Platí v celé aplikaci.

### Opravy
- Při přesunu nebo změně velikosti sekce Náhled zůstávala na starém místě viset kopie tlačítka Přehrát.
  Příčina: plocha videa je nativní okno (kvůli mpv) a Qt kvůli ní dělalo nativními i tlačítko, posuvník
  a čas; nativní okno tlačítka se při přesunu sekce nepřesunulo. Teď je nativní jen plocha videa
  (`Qt.AA_DontCreateNativeWidgetSiblings`) a záře tlačítka se kreslí přímo v něm, bez grafického efektu.
- Celková délka videa pod náhledem se ukáže hned po načtení (dřív až po prvním posunu času).

### Oranžová = „teď“ a „akce“, modrá = výběr a fokus
- Náhled: tlačítko Přehrát/Pauza je oranžové kolečko, pod myší se jemně rozzáří; posuvník má přehranou
  část a úchyt oranžové, zbytek tlumeně šedý; aktuální čas je oranžově (JetBrains Mono), délka šedě.
- Titulky: právě přehrávaný titulek má vlevo oranžový proužek 3 px a oranžové časy, seznam se k němu
  při přehrávání posouvá. Překrývají-li se časy dvou titulků, ukáže se u nich oranžová ikonka
  upozornění s popiskem. Označený řádek zůstává modrý.
- Nastavení: nové **presety stylu** – výběr nahoře v sekci, oranžové „Uložit preset“ a smazání (✕);
  vestavěný preset „Výchozí“ nejde přepsat ani smazat. Preset mění vzhled, časování (posun, předstih)
  zůstává z videa. Liší-li se skupina (Text, Obrys a stín, Pozadí, Pozice, Efekty) od presetu, svítí v jejím
  záhlaví oranžová tečka – klik na ni skupinu po potvrzení vrátí. Presety jsou v `presety.json` v nastavení.
- Časová osa: přichytávání má ikonu magnetu – oranžová = zapnuto, šedá = vypnuto (místo modrého
  podbarvení); zamčené titulky mají u prvního slova malý oranžový zámek.
- Sekce, ve které právě pracuješ (poslední kliknutí), má pod záhlavím oranžovou linku 2 px, ostatní neutrální.
- Tečka u loga je během zpracování (přepis, export, zarovnání) oranžová a jemně pulzuje, jinak modrá.
- Po exportu se místo dialogu ukáže v pravém dolním rohu notifikace „Export dokončen“ s oranžovým
  proužkem a tlačítkem „Otevřít složku“ (otevře Průzkumníka s označeným videem); po 6 s sama zmizí,
  pod myší počká.
- Všechny barvy včetně světlejší oranžové a poloprůhledných variant jsou v `theme.py`. Kontrast:
  tmavý text na oranžové 7,0 : 1, oranžový text na pozadí 7,0 : 1, na panelu 6,5 : 1, na modrém výběru 5,5 : 1.

## 1.4.0 – 2026-10-31

### Přesné časování slov
- **Zarovnání ke zvuku (forced alignment):** po přepisu se každé slovo zarovná ke zvuku akustickým
  modelem wav2vec2 (stejný postup jako WhisperX). Čeština, slovenština, angličtina, němčina,
  španělština, francouzština, italština a polština mají vlastní model, ostatní jazyky vícejazyčný MMS.
  Běží na GPU (PyTorch s CUDA). Model se stáhne při prvním použití (asi 1,2 GB).
- Začátek slova se dorovná k nástupu zvuku (až o 60 ms dřív, jen u výrazného náběhu).
- Slova se nepřekrývají, mezi nimi je mezera aspoň 20 ms a každé je vidět aspoň 0,12 s. Když to rychlá
  řeč nedovolí, zvýraznění ukáže slova po dvou, aby neproblikávala.
- Lepší přepis: Whisper s beam 5, bez navazování na předchozí text (méně „rozjíždění“ a halucinací),
  s VAD; zvuk mono 16 kHz s normalizovanou hlasitostí. Videa, jejichž zvuková stopa začíná později
  než obraz, se srovnají podle `start_time`.
- V dialogu jazyka řeči: **Přesné časování (pomalejší)** (výchozí zapnuto) a **Oddělit hlas od hudby
  (Demucs)** pro videa s hudbou v pozadí. Volba se pamatuje.

### Nástroje
- **Nastavení → Časování:** *Posun titulků* (± ms – opraví zpoždění všech titulků najednou)
  a *Předstih slova* (výchozí 40 ms – slovo se ukáže o chvilku dřív, než zazní).
- **Znovu zarovnat výběr** (Ctrl+Shift+A, lišta časové osy, kontextové menu slova): po ruční opravě
  textu znovu zarovná jen označená slova; jde vrátit (Ctrl+Z).

### Výsledek měření (odchylka začátků slov od nástupu zvuku)
- krátké video (9 s): 67 → 15 ms · rozhovor: 59 → 39 ms · 3 min přednášky: 102 → 81 ms ·
  řeč s hlasitou hudbou: 65 → 19 ms, s Demucsem 14 ms.

## 1.3.0 – 2026-10-30

### Nový název: kupcake.studio
- Aplikace se jmenuje **kupcake.studio** (dříve tkStudio, ještě dříve Spellcast): okno, dialogy,
  O aplikaci, menu, kontextová nabídka „Otevřít v kupcake.studio“. Soubory a složky používají
  technický název `KupcakeStudio`: `KupcakeStudio.exe`, `KupcakeStudio-Setup-<verze>.exe`,
  AppUserModelID `iamtomkup.kupcakestudio`.
- Nastavení, presety, rozvržení a stažený model se při prvním spuštění samy přesunou ze složek
  `tkStudio` i `Spellcast` (podle toho, která existuje) do `%APPDATA%\KupcakeStudio`
  a `%LOCALAPPDATA%\KupcakeStudio`.
- Instalátor (stejné AppId) nahradí nainstalované tkStudio i Spellcast: program přesune do
  `C:\Program Files\KupcakeStudio`, odstraní starou složku, zástupce a položky v kontextové nabídce
  a vytvoří nové.

### Cupcake
- Nová ikona: kreslený cupcake – modrá poleva, oranžová třešnička, tři svislé proužky na košíčku;
  u 16 a 24 px zjednodušená silueta s třešničkou.
- Logo v záhlaví „• kupcake.studio“ s malým cupcakem.
- Animovaný cupcake (třešnička poskakuje, kolem probliknou modré jiskřičky) během přepisu a exportu,
  v prázdném náhledu a v okně O aplikaci (to je teď vlastní dialog s odkazem na tomkup.cz).

## 1.2.0 – 2026-10-30

### Nový název: tkStudio
- Aplikace se jmenuje **tkStudio** (dříve Spellcast): titulek okna, dialogy, O aplikaci, menu,
  `tkStudio.exe`, instalátor `tkStudio-Setup-<verze>.exe`, AppUserModelID `iamtomkup.tkstudio`.
- Nastavení, presety, rozvržení a stažený model se při prvním spuštění samy přesunou ze složek
  `%APPDATA%\Spellcast` a `%LOCALAPPDATA%\Spellcast` do `…\tkStudio`.
- Instalátor (stejné AppId) nahradí nainstalovaný Spellcast: program přesune do
  `C:\Program Files\tkStudio`, starou složku, zástupce a položku „Otevřít ve Spellcast“ odstraní
  a vytvoří nové („Otevřít v tkStudio“).
- Nová ikona: monogram tk v teplé bílé s modrou tečkou na téměř černém čtverci.

### Vzhled v barvách značky iamtom.kup
- Téměř černé pozadí `#080808`, panely `#111214`, teplá bílá `#F2EFEA`.
- Modrá `#00B4FF` místo tyrkysové: přehrávací hlava, výběr, aktivní pole, záložky, přepínače,
  posuvníky, linka pod záhlavím. Záře zůstala jen u přehrávací hlavy a výběru.
- Oranžová `#FF6A00` jen pro hlavní akce (Exportovat video, Přepsat) a tečku u probíhajícího
  zpracování.
- Logo „• tkStudio“ v záhlaví okna, hlavní tlačítka jako „pilulky“, záhlaví panelů v technickém
  stylu („● NÁHLED“ – JetBrains Mono, velká písmena).
- Úvodní plocha před nahráním videa: tmavý přechod s pár hvězdičkami a „CREATIVE AI · VIDEO ·
  SUBTITLES“.
- O aplikaci: logo, verze, „vytvořil Tomáš Kupec · iamtom.kup“ a odkaz na tomkup.cz.
- Časová osa: tlumená paleta skupin (šalvějová, švestková, vínová, olivová, břidlicová),
  samostatná slova `#2A2E35`; smyčka a značky v tlumené pískové místo fialové.

### Opravy
- Po výběru jazyka řeči se mohly zacyklit filtry událostí (kolečko myši, animace tlačítek), když
  Python zrovna uklízel paměť – typ prvku se teď zjišťuje čistě v Qt (`QObject.inherits`).

## 1.1.1 – 2026-10-30

- Kolečko myši už nemění hodnoty číselných polí, rozbalovacích seznamů a posuvníků jen při najetí
  kurzorem. Hodnotu mění až v aktivním poli (po kliknutí do něj, s tyrkysovým obrysem); jinak
  posouvá panel Nastavení. Klik mimo pole nebo Esc pole deaktivuje. Platí v celé aplikaci.
- Aktivní posuvník (Pozice) má tyrkysový obrys úchytu.

## 1.1.0 – 2026-10-30

### Rozhraní
- **Volně přesouvatelné sekce** (Titulky, Náhled, Nastavení, Časová osa) jako v DaVinci Resolve /
  Visual Studiu: přetažení za záhlaví vlevo/vpravo/nahoru/dolů s tyrkysovým náhledem místa,
  vložení jako záložka, odpojení do samostatného okna (i na druhý monitor), změna velikosti úchyty.
- Dvojklik na záhlaví sekce ji roztáhne přes celé okno, další dvojklik vrátí rozvržení.
- Menu **Zobrazení**: zapínání/vypínání sekcí, **Uložená rozvržení** (pojmenovaná, např. „Časování“,
  „Styl“), **Zamknout rozvržení**, **Obnovit výchozí rozvržení**. Rozvržení včetně samostatných oken
  se pamatuje mezi spuštěními.
- Klávesové zkratky fungují i v odpojených oknech sekcí.
- Nový vzhled „tech“: tmavá paleta, neonový tyrkysový akcent jen pro zvýraznění, písma Inter
  a JetBrains Mono, plynulé animace tlačítek, záře u přehrávací hlavy, výběru a tlačítka Export.
- Sbalovací skupiny v panelu Nastavení, tenký ukazatel průběhu.

### Jazyky
- Rozhraní v češtině, angličtině, němčině, španělštině a slovenštině (**Nastavení → Jazyk**),
  přepnutí bez restartu; poprvé podle jazyka Windows.
- Volba **jazyka řeči** po otevření videa (automatické rozpoznání nebo jeden ze 100 jazyků Whisperu),
  poslední volba se pamatuje.

### Časová osa
- Seskupení / rozdělení skupiny (Ctrl+G, Ctrl+Shift+G), rozdělení u slova, rozříznutí na přehrávací
  hlavě (Ctrl+B), mazání s posunem i bez (Delete, Shift+Delete), kopírovat/vyjmout/vložit, vložení
  nového slova, spojení slov (Ctrl+J), úprava textu přímo na ose.
- Přehrávání J / K / L, krokování po snímku a po sekundě, Home/End, ↑↓ mezi titulky, smyčka
  (Shift+tažení na měřítku, Ctrl+L), přehrát výběr (Shift+Mezerník), přiblížení na výběr (Z),
  sledování přehrávací hlavy, časový kód HH:MM:SS:FF, vyšší stopa.
- Přichytávání (N) se zobrazenou čárou, značky (M), zamčení titulku, kontextové menu, panel nástrojů
  nad osou, okno se všemi zkratkami (F1). Vše jde vrátit (Ctrl+Z).
- Samostatná slova mají neutrální barvu, skupiny barevné.

### Ostatní
- Oprava: seskupování slov na časové ose.
- Při aktualizaci z 1.0 se staré rozložení panelů nahradí výchozím rozvržením sekcí; nečitelné
  nebo poškozené uložené rozvržení aplikaci nezastaví. Styl titulků i jazyk zůstávají.
- Instalátor při aktualizaci nejdřív odstraní knihovny staré verze.
- Přibaleny licence třetích stran (`THIRD_PARTY_LICENSES.md`, složka `licenses`).

## 1.0.0 – 2026-10-29

- První verze: přepis řeči faster-whisper large-v3 na GPU s časy slov, editor titulků, panel stylu
  s živým náhledem, přehrávač mpv, časová osa po slovech, vypálení titulků do videa přes FFmpeg
  (NVENC), instalátor.
