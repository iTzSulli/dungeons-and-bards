#define AppName "Dungeon & Bard"
#define AppVersion "1.0.0"
#define AppExecutable "DungeonAndBardGame.exe"

[Setup]
AppId={{4F255A5A-2077-40E2-8A78-9D10628E23D9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Dungeon & Bard
DefaultDirName={autopf}\Dungeon & Bard
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExecutable}
OutputDir=dist
OutputBaseFilename=DungeonAndBardSetup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
Uninstallable=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti aggiuntivi:"; Flags: unchecked

[Files]
Source: "dist\{#AppExecutable}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExecutable}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExecutable}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExecutable}"; Description: "Avvia {#AppName}"; Flags: postinstall nowait skipifsilent
