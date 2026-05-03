; installer.iss - Inno Setup 安装包配置
[Setup]
AppName=Anki 卡片生成器
AppVersion=1.0
AppPublisher=AnkiMaker
DefaultDirName={autopf}\AnkiMaker
DefaultGroupName=AnkiMaker
OutputBaseFilename=AnkiMaker_Setup
OutputDir=installer
Compression=lzma2/ultra64
SolidCompression=yes
; 要求管理员权限（写入 Program Files 需要）
PrivilegesRequired=admin

[Files]
; 主程序（PyInstaller 打包产物）
Source: "dist\anki-maker\*"; DestDir: "{app}"; Flags: recursesubdirs
; ffmpeg 二进制文件
Source: "bin\ffmpeg.exe"; DestDir: "{app}\bin"
Source: "bin\ffprobe.exe"; DestDir: "{app}\bin"

[Icons]
Name: "{group}\Anki 卡片生成器"; Filename: "{app}\anki-maker.exe"
Name: "{userdesktop}\Anki 卡片生成器"; Filename: "{app}\anki-maker.exe"

[Run]
Filename: "{app}\anki-maker.exe"; Description: "立即启动"; Flags: postinstall skipifsilent

[UninstallDelete]
; 卸载时清理用户生成的 output 目录
Type: filesandordirs; Name: "{app}\output"
Type: filesandordirs; Name: "{app}\temp"
