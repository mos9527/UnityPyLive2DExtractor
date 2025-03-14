# -*- mode: python ; coding: utf-8 -*-

# https://github.com/K0lb3/UnityPy/issues/184
import UnityPy, UnityPyLive2DExtractor, archspec, os
unitypy_path = lambda path: os.path.join(os.path.dirname(UnityPy.__file__), path)
archspec_path = lambda path: os.path.join(os.path.dirname(archspec.__file__), path)
UnityPyLive2DExtractor_path = lambda path: os.path.join(os.path.dirname(UnityPyLive2DExtractor.__file__), path)
a = Analysis(
    ['UnityPyLive2DExtractor/__main__.py'],
    pathex=[
    ],
    binaries=[],
    datas=[
        (unitypy_path('resources/*'), 'UnityPy/resources'),
        (UnityPyLive2DExtractor_path(''), 'UnityPyLive2DExtractor'),
        (archspec_path('json'), 'archspec/json'),
    ],
    hiddenimports=[],
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
    name='UnityPyLive2DExtractor',
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
    icon='NONE',
)