# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('lib\\serviceinterface2.dll', 'lib'), ('lib\\libgcc_s_seh-1.dll', 'lib'), ('lib\\libstdc++-6.dll', 'lib'), ('lib\\libwinpthread-1.dll', 'lib')],
    datas=[('assets\\i10H.glb', 'assets'), ('assets\\i10H.STEP', 'assets'), ('assets\\twin_links\\link0.glb', 'assets/twin_links'), ('assets\\twin_links\\link1.glb', 'assets/twin_links'), ('assets\\twin_links\\link2.glb', 'assets/twin_links'), ('assets\\twin_links\\link3.glb', 'assets/twin_links'), ('assets\\twin_links\\link4.glb', 'assets/twin_links'), ('assets\\twin_links\\link5.glb', 'assets/twin_links'), ('static\\three\\three.module.js', 'static/three'), ('static\\three\\addons\\controls\\OrbitControls.js', 'static/three/addons/controls'), ('static\\three\\addons\\loaders\\GLTFLoader.js', 'static/three/addons/loaders'), ('static\\three\\addons\\utils\\BufferGeometryUtils.js', 'static/three/addons/utils')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'fastapi', 'pydantic', 'api_server', 'ros2_api_server', 'camera_orbbec', 'pyorbbecsdk', 'cv2', 'numpy'],
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
    name='aubo_host_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
