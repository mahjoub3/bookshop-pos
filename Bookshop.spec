# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

all_django_helpers = (
    collect_submodules('whitenoise') +
    collect_submodules('crispy_forms') +
    collect_submodules('crispy_tailwind') +
    collect_submodules('django_htmx')
)
a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('shop', 'shop'),
        ('templates', 'templates'),
        ('static', 'static'),
        ('accounts', 'accounts'),
        ('catalog', 'catalog'),
        ('core', 'core'),
        ('customers', 'customers'),
        ('dashboard', 'dashboard'),
        ('inventory', 'inventory'),
        ('purchasing', 'purchasing'),
        ('reports', 'reports'),
        ('sales', 'sales'),
        ('.env', '.'),
    ],
    hiddenimports=[
        'shop.settings',
        'shop.urls',
        'shop.wsgi',
        'core.context_processors',
        'webview',
        'webview.platforms.edgechromium',
        'clr',
        'pythonnet',
    ] + all_django_helpers,
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
    [],
    exclude_binaries=True,
    name='Bookshop',
    debug=False,
    icon='bookshop.ico',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # <-- TEMP: show console to catch errors
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Bookshop',
)