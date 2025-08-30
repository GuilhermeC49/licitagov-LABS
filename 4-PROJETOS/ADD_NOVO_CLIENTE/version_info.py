# version_info.py — recurso de versão para PyInstaller
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),      # <-- AUMENTE quando rebuildar (ex.: 1,0,0,1)
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x4,
    fileType=0x1,               # 0x1 = app
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904b0', [  # 0409=en-US; 04b0=UTF-16. Pode manter assim.
        StringStruct('CompanyName', 'LicitaGov'),
        StringStruct('FileDescription', 'Criador de Estruturas LicitaGov'),
        StringStruct('FileVersion', '1.0.0.0'),    # <-- sincronia com filevers
        StringStruct('InternalName', 'LicitagovEstruturas'),
        StringStruct('OriginalFilename', 'LicitagovEstruturas.exe'),
        StringStruct('ProductName', 'Licitagov Estruturas'),
        StringStruct('ProductVersion', '1.0.0.0')  # <-- sincronia com prodvers
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
