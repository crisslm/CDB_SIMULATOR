; ==============================================================================
; Script do Inno Setup para CDB Simulator (Desktop)
; Para compilar: iscc CDB_Simulator.iss
; Baixe o Inno Setup em: https://jrsoftware.org/isinfo.php
; ==============================================================================

[Setup]
AppName=CDB Simulator
AppVersion=1.0.0
AppPublisher=CDB Simulator
AppPublisherURL=https://github.com/crisslm/CDB_SIMULATOR
AppSupportURL=https://github.com/crisslm/CDB_SIMULATOR/issues
AppUpdatesURL=https://github.com/crisslm/CDB_SIMULATOR/releases
DefaultDirName={pf}\CDB Simulator
DefaultGroupName=CDB Simulator
AllowNoIcons=yes
LicenseFile=
OutputDir=installer
OutputBaseFilename=CDB_Simulator_Setup_1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "portugues"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; O executável gerado pelo PyInstaller
Source: "dist\CDB_Simulator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CDB Simulator"; Filename: "{app}\CDB_Simulator.exe"
Name: "{group}\Desinstalar CDB Simulator"; Filename: "{uninstallexe}"
Name: "{commondesktop}\CDB Simulator"; Filename: "{app}\CDB_Simulator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CDB_Simulator.exe"; Description: "{cm:LaunchProgram,CDB Simulator}"; Flags: nowait postinstall skipifsilent

; Nota: A pasta de dados do usuário (~/.cdb_simulator) NÃO é removida na desinstalação.
; O Inno Setup não remove pastas fora de {app} a menos que listadas em [UninstallDelete].
