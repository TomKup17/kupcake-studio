# Bezpečnost

## Jak nahlásit bezpečnostní problém

Našel jsi v kupcake.studio bezpečnostní chybu (např. spuštění cizího kódu, podvržený model, únik
souborů, problém v instalátoru)? **Nehlas ji veřejně** (ne v Issues, diskuzích ani na sociálních sítích),
ať ji nikdo nezneužije dřív, než bude opravená.

1. Pošli hlášení soukromě:
   - na GitHubu v repozitáři **Security → Report a vulnerability** (soukromé hlášení), nebo
   - přes kontakt na webu autora **https://tomkup.cz**.
2. Napiš:
   - verzi aplikace (Nápověda → O aplikaci) a verzi Windows,
   - co se stane a jak to zopakovat (kroky, případně ukázkový soubor),
   - jaký dopad to podle tebe má.
3. Do 7 dnů dostaneš odpověď s dalším postupem. Opravu vydám co nejdřív jako novou verzi a po vydání
   tě (pokud budeš chtít) uvedu v seznamu změn.

Prosím netestuj problém na cizích počítačích ani datech a nestahuj nic, k čemu nemáš oprávnění.

## Podporované verze

Opravy dostává jen **poslední vydaná verze**. Oficiální instalátor je ke stažení jen z tohoto repozitáře
(Releases) – verze z jiných zdrojů mohou být upravené.

## Co aplikace dělá pro bezpečnost

- Modely (Whisper, zarovnání slov, Demucs) se stahují **jen se souhlasem uživatele**, jen přes HTTPS
  z oficiálních zdrojů (huggingface.co, dl.fbaipublicfiles.com), v pevné revizi a s kontrolou **SHA-256**
  každého souboru (`manifest_modelu.py`, `stahovani.py`). Soubor, který nesedí, se smaže; soubor jiné velikosti
  se odmítne už podle hlavičky serveru. Přesměrování smí vést jen na HTTPS a jen na huggingface.co / `*.hf.co`
  / dl.fbaipublicfiles.com – IP adresy, localhost, jiné porty a cizí domény se odmítnou před připojením;
  certifikát serveru se ověřuje. Ověřené soubory nesou ve značce `.hotovo` otisk (velikost + čas změny);
  změněný soubor se před použitím znovu ověří.
- Knihovny Hugging Face jsou vynuceně offline a bez telemetrie (`cesty.py`); samy nikdy nic nestahují.
- Model Demucs (formát pickle) se načítá výhradně omezeným unpicklerem PyTorch (`weights_only=True`) s několika
  povolenými datovými typy (HTDemucs, Fraction, numpy float64 – přesně to, co oficiální soubor obsahuje) a vždy
  až po ověření SHA-256 (`hlas.py`). Modely wav2vec2 jsou safetensors,
  nebo je transformers načítá rovněž s `weights_only=True`. Whisper (CTranslate2) není pickle.
- Kontrola nové verze jen čte seznam vydání z api.github.com; aplikace **nikdy nestahuje ani nespouští
  instalátor** – tlačítko Stáhnout otevře stránku vydání v prohlížeči, a jen na github.com v repozitáři aplikace.
- FFmpeg a mpv dostávají argumenty jako seznam (nikdy přes shell) a smí číst jen místní soubory –
  video, které je ve skutečnosti playlist s adresami na internet, nic nestáhne. Export nikdy nepřepíše
  zdrojové video.
- mpv nenačítá konfiguraci ani skripty z profilu uživatele a nepoužívá youtube-dl.
- Projekty `.kupcake` a nastavení jsou JSON / INI (nikdy pickle); každá hodnota se při načtení kontroluje
  na typ, poškozený projekt skončí srozumitelnou hláškou, ukládá se atomicky (dočasný soubor + přejmenování).
- Text titulků se do ASS/SRT/VTT escapuje tak, aby se nedal vykonat jako příkaz formátu.
- Instalátor nepotřebuje práva správce (instaluje se jen pro aktuálního uživatele). Zatím není digitálně
  podepsaný – ověř SHA-256 ze souboru `.sha256` u vydání (pro `.exe` i všechny části `.bin`).
- Hlášení chyby neobsahuje uživatelské jméno (cesty do profilu se nahrazují `%LOCALAPPDATA%`).

Bezpečnostní testy: `tests/` (`python -m unittest discover -s tests`). Poslední audit kódu s nálezy a stavem:
[docs/BEZPECNOSTNI_AUDIT.md](docs/BEZPECNOSTNI_AUDIT.md).
