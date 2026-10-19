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
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion=0.1.0.0
VersionInfoDescription=re/read Desktop Installer
VersionInfoProductName=re/read Desktop

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\re/read Desktop"; Filename: "{app}\reread_pyext.exe"
Name: "{autodesktop}\re/read Desktop"; Filename: "{app}\reread_pyext.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo lối tắt trên màn hình nền"; Flags: unchecked

[Run]
Filename: "{app}\reread_pyext.exe"; Description: "Mở re/read Desktop"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\reread_pyext.exe"; Parameters: "--uninstall-cleanup"; RunOnceId: "RereadRemoveUserData"; Flags: waituntilterminated skipifdoesntexist

[Code]
function InitializeUninstall: Boolean;
begin
  Result := True;
  if not UninstallSilent then
    Result := MsgBox(
      'Gỡ re/read Desktop sẽ xóa cài đặt, thiết lập, lịch sử, nhật ký và các mô hình đã tải.' + #13#10 + #13#10 +
      'Bạn có muốn tiếp tục không?',
      mbConfirmation, MB_YESNO) = IDYES;
end;
