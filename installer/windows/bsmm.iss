; Current Python/Vue application. Compile only through build.py (canonical version).
#ifndef AppVersion
  #error AppVersion must be supplied by build.py
#endif
#ifndef BundleDir
  #error BundleDir must be supplied by build.py
#endif

[Setup]
AppId={{EC42155A-D71C-4609-A40A-18FBBE0D91B2}
AppName=Bitcoin Solo Miner Monitor
AppVersion={#AppVersion}
VersionInfoVersion={#FileVersion}
VersionInfoProductTextVersion={#AppVersion}
AppPublisher=Bitcoin Solo Miner Monitor
DefaultDirName={localappdata}\Programs\Bitcoin Solo Miner Monitor
DefaultGroupName=Bitcoin Solo Miner Monitor
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=bsmm-{#AppVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=no
RestartApplications=no
UninstallDisplayIcon={app}\bsmm.exe

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Start dashboard"; Filename: "{app}\bsmm.exe"; Parameters: "start --open"; WorkingDir: "{app}"; Flags: runminimized
Name: "{group}\Stop dashboard"; Filename: "{app}\bsmm.exe"; Parameters: "stop"; WorkingDir: "{app}"; Flags: runminimized
Name: "{group}\Agent guide"; Filename: "{app}\AGENT-GUIDE.txt"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\bsmm.exe"; Parameters: "start --open"; Description: "Open the dashboard"; Flags: postinstall nowait skipifsilent runminimized

; Never delete the user's platform data directory, database, encryption key or credentials.
; Inno removes only the files it installed. No wildcard [UninstallDelete] section.
[Code]
function StopExisting(): Boolean;
var
  Code: Integer;
  Exe: String;
begin
  Exe := ExpandConstant('{app}\bsmm.exe');
  Result := True;
  if FileExists(Exe) then
    Result := Exec(Exe, 'stop', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not StopExisting() then
    Result := 'Could not safely stop this monitor. Stop its background instance or service, then retry. User data has not been removed.';
end;

function InitializeUninstall(): Boolean;
begin
  Result := StopExisting();
  if not Result then
    MsgBox('Could not safely stop this monitor. Uninstall cancelled; data and application files were retained.', mbError, MB_OK);
end;
