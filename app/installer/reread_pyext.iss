#define AppVersion GetEnv("REREAD_APP_VERSION")
#define BundleDir GetEnv("REREAD_BUNDLE_DIR")
#define OutputDir GetEnv("REREAD_OUTPUT_DIR")

[Setup]
AppId={{1C2061A9-87ED-41F5-926B-515B5664B382}
AppName=re/read Desktop
AppVersion={#AppVersion}
AppPublisher=re/read contributors
AppPublisherURL=https://github.com/nvtruongops/reread-pyext
AppSupportURL=https://github.com/nvtruongops/reread-pyext/issues
AppUpdatesURL=https://github.com/nvtruongops/reread-pyext/releases
AppComments=Offline desktop translator for selected text.
DefaultDirName={localappdata}\Programs\re-read Desktop
DefaultGroupName=re/read Desktop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=yes
UninstallDisplayName=re/read Desktop
UninstallDisplayIcon={app}\reread_pyext.exe
SetupIconFile={#BundleDir}\assets\icon.ico
OutputDir={#OutputDir}
OutputBaseFilename=reread_pyext_setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription=re/read Desktop Installer
VersionInfoProductName=re/read Desktop

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "vi"; MessagesFile: "languages\Vietnamese.isl"

[CustomMessages]
en.CreateDesktopShortcut=Create a desktop shortcut
vi.CreateDesktopShortcut=Tạo lối tắt trên màn hình nền
en.LaunchApp=Launch re/read Desktop
vi.LaunchApp=Mở re/read Desktop
en.UninstallDataPrompt=Uninstalling re/read Desktop will remove its settings, history, logs, and downloaded models.%n%nDo you want to continue?
vi.UninstallDataPrompt=Gỡ re/read Desktop sẽ xóa cài đặt, lịch sử, nhật ký và các mô hình đã tải.%n%nBạn có muốn tiếp tục không?

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\re/read Desktop"; Filename: "{app}\reread_pyext.exe"
Name: "{autodesktop}\re/read Desktop"; Filename: "{app}\reread_pyext.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopShortcut}"; Flags: unchecked

[Run]
Filename: "{app}\reread_pyext.exe"; Parameters: "--ui-language={language}"; Description: "{cm:LaunchApp}"; Flags: postinstall nowait skipifsilent; Check: not IsAutomaticUpdate
Filename: "{app}\reread_pyext.exe"; Parameters: "--ui-language={language}"; Flags: nowait; Check: IsAutomaticUpdate

[UninstallRun]
Filename: "{app}\reread_pyext.exe"; Parameters: "--uninstall-cleanup"; RunOnceId: "RereadRemoveUserData"; Flags: waituntilterminated skipifdoesntexist

[Code]
function IsAutomaticUpdate: Boolean;
begin
  Result := ExpandConstant('{param:RESTARTAPP|0}') = '1';
end;

function InitializeUninstall: Boolean;
begin
  Result := True;
  if not UninstallSilent then
    Result := MsgBox(
      ExpandConstant('{cm:UninstallDataPrompt}'),
      mbConfirmation, MB_YESNO) = IDYES;
end;
