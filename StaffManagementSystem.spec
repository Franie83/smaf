# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('config.py', '.'), ('models.py', '.'), ('utils.py', '.')]
binaries = []
hiddenimports = ['flask', 'flask_sqlalchemy', 'flask_login', 'sqlalchemy', 'psycopg2', 'psycopg2_binary', 'cloudinary', 'cloudinary.uploader', 'cloudinary.api', 'rembg', 'rembg.session_factory', 'onnxruntime', 'PIL', 'PIL.Image', 'PIL.ImageEnhance', 'PIL.ImageFilter', 'pandas', 'numpy', 'openpyxl', 'requests', 'pywhatkit', 'webbrowser', 'hashlib', 'json', 'platform', 'socket', 'uuid', 'datetime', 're', 'io', 'zipfile', 'base64', 'tempfile']
datas += collect_data_files('rembg')
datas += collect_data_files('onnxruntime')
tmp_ret = collect_all('rembg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'test', 'tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StaffManagementSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
