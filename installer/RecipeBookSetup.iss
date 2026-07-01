#define MyAppName "Книга рецептов"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Recipe Book"
#define MyAppExeName "RecipeBook.exe"
#define MyLauncherExeName "RecipeBookLauncher.exe"

#define ReleaseDirectory "..\release"
#define AppIcon "..\desktop\assets\RecipeBook.ico"
#define PrerequisitesDirectory "prerequisites"


[Setup]
AppId={{8BD57778-F873-426F-93E4-90BDF4544800}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\RecipeBook
DefaultGroupName={#MyAppName}

OutputDir=..\installer-output
OutputBaseFilename=RecipeBookSetup-{#MyAppVersion}

SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#MyLauncherExeName}

Compression=lzma2
SolidCompression=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Нужны повышенные права для системной установки Docker.
PrivilegesRequired=admin

WizardStyle=modern

DisableProgramGroupPage=yes
AllowNoIcons=no

CloseApplications=yes
RestartApplications=no
RestartIfNeededByRun=yes

SetupLogging=yes


[Languages]
Name: "russian"; \
    MessagesFile: "compiler:Languages\Russian.isl"


[Tasks]
Name: "desktopicon"; \
    Description: "Создать ярлык на рабочем столе"; \
    GroupDescription: "Дополнительные ярлыки:"; \
    Flags: checkedonce


[Files]
Source: "{#ReleaseDirectory}\RecipeBook.exe"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\RecipeBookLauncher.exe"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\Start.bat"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\compose.yaml"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\Dockerfile"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\requirements.txt"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\alembic.ini"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\.env"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "{#ReleaseDirectory}\backend\*"; \
    DestDir: "{app}\backend"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

Source: "{#ReleaseDirectory}\scripts\*"; \
    DestDir: "{app}\scripts"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

Source: "{#ReleaseDirectory}\backups\initial\*"; \
    DestDir: "{app}\backups\initial"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

Source: "{#PrerequisitesDirectory}\Docker Desktop Installer.exe"; \
    Flags: dontcopy

Source: "{#PrerequisitesDirectory}\wsl-x64.msi"; \
    Flags: dontcopy

Source: "{#PrerequisitesDirectory}\InstallPrerequisites.ps1"; \
    Flags: dontcopy

Source: "{#ReleaseDirectory}\media\*"; \
    DestDir: "{app}\media"; \
    Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

[Dirs]
Name: "{app}\media"
Name: "{app}\media\recipes"
Name: "{app}\backups"


[Icons]
Name: "{autodesktop}\Книга рецептов"; \
    Filename: "{app}\{#MyLauncherExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyLauncherExeName}"; \
    Tasks: desktopicon

Name: "{group}\Книга рецептов"; \
    Filename: "{app}\{#MyLauncherExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyLauncherExeName}"


[Run]
Filename: "{app}\{#MyLauncherExeName}"; \
    Description: "Запустить Книгу рецептов"; \
    WorkingDir: "{app}"; \
    Flags: nowait postinstall skipifsilent; \
    Check: CanLaunchRecipeBook


[Code]

var
  PrerequisitesNeedRestart: Boolean;


function PrepareToInstall(
  var NeedsRestart: Boolean
): String;
var
  PowerShellPath: String;
  PowerShellParameters: String;
  RestartMarker: String;
  ResultCode: Integer;
begin
  Result := '';
  PrerequisitesNeedRestart := False;

  try
    ExtractTemporaryFile(
      'Docker Desktop Installer.exe'
    );

    ExtractTemporaryFile(
      'wsl-x64.msi'
    );

    ExtractTemporaryFile(
      'InstallPrerequisites.ps1'
    );
  except
    Result :=
      'Не удалось распаковать системные компоненты: ' +
      GetExceptionMessage;
    Exit;
  end;

  RestartMarker :=
    ExpandConstant(
      '{tmp}\RecipeBookRestart.required'
    );

  PowerShellPath :=
    ExpandConstant(
      '{sysnative}\WindowsPowerShell\v1.0\powershell.exe'
    );

  PowerShellParameters :=
    '-NoLogo ' +
    '-NoProfile ' +
    '-NonInteractive ' +
    '-ExecutionPolicy Bypass ' +
    '-WindowStyle Hidden ' +
    '-File "' +
    ExpandConstant(
      '{tmp}\InstallPrerequisites.ps1'
    ) +
    '" ' +
    '-DockerInstaller "' +
    ExpandConstant(
      '{tmp}\Docker Desktop Installer.exe'
    ) +
    '" ' +
    '-WslInstaller "' +
    ExpandConstant(
      '{tmp}\wsl-x64.msi'
    ) +
    '" ' +
    '-RestartMarker "' +
    RestartMarker +
    '"';

  WizardForm.StatusLabel.Caption :=
    'Подготовка системных компонентов...';

  if not Exec(
    PowerShellPath,
    PowerShellParameters,
    ExpandConstant('{tmp}'),
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    Result :=
      'Не удалось запустить установку системных компонентов.';
    Exit;
  end;

  if ResultCode <> 0 then
  begin
    Result :=
      'Не удалось установить или обновить WSL и Docker Desktop.' +
      Chr(13) + Chr(10) +
      Chr(13) + Chr(10) +
      'Журнал установки:' +
      Chr(13) + Chr(10) +
      'C:\ProgramData\RecipeBook\logs\' +
      'prerequisites-install.log';
    Exit;
  end;

  if FileExists(RestartMarker) then
  begin
    NeedsRestart := True;
    PrerequisitesNeedRestart := True;
  end;
end;


function CanLaunchRecipeBook(): Boolean;
begin
  Result := not PrerequisitesNeedRestart;
end;