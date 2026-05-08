Write-Host "开始一键打包 Aubo Windows 综合上位机 (GUI + FastAPI) 为单文件 .exe ..." -ForegroundColor Green

pip install pyinstaller

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "aubo_host_app.spec") { Remove-Item -Force "aubo_host_app.spec" }

pyinstaller --onefile --windowed --name "aubo_host_app" `
  --add-binary "lib\serviceinterface2.dll;lib" `
  --add-binary "lib\libgcc_s_seh-1.dll;lib" `
  --add-binary "lib\libstdc++-6.dll;lib" `
  --add-binary "lib\libwinpthread-1.dll;lib" `
  --add-data "assets\i10H.glb;assets" `
  --add-data "assets\i10H.STEP;assets" `
  --add-data "assets\twin_links\link0.glb;assets/twin_links" `
  --add-data "assets\twin_links\link1.glb;assets/twin_links" `
  --add-data "assets\twin_links\link2.glb;assets/twin_links" `
  --add-data "assets\twin_links\link3.glb;assets/twin_links" `
  --add-data "assets\twin_links\link4.glb;assets/twin_links" `
  --add-data "assets\twin_links\link5.glb;assets/twin_links" `
  --add-data "static\three\three.module.js;static/three" `
  --add-data "static\three\addons\controls\OrbitControls.js;static/three/addons/controls" `
  --add-data "static\three\addons\loaders\GLTFLoader.js;static/three/addons/loaders" `
  --add-data "static\three\addons\utils\BufferGeometryUtils.js;static/three/addons/utils" `
  --hidden-import "uvicorn.logging" `
  --hidden-import "uvicorn.loops" `
  --hidden-import "uvicorn.loops.auto" `
  --hidden-import "uvicorn.loops.asyncio" `
  --hidden-import "uvicorn.protocols" `
  --hidden-import "uvicorn.protocols.http" `
  --hidden-import "uvicorn.protocols.http.auto" `
  --hidden-import "uvicorn.protocols.http.h11_impl" `
  --hidden-import "uvicorn.protocols.websockets" `
  --hidden-import "uvicorn.protocols.websockets.auto" `
  --hidden-import "uvicorn.lifespan.on" `
  --hidden-import "uvicorn.lifespan.off" `
  --hidden-import "fastapi" `
  --hidden-import "pydantic" `
  --hidden-import "api_server" `
  --hidden-import "ros2_api_server" `
  --hidden-import "camera_orbbec" `
  --hidden-import "pyorbbecsdk" `
  --hidden-import "cv2" `
  --hidden-import "numpy" `
  main.py

if ($?) {
  Write-Host "打包完成！可执行文件位于: dist\aubo_host_app.exe" -ForegroundColor Cyan
} else {
  Write-Host "打包失败，请检查错误日志。" -ForegroundColor Red
}
