; Instalátor kupcake.studio (Inno Setup 6). Kompiluje ho build.bat s verzí z version.py:
;   ISCC /DAppVersion=1.3.0 installer\KupcakeStudio.iss  ->  dist\KupcakeStudio-Setup-1.3.0.exe
; Soubor musí zůstat v UTF-8 s BOM (kvůli češtině).
;
; Bez práv správce: instaluje se jen pro aktuálního uživatele do %LOCALAPPDATA%\Programs\KupcakeStudio
; (PrivilegesRequired=lowest), zástupci a kontextová nabídka v jeho profilu (HKCU).
;
; Aktualizace: AppId je pevné, takže nová verze nahradí starou (jeden záznam v Nastavení → Aplikace).
; Verze do 1.5 (i pod názvy Spellcast a tkStudio) se instalovaly pro všechny uživatele do Program Files –
; takovou instalaci instalátor bez práv správce smazat nemůže, proto nabídne spustit její odinstalátor
; (Windows se zeptá na potvrzení správce). Nastavení (%APPDATA%\KupcakeStudio) a modely
; (%LOCALAPPDATA%\KupcakeStudio) leží mimo složku programu a zůstanou.

#ifndef AppVersion
  #error Verzi předává build.bat (/DAppVersion=…) z version.py – spusť build.bat.
#endif
; číselná verze pro údaje o souboru (1.0.0 z 1.0.0-beta.1); build.bat ji předává zvlášť
#ifndef AppVersionNum
  #define AppVersionNum AppVersion
#endif
; názvy a AppId jdou pro test instalátoru přepsat (/DTechName=… /DAppIdGuid=… /DZdroj=…), jinak tyto:
#define AppName "kupcake.studio"
#ifndef TechName
  #define TechName "KupcakeStudio"
#endif
#define AppPublisher "iamtom.kup"
#define AppExe TechName + ".exe"
#define AppUserModelID "iamtomkup.kupcakestudio"
#define MenuText "Otevřít v kupcake.studio"
#ifndef AppIdGuid
  #define AppIdGuid "{8E1F3C52-6A4D-4B8E-9C7A-3D2E5F1A7B90}"
#endif
#ifndef Zdroj
  #define Zdroj "..\dist\" + TechName
#endif
; velikost jedné části instalátoru – GitHub Releases bere soubory nejvýš do 2 GiB (2 147 483 648 B);
; „max“ = 2 100 000 000 B, s rezervou pod limitem. Pro test lze zmenšit (/DVelikostCasti=1000000).
#ifndef VelikostCasti
  #define VelikostCasti "max"
#endif

[Setup]
; AppId nikdy neměnit – podle něj Windows pozná aktualizaci téže aplikace (i ze Spellcastu a tkStudio)
AppId={{#AppIdGuid}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://tomkup.cz
; {autopf} je při instalaci bez práv správce %LOCALAPPDATA%\Programs
DefaultDirName={autopf}\{#TechName}
UsePreviousAppDir=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename={#TechName}-Setup-{#AppVersion}
SetupIconFile=..\kupcake.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersionNum}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} – instalátor
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersionNum}
WizardStyle=modern
; aplikace drží tento mutex, dokud běží – instalace i odinstalace ji nejdřív požádá o zavření
; (další dva jsou mutexy tkStudio a Spellcastu, ať aktualizace pozná i běžící starou verzi)
AppMutex=KupcakeStudioBeziMutex,tkStudioBeziMutex,SpellcastBeziMutex
CloseApplications=yes
ChangesAssociations=yes
Compression=lzma2/normal
SolidCompression=yes
; instalátor má přes 3 GB – data se rozdělí do částí KupcakeStudio-Setup-<verze>-1.bin, -2.bin…, které
; musí ležet ve stejné složce jako Setup.exe (sám Setup.exe má jen pár MB)
DiskSpanning=yes
DiskSliceSize={#VelikostCasti}
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=8

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[Tasks]
Name: "desktopicon"; Description: "Vytvořit zástupce na ploše"; GroupDescription: "Zástupci:"; Flags: unchecked
Name: "kontextmenu"; Description: "Přidat k videím do nabídky pravého tlačítka položku „{#MenuText}“"; GroupDescription: "Integrace do Windows:"; Flags: unchecked

[InstallDelete]
; před aktualizací smazat knihovny staré verze, ať se nemíchají s novými (nastavení a model jsou jinde)
Type: filesandordirs; Name: "{app}\_internal"
; zástupci dřívějších názvů – nahradí je zástupci kupcake.studio (ze [Icons])
Type: files; Name: "{autodesktop}\tkStudio.lnk"
Type: files; Name: "{autoprograms}\tkStudio.lnk"
Type: files; Name: "{userdesktop}\tkStudio.lnk"
Type: files; Name: "{autodesktop}\Spellcast.lnk"
Type: files; Name: "{autoprograms}\Spellcast.lnk"
Type: files; Name: "{userdesktop}\Spellcast.lnk"

[Files]
Source: "{#Zdroj}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Comment: "Automatické titulky z videa"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Registry]
; „Otevřít v kupcake.studio“ pro video soubory (ve Windows 11 pod „Zobrazit další možnosti“)
#define VideoMenu(Ext) \
  'Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\' + Ext + '\shell\' + TechName + '"; ValueType: string; ValueName: ""; ValueData: "' + MenuText + '"; Flags: uninsdeletekey; Tasks: kontextmenu' + NewLine + \
  'Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\' + Ext + '\shell\' + TechName + '"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\' + AppExe + '"",0"; Tasks: kontextmenu' + NewLine + \
  'Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\' + Ext + '\shell\' + TechName + '\command"; ValueType: string; ValueName: ""; ValueData: """{app}\' + AppExe + '"" ""%1"""; Tasks: kontextmenu' + NewLine
#emit VideoMenu(".mp4")
#emit VideoMenu(".mov")
#emit VideoMenu(".mkv")
#emit VideoMenu(".avi")
#emit VideoMenu(".webm")
#emit VideoMenu(".m4v")
#emit VideoMenu(".mts")
; projekty .kupcake se otevřou dvojklikem v kupcake.studio
Root: HKA; Subkey: "Software\Classes\.kupcake"; ValueType: string; ValueName: ""; ValueData: "{#TechName}.Projekt"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#TechName}.Projekt"; ValueType: string; ValueName: ""; ValueData: "Projekt kupcake.studio"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#TechName}.Projekt\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"
Root: HKA; Subkey: "Software\Classes\{#TechName}.Projekt\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "Spustit {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  KlicOdinstalace = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppIdGuid}_is1';

// Starší verze (do 1.5, i Spellcast a tkStudio) byly nainstalované pro všechny uživatele (Program Files,
// záznam v HKLM). Bez práv správce je tento instalátor smazat nemůže – nabídne spustit jejich odinstalátor.
// Ten si o práva správce řekne sám (UAC); nastavení a modely nemaže (běží potichu, bez dotazu na data).
function OdinstalujStarouVerzi(): Boolean;
var
  Prikaz, Slozka: String;
  Kod: Integer;
begin
  Result := True;
  if not RegQueryStringValue(HKLM, KlicOdinstalace, 'UninstallString', Prikaz) then
    Exit;
  RegQueryStringValue(HKLM, KlicOdinstalace, 'InstallLocation', Slozka);
  if SuppressibleMsgBox('Na počítači je starší verze nainstalovaná pro všechny uživatele:' + #13#10 + Slozka + #13#10#13#10 +
       'Nová verze se instaluje bez práv správce jen pro tebe, proto je potřeba starou nejdřív odinstalovat ' +
       '(Windows se zeptá na potvrzení správce). Nastavení, presety a stažené modely zůstanou.' + #13#10#13#10 +
       'Odinstalovat starou verzi teď?', mbConfirmation, MB_YESNO, IDNO) <> IDYES then
  begin
    SuppressibleMsgBox('Instalace zrušena. Starou verzi můžeš odinstalovat v Nastavení → Aplikace a pak instalaci spustit znovu.',
      mbInformation, MB_OK, IDOK);
    Result := False;
    Exit;
  end;
  Prikaz := RemoveQuotes(Prikaz);
  if not ShellExec('', Prikaz, '/SILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, Kod)
     or RegKeyExists(HKLM, KlicOdinstalace) then
  begin
    SuppressibleMsgBox('Starou verzi se nepodařilo odinstalovat. Odinstaluj ji v Nastavení → Aplikace a spusť instalaci znovu.',
      mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

// Bez první části dat by Inno Setup chtěl „vložit disk 2“ – srozumitelnější je říct, co chybí, hned.
function ChybiCasti(): Boolean;
var
  Cast: String;
begin
  Cast := ExpandConstant('{src}\{#TechName}-Setup-{#AppVersion}-1.bin');
  Result := not FileExists(Cast);
  if Result then
    SuppressibleMsgBox('Vedle instalátoru chybí soubor:' + #13#10 + ExtractFileName(Cast) + #13#10#13#10 +
      'Instalátor má víc částí. Stáhni z Releases všechny soubory {#TechName}-Setup-{#AppVersion} ' +
      '(.exe i všechny .bin) do jedné složky a spusť instalátor znovu.', mbError, MB_OK, IDOK);
end;

function InitializeSetup(): Boolean;
begin
  Result := (not ChybiCasti()) and OdinstalujStarouVerzi();
end;

procedure SmazStaryKontext(Root: Integer; Klic: String);
var
  Pripony: TArrayOfString;
  i: Integer;
begin
  SetArrayLength(Pripony, 7);
  Pripony[0] := '.mp4'; Pripony[1] := '.mov'; Pripony[2] := '.mkv'; Pripony[3] := '.avi';
  Pripony[4] := '.webm'; Pripony[5] := '.m4v'; Pripony[6] := '.mts';
  for i := 0 to GetArrayLength(Pripony) - 1 do
    RegDeleteKeyIncludingSubkeys(Root, 'Software\Classes\SystemFileAssociations\' + Pripony[i] + '\shell\' + Klic);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // položky „Otevřít v tkStudio“ / „Otevřít ve Spellcast“ z kontextové nabídky uživatele
    // (ty pro všechny uživatele v HKLM odstranil odinstalátor staré verze)
    SmazStaryKontext(HKCU, 'tkStudio');
    SmazStaryKontext(HKCU, 'Spellcast');
  end;
end;

// Při odinstalaci nabídne „Smazat i stažené modely a nastavení“ (modely řeči a časování – i několik GB –,
// nastavení, presety, logy, automaticky uloženou práci). Projekty .kupcake a exportovaná videa zůstanou.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent() then
    if MsgBox('Smazat i stažené modely a nastavení?' + #13#10#13#10 +
              'Smaže se: stažené modely (i několik GB), nastavení, presety, logy a automaticky uložená práce.' + #13#10 +
              'Zůstanou: tvoje projekty (.kupcake) a exportovaná videa.' + #13#10#13#10 +
              'Pokud kupcake.studio plánuješ znovu nainstalovat, zvol Ne – modely se pak nebudou stahovat znovu.',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{localappdata}\{#TechName}'), True, True, True);
      DelTree(ExpandConstant('{userappdata}\{#TechName}'), True, True, True);
      // zbytky dřívějších názvů (kdyby se při přechodu nepřesunuly)
      DelTree(ExpandConstant('{localappdata}\tkStudio'), True, True, True);
      DelTree(ExpandConstant('{userappdata}\tkStudio'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\Spellcast'), True, True, True);
      DelTree(ExpandConstant('{userappdata}\Spellcast'), True, True, True);
    end;
end;
