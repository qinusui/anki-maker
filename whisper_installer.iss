[Setup]
AppName=ClipLingo Whisper Plugin
AppVersion=1.0
AppPublisher=ClipLingo
DefaultDirName={autopf}\ClipLingo
DefaultGroupName=ClipLingo
OutputBaseFilename=ClipLingo_Whisper_Setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=frontend\public\favicon.ico
DisableDirPage=no

[Files]
; 安装 whisper_plugin 到主程序同级目录
Source: "dist\whisper_plugin\*"; DestDir: "{app}\whisper_plugin"; Flags: recursesubdirs

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not FileExists(ExpandConstant('{app}\ClipLingo.exe')) then
    begin
      MsgBox('注意：所选目录未检测到 ClipLingo.exe。' + #13#10 +
             '请确保 Whisper 插件安装在 ClipLingo 主程序同级目录下，否则无法启用转录功能。',
             mbInformation, MB_OK);
    end;
  end;
end;
