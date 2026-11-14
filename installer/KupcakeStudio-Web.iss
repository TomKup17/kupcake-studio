; kupcake.studio – Copyright (C) 2026 Tomáš Kupec
; SPDX-License-Identifier: GPL-3.0-only
; Malý stahovací instalátor kupcake.studio (Inno Setup 6.5+): jeden soubor KupcakeStudio-Setup.exe o pár MB.
; Kompiluje ho build.bat po plném instalátoru (KupcakeStudio.iss):
;   python nastroje\web_instalator.py <verze>     -> build\web_casti.iss, build\web_modely.iss
;   ISCC /DAppVersion=<verze> installer\KupcakeStudio-Web.iss  ->  dist\KupcakeStudio-Setup.exe
; Soubor musí zůstat v UTF-8 s BOM (kvůli češtině).
;
; Co dělá:
;  1. ukáže podmínky použití a volby (zástupci, AI modely ke stažení),
;  2. stáhne z GitHub Releases části plného instalátoru (.exe, -1.bin, -2.bin) do dočasné složky a ověří SHA-256,
;  3. spustí plný instalátor bez průvodce (/SILENT) s vybranými volbami – aplikace se nainstaluje přesně jako z něj,
;  4. stáhne vybrané AI modely z huggingface.co (Demucs z dl.fbaipublicfiles.com) tam, kde je aplikace hledá;
;     každý soubor ověří proti SHA-256 z manifest_modelu.py. Aplikace je při prvním použití ještě jednou ověří.
; Sám nic neregistruje ani neodinstalovává (Uninstallable=no) – aplikaci spravuje plný instalátor.
;
; Test bez GitHubu (soubory z místního serveru, jiný název aplikace a složka dat):
;   ISCC /DAppVersion=… /DZakladUrl=http://127.0.0.1:8124/ /DTechName=… /DDataDir=… installer\KupcakeStudio-Web.iss

#ifndef AppVersion
  #error Verzi předává build.bat (/DAppVersion=…) z version.py – spusť build.bat.
#endif
#ifndef AppVersionNum
  #define AppVersionNum AppVersion
#endif
#ifndef AppName
  #define AppName "kupcake.studio"
#endif
#ifndef TechName
  #define TechName "KupcakeStudio"
#endif
#define AppPublisher "iamtom.kup"
#define AppExe TechName + ".exe"
; odkud se stahují části plného instalátoru – konkrétní vydání (pre-release nenajde odkaz /releases/latest)
#ifndef ZakladUrl
  #define ZakladUrl "https://github.com/TomKup17/kupcake-studio/releases/download/v" + AppVersion + "/"
#endif
; složka dat aplikace (cesty.py: %LOCALAPPDATA%\KupcakeStudio) – modely do \models
#ifndef DataDir
  #define DataDir "{localappdata}\" + TechName
#endif
; plný instalátor (stejný název jako u vydání); přepsatelné pro test
#ifndef PlnySetup
  #define PlnySetup TechName + "-Setup-" + AppVersion + ".exe"
#endif

#include "..\build\web_casti.iss"

[Setup]
; vlastní AppId – stahovač se neregistruje (Uninstallable=no), aplikace má AppId plného instalátoru
AppId={#TechName}-Stahovac
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://tomkup.cz
CreateAppDir=no
Uninstallable=no
DisableProgramGroupPage=yes
DisableReadyPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
; bez čísla verze – po vydání stabilní verze na něj může vést trvalý odkaz …/releases/latest/download/KupcakeStudio-Setup.exe
OutputBaseFilename={#TechName}-Setup
SetupIconFile=..\kupcake.ico
LicenseFile=PODMINKY.txt
VersionInfoVersion={#AppVersionNum}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} – instalátor (stahuje z internetu)
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersionNum}
WizardStyle=modern
; běžící aplikace by plný instalátor bez průvodce zastavila – zeptat se hned na začátku
AppMutex=KupcakeStudioBeziMutex,tkStudioBeziMutex,SpellcastBeziMutex
CloseApplications=no
SetupLogging=yes
Compression=lzma2/max
SolidCompression=yes

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
czech.SkupinaModely=AI modely – stáhnout hned, jinak se stáhnou až v aplikaci (vždy s dotazem):
czech.SkupinaCasovani=Přesné časování slov podle jazyka tvých videí:
czech.SkupinaHlas=Volitelné:
czech.SkupinaZastupci=Zástupci a integrace do Windows:
czech.StahujiNadpis=Stahuje se kupcake.studio
czech.StahujiPopis=Instalátor stahuje aplikaci (asi %1) z GitHubu. Podle rychlosti internetu to může trvat i desítky minut.
czech.InstalujiPopis=Instaluje se kupcake.studio. Chvíli to potrvá.
czech.MaloMista=Na disku %1 je volných %2, instalace potřebuje asi %3 (stažené soubory, aplikace a vybrané modely).%n%nUvolni místo nebo zruš výběr některých modelů a zkus to znovu.
czech.ChybaInstalace=Instalace aplikace se nezdařila (kód %1).%n%nZkus instalaci spustit znovu. Pokud to nepomůže, stáhni z GitHub Releases plný instalátor (.exe a všechny .bin do jedné složky).
czech.ChybaSpusteni=Instalátor aplikace se nepodařilo spustit:%n%1
czech.PamStahne=Stáhne se z internetu:
czech.PamAplikace=aplikace kupcake.studio %1 – %2 z github.com
czech.PamModely=vybrané AI modely – %1 z huggingface.co
czech.PamDemucs=model Demucs – %1 z dl.fbaipublicfiles.com
czech.PamNic=AI modely se stáhnou až v aplikaci, po tvém souhlasu.
czech.PamUzStazene=vybrané AI modely už v počítači máš – znovu se stahovat nebudou.
czech.SpustitAplikaci=Spustit kupcake.studio

[Tasks]
; stejné názvy jako v plném instalátoru – předávají se mu (/TASKS=…)
Name: "desktopicon"; Description: "Vytvořit zástupce na ploše"; GroupDescription: "{cm:SkupinaZastupci}"; Flags: unchecked
Name: "kontextmenu"; Description: "Přidat k videím do nabídky pravého tlačítka položku „Otevřít v kupcake.studio“"; GroupDescription: "{cm:SkupinaZastupci}"; Flags: unchecked

; volby a soubory AI modelů (vygenerované z manifest_modelu.py)
#include "..\build\web_modely.iss"

[Run]
Filename: "{autopf}\{#TechName}\{#AppExe}"; Description: "{cm:SpustitAplikaci}"; Flags: nowait postinstall skipifsilent; Check: AplikaceNainstalovana

[Code]
var
  Stahovani: TDownloadWizardPage;
  JazykVybran: Boolean;

// Soubor modelu chybí nebo nemá správnou velikost → stáhnout (už stažený model se znovu nestahuje).
function ChybiSoubor(Cesta, Velikost: String): Boolean;
var
  Skutecna: Int64;
begin
  Result := not (FileSize64(ExpandConstant(Cesta), Skutecna) and (Skutecna = StrToInt64(Velikost)));
end;

function AplikaceNainstalovana(): Boolean;
begin
  Result := FileExists(ExpandConstant('{autopf}\{#TechName}\{#AppExe}'));
end;

// Volby zadané při spuštění (/TASKS=…, /MERGETASKS=…) mají přednost před předvýběrem.
function UlohyZPrikazu(): Boolean;
var
  i: Integer;
begin
  Result := False;
  for i := 1 to ParamCount do
    if (Pos('/TASKS=', Uppercase(ParamStr(i))) = 1) or (Pos('/MERGETASKS=', Uppercase(ParamStr(i))) = 1) then
      Result := True;
end;

// Přesné časování: předvybrat jazyk podle jazyka Windows (jen poprvé, pak platí volba uživatele).
procedure CurPageChanged(CurPageID: Integer);
var
  Jazyk: Integer;
begin
  if (CurPageID = wpSelectTasks) and not JazykVybran then
  begin
    JazykVybran := True;
    if WizardSilent() or UlohyZPrikazu() then
      Exit;
    Jazyk := GetUILanguage() and $3FF;
    case Jazyk of
      $05: WizardSelectTasks('cas_cs');
      $1B: WizardSelectTasks('cas_sk');
      $09: WizardSelectTasks('cas_en');
      $07: WizardSelectTasks('cas_de');
      $0A: WizardSelectTasks('cas_es');
      $0C: WizardSelectTasks('cas_fr');
      $10: WizardSelectTasks('cas_it');
      $15: WizardSelectTasks('cas_pl');
    end;
  end;
end;

// Velikost vybraných modelů, které se opravdu budou stahovat (WizardIsTaskSelected + ChybiSoubor).
function VelikostModelu(Demucs: Boolean): Int64;
var
  Seznam: TStringList;
  i: Integer;
  Uloha, Cesta, Velikost: String;
begin
  Result := 0;
  Seznam := TStringList.Create;
  try
    PridejModely(Seznam);
    for i := 0 to Seznam.Count - 1 do
    begin
      // položka: úloha|cesta|velikost
      Uloha := Copy(Seznam[i], 1, Pos('|', Seznam[i]) - 1);
      Cesta := Copy(Seznam[i], Pos('|', Seznam[i]) + 1, MaxInt);
      Velikost := Copy(Cesta, Pos('|', Cesta) + 1, MaxInt);
      Cesta := Copy(Cesta, 1, Pos('|', Cesta) - 1);
      if ((Uloha = 'demucs') = Demucs) and WizardIsTaskSelected(Uloha) and ChybiSoubor(Cesta, Velikost) then
        Result := Result + StrToInt64(Velikost);
    end;
  finally
    Seznam.Free;
  end;
end;

// Velikost jako ji ukazují Windows (1 GB = 1024³ B), s desetinnou čárkou.
function VGB(Bajty: Int64): String;
begin
  if Bajty >= 1073741824 then
  begin
    Result := Format('%.1f GB', [Bajty / 1073741824.0]);
    StringChangeEx(Result, '.', ',', True);
  end
  else
    Result := Format('%d MB', [Round(Bajty / 1048576.0)]);
end;

procedure InitializeWizard();
begin
  Stahovani := CreateDownloadPage(CustomMessage('StahujiNadpis'),
    FmtMessage(CustomMessage('StahujiPopis'), [VGB(StrToInt64('{#VelikostCastiCelkem}'))]), nil);
  Stahovani.ShowBaseNameInsteadOfUrl := True;
end;

// Je zaškrtnutý aspoň jeden model? (i když už je stažený a stahovat se nebude)
function VybranyModel(): Boolean;
var
  Seznam: TStringList;
  i: Integer;
begin
  Result := False;
  Seznam := TStringList.Create;
  try
    PridejModely(Seznam);
    for i := 0 to Seznam.Count - 1 do
      if WizardIsTaskSelected(Copy(Seznam[i], 1, Pos('|', Seznam[i]) - 1)) then
        Result := True;
  finally
    Seznam.Free;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo,
  MemoGroupInfo, MemoTasksInfo: String): String;
var
  Modely, Demucs: Int64;
begin
  Modely := VelikostModelu(False);
  Demucs := VelikostModelu(True);
  Result := CustomMessage('PamStahne') + NewLine +
    Space + FmtMessage(CustomMessage('PamAplikace'), ['{#AppVersion}', VGB(StrToInt64('{#VelikostCastiCelkem}'))]) + NewLine;
  if Modely > 0 then
    Result := Result + Space + FmtMessage(CustomMessage('PamModely'), [VGB(Modely)]) + NewLine;
  if Demucs > 0 then
    Result := Result + Space + FmtMessage(CustomMessage('PamDemucs'), [VGB(Demucs)]) + NewLine;
  if (Modely + Demucs = 0) and VybranyModel() then
    Result := Result + Space + CustomMessage('PamUzStazene') + NewLine
  else if Modely + Demucs = 0 then
    Result := Result + Space + CustomMessage('PamNic') + NewLine;
  if MemoTasksInfo <> '' then
    Result := Result + NewLine + MemoTasksInfo;
end;

// Místo na disku: stažené části (v dočasné složce) + aplikace + modely. Většinou jde o stejný disk.
function DostMista(): Boolean;
var
  Volno, Celkem, Potreba: Int64;
  Disk: String;
begin
  Disk := ExtractFileDrive(ExpandConstant('{autopf}'));
  Potreba := StrToInt64('{#VelikostCastiCelkem}') + StrToInt64('{#VelikostAplikace}') +
    VelikostModelu(False) + VelikostModelu(True) + 500000000;
  Result := True;
  if GetSpaceOnDisk64(Disk, Volno, Celkem) and (Volno < Potreba) then
  begin
    SuppressibleMsgBox(FmtMessage(CustomMessage('MaloMista'), [Disk, VGB(Volno), VGB(Potreba)]),
      mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

// Po stisku Instalovat: stáhnout a ověřit části plného instalátoru (se zrušením a srozumitelnou chybou).
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Chyba: String;
begin
  Result := True;
  if CurPageID <> wpReady then
    Exit;
  if not DostMista() then
  begin
    Result := False;
    Exit;
  end;
  Stahovani.Clear;
  PridejCasti(Stahovani);
  Stahovani.Show;
  try
    try
      Stahovani.Download;
    except
      if Stahovani.AbortedByUser then
        Log('Stahování zrušil uživatel.')
      else
      begin
        Chyba := Format('%s: %s', [Stahovani.LastBaseNameOrUrl, GetExceptionMessage]);
        SuppressibleMsgBox(AddPeriod(Chyba), mbCriticalError, MB_OK, IDOK);
      end;
      Result := False;
    end;
  finally
    Stahovani.Hide;
  end;
end;

function VybraneUlohy(): String;
begin
  Result := '';
  if WizardIsTaskSelected('desktopicon') then
    Result := 'desktopicon';
  if WizardIsTaskSelected('kontextmenu') then
  begin
    if Result <> '' then
      Result := Result + ',';
    Result := Result + 'kontextmenu';
  end;
end;

// Plný instalátor bez průvodce. Když selže, stahovač skončí s chybou (modely se pak nestahují).
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Kod: Integer;
  Parametry: String;
begin
  Result := '';
  WizardForm.PreparingLabel.Caption := CustomMessage('InstalujiPopis');
  Parametry := '/SILENT /SUPPRESSMSGBOXES /NORESTART /SP- /NOCANCEL /TASKS="' + VybraneUlohy() + '"';
  Log('Spouštím plný instalátor: ' + Parametry);
  if not Exec(ExpandConstant('{tmp}\{#PlnySetup}'), Parametry, ExpandConstant('{tmp}'), SW_SHOW,
              ewWaitUntilTerminated, Kod) then
    Result := FmtMessage(CustomMessage('ChybaSpusteni'), [SysErrorMessage(Kod)])
  else if Kod <> 0 then
    Result := FmtMessage(CustomMessage('ChybaInstalace'), [IntToStr(Kod)])
  else if not AplikaceNainstalovana() then
    Result := FmtMessage(CustomMessage('ChybaInstalace'), ['-']);
end;
