# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['web_app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('attendance.db', '.'), ('requirements.txt', '.'), ('README.md', '.')],
    hiddenimports=['flask', 'flask_sqlalchemy', 'sqlite3', 'datetime', 'timedelta', 'zk', 'openpyxl', 'werkzeug', 'jinja2', 'markupsafe', 'itsdangerous', 'click', 'blinker'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AttendanceSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
