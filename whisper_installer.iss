[Setup]
AppName=ClipLingo Whisper Plugin
AppVersion=1.0
AppPublisher=ClipLingo
DefaultDirName={autopf}\ClipLingo\whisper_plugin
DefaultGroupName=ClipLingo
OutputBaseFilename=ClipLingo_Whisper_Setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
; 安装 whisper_plugin 目录到主程序安装目录下
Source: "dist\whisper_plugin\*"; DestDir: "{app}\whisper_plugin"; Flags: recursesubdirs

[Code]
// 检测主程序是否已安装
function IsMainAppInstalled(): Boolean;
begin
  Result := DirExists(ExpandConstant('{autopf}\ClipLingo'))
    and FileExists(ExpandConstant('{autopf}\ClipLingo\ClipLingo.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsMainAppInstalled() then
    begin
      MsgBox('注意：主程序 ClipLingo 未安装。' + #13#10 +
             '请先安装 ClipLingo_Setup.exe，然后再安装此插件。',
             mbInformation, MB_OK);
    end;
  end;
end;
