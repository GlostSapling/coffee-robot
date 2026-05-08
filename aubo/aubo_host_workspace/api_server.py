import logging
import os
import sys
import threading
from typing import List

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

import core_state

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(
    title="Aubo Robot WebAPI Host",
    description="Web 控制页面 + 机械臂与相机统一 REST API",
    version="2.0.0",
)

_camera_stream_enabled = False
_camera_stream_lock = threading.Lock()


def _set_camera_stream_enabled(enabled: bool):
    global _camera_stream_enabled
    with _camera_stream_lock:
        _camera_stream_enabled = bool(enabled)


def _is_camera_stream_enabled() -> bool:
    with _camera_stream_lock:
        return _camera_stream_enabled


class MoveJRequest(BaseModel):
    joints: List[float]


class ConnectRequest(BaseModel):
    ip: str
    port: int = 8899


class CameraSelectRequest(BaseModel):
    serial: str = ""


class CaptureVideoRequest(BaseModel):
    duration_sec: int = 3


class StreamToggleRequest(BaseModel):
    enabled: bool


def _robot_or_raise():
    robot = core_state.get_robot()
    if not robot:
        raise HTTPException(status_code=500, detail="上位机 SDK 尚未初始化")
    return robot


def _camera_or_raise():
    cam = core_state.get_camera_service()
    if not cam:
        raise HTTPException(status_code=500, detail="相机服务未初始化")
    return cam


def _media_store_or_raise():
    store = core_state.get_media_store()
    if not store:
        raise HTTPException(status_code=500, detail="媒体存储未初始化")
    return store


def _resource_path(*parts: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_dir = getattr(sys, "_MEIPASS")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *parts)


@app.get("/", response_class=HTMLResponse)
def web_home():
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Aubo Web 控制台</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", "PingFang SC", sans-serif; background: #0b1220; color: #e5e7eb; }
    .wrap { max-width: 1180px; margin: 16px auto; padding: 0 16px 24px; }
    .head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    .title { font-size: 22px; font-weight: 700; letter-spacing: .4px; }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }
    .card { background: #111b2e; border: 1px solid #1f2a44; border-radius: 14px; padding: 14px; box-shadow: 0 8px 20px rgba(0,0,0,.25); }
    .c4 { grid-column: span 4; } .c6 { grid-column: span 6; } .c8 { grid-column: span 8; } .c12 { grid-column: span 12; }
    h3 { margin: 0 0 10px; font-size: 16px; color: #93c5fd; }
    .row { display: flex; gap: 8px; align-items: center; margin: 8px 0; flex-wrap: wrap; }
    input, select { background: #0f172a; color: #e5e7eb; border: 1px solid #334155; border-radius: 8px; padding: 8px 10px; min-width: 140px; }
    input.wide { min-width: 420px; width: 100%; }
    button { background: #2563eb; color: #fff; border: 0; padding: 8px 12px; border-radius: 8px; cursor: pointer; }
    button:hover { background: #3b82f6; }
    button.gray { background: #475569; } button.danger { background: #dc2626; } button.green { background: #059669; } button.purple { background: #7c3aed; }
    pre { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px; max-height: 220px; overflow: auto; white-space: pre-wrap; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #23304d; padding: 8px; font-size: 13px; text-align: left; }
    .muted { color: #94a3b8; font-size: 12px; }
    .badge { padding: 6px 10px; border-radius: 999px; font-size: 12px; border: 1px solid #334155; }
    .badge.ok { background: #064e3b; color: #a7f3d0; border-color: #065f46; }
    .badge.off { background: #3f1d1d; color: #fecaca; border-color: #7f1d1d; }
    #twinViewport { width: 100%; height: 420px; border: 1px solid #334155; border-radius: 12px; overflow: hidden; background: #0b1220; }
    @media (max-width: 1024px) { .c4, .c6, .c8 { grid-column: span 12; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="title">Aubo Web 控制台</div>
      <div class="muted">WebAPI 与 GUI 功能对齐（测试版）</div>
    </div>
    <div class="grid">
      <div class="card c12">
        <h3>机械臂连接状态</h3>
        <div class="row">
          <input id="ip" value="192.168.10.3" />
          <button onclick="connectRobot()">连接</button>
          <button class="gray" onclick="disconnectRobot()">断开</button>
          <button class="green" onclick="refreshStatus()">刷新状态</button>
          <span id="connBadge" class="badge off">未连接</span>
          <span class="muted">状态信息会实时回填到 MoveJ 滑条</span>
        </div>
        <pre id="statusBox">等待操作...</pre>
      </div>

      <div id="twinCard" class="card c6" style="display:none;">
        <h3>实时相机流</h3>
        <div class="row">
          <button class="green" onclick="startCameraStream()">开启实时相机流</button>
          <button class="gray" onclick="stopCameraStream()">关闭实时相机流</button>
          <span id="streamState" class="muted">流状态: 已关闭</span>
        </div>
        <div class="row">
          <img id="streamImg" style="width:100%;max-width:720px;border:1px solid #334155;border-radius:10px;display:none;" />
        </div>
      </div>

      <div class="card c6">
        <h3>数字孪生（Web 3D）</h3>
        <div class="row">
          <button class="green" onclick="updateTwinState()">刷新孪生状态</button>
          <a href="/api/twin/step" target="_blank"><button class="gray">下载STEP</button></a>
          <a href="/api/twin/model.glb" target="_blank"><button class="gray">下载GLB</button></a>
          <span id="twinState" class="muted">状态: 待初始化</span>
        </div>
        <div id="twinViewport"></div>
        <div class="muted">说明：STEP 已转换为 GLB，并由 Three.js 渲染；运动状态与关节角实时联动。</div>
      </div>

      <div class="card c8">
        <h3>MoveJ 控制（点位 + 滑条 + 直接输入）</h3>
        <div class="row"><input id="pointName" placeholder="点位名称（例如 home）" />
          <button class="gray" onclick="savePoint()">保存点位</button>
          <select id="pointSelect"></select>
          <button class="gray" onclick="loadPoint()">加载点位</button>
        </div>
        <div class="row">
          <span>J1</span><input id="j1" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j1v">0.0°</span>
        </div>
        <div class="row">
          <span>J2</span><input id="j2" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j2v">0.0°</span>
        </div>
        <div class="row">
          <span>J3</span><input id="j3" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j3v">0.0°</span>
        </div>
        <div class="row">
          <span>J4</span><input id="j4" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j4v">0.0°</span>
        </div>
        <div class="row">
          <span>J5</span><input id="j5" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j5v">0.0°</span>
        </div>
        <div class="row">
          <span>J6</span><input id="j6" type="range" min="-175" max="175" step="0.1" value="0" oninput="syncFromSliders()" />
          <span id="j6v">0.0°</span>
        </div>
        <div class="row">
          <input id="joints" class="wide" value="[0, 0, 0, 0, 0, 0]" />
          <button class="green" onclick="movej()">执行 MoveJ</button>
        </div>
        <div class="muted">提示：滑条单位为度（deg），输入框单位为弧度（rad），两者会自动同步。</div>
        <pre id="movejBox">等待操作...</pre>
      </div>

      <div class="card c4">
        <h3>相机选择与相机操作</h3>
        <div class="row">
          <button onclick="loadCameras()">刷新相机列表</button>
          <select id="cameraSelect"></select>
          <button class="purple" onclick="applyCamera()">应用相机</button>
        </div>
        <div class="row">
          <button onclick="capturePhoto()">拍照</button>
          <button onclick="captureVideo(3)">录像3秒</button>
          <button onclick="captureVideo(5)">录像5秒</button>
          <button onclick="captureVideo(10)">录像10秒</button>
        </div>
        <div class="row">
          <button class="purple" onclick="captureDepthPhoto()">深度拍照</button>
          <button class="purple" onclick="captureDepthVideo(3)">深度3秒</button>
          <button class="purple" onclick="captureDepthVideo(5)">深度5秒</button>
          <button class="purple" onclick="captureDepthVideo(10)">深度10秒</button>
        </div>
        <pre id="camBox">等待操作...</pre>
        <pre id="captureBox">等待操作...</pre>
      </div>

      <div class="card c12">
        <h3>媒体记录</h3>
        <div class="row"><button onclick="loadMedia()">刷新媒体列表</button></div>
        <table>
          <thead><tr><th>ID</th><th>类型</th><th>文件</th><th>时长</th><th>分辨率</th><th>FPS</th><th>备注</th><th>操作</th></tr></thead>
          <tbody id="mediaBody"></tbody>
        </table>
      </div>
    </div>
  </div>
<script type="importmap">
{
  "imports": {
    "three": "/static/three/three.module.js",
    "three/addons/": "/static/three/addons/"
  }
}
</script>
<script>

async function api(path, opts={}) {
  const r = await fetch(path, {headers: {'Content-Type':'application/json'}, ...opts});
  const txt = await r.text();
  let data = {};
  try { data = txt ? JSON.parse(txt) : {}; } catch { data = {raw: txt}; }
  if (!r.ok) throw new Error(data.detail || data.message || txt || ('HTTP ' + r.status));
  return data;
}
function show(id, obj){ document.getElementById(id).textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2); }
let robotConnected = false;
function setConnBadge(connected){
  robotConnected = !!connected;
  const el = document.getElementById('connBadge');
  if(!el) return;
  el.className = connected ? 'badge ok' : 'badge off';
  el.textContent = connected ? '已连接' : '未连接';
}
function deg2rad(d){ return d * Math.PI / 180.0; }
function rad2deg(r){ return r * 180.0 / Math.PI; }
function getSliderDeg(){ return [1,2,3,4,5,6].map(i => Number(document.getElementById('j'+i).value)); }
function setSliderDeg(vals){
  [1,2,3,4,5,6].forEach(i => {
    const v = Number(vals[i-1] || 0);
    document.getElementById('j'+i).value = v;
    document.getElementById('j'+i+'v').textContent = v.toFixed(1) + '°';
  });
}
function syncFromSliders(){
  const d = getSliderDeg();
  setSliderDeg(d);
  const r = d.map(deg2rad);
  document.getElementById('joints').value = JSON.stringify(r.map(x => Number(x.toFixed(6))));
}
function syncFromInput(){
  try{
    const r = JSON.parse(document.getElementById('joints').value);
    if(Array.isArray(r) && r.length === 6){
      setSliderDeg(r.map(rad2deg));
    }
  }catch(_){}
}
function loadPointNames(){
  const raw = localStorage.getItem('aubo_points') || '{}';
  const map = JSON.parse(raw);
  const sel = document.getElementById('pointSelect');
  sel.innerHTML = '';
  Object.keys(map).sort().forEach(name => {
    const o = document.createElement('option');
    o.value = name;
    o.textContent = name;
    sel.appendChild(o);
  });
}
function savePoint(){
  const name = (document.getElementById('pointName').value || '').trim();
  if(!name){ alert('请输入点位名称'); return; }
  const raw = localStorage.getItem('aubo_points') || '{}';
  const map = JSON.parse(raw);
  map[name] = getSliderDeg();
  localStorage.setItem('aubo_points', JSON.stringify(map));
  loadPointNames();
  document.getElementById('pointSelect').value = name;
}
function loadPoint(){
  const name = document.getElementById('pointSelect').value;
  const raw = localStorage.getItem('aubo_points') || '{}';
  const map = JSON.parse(raw);
  if(!map[name]) return;
  setSliderDeg(map[name]);
  syncFromSliders();
}
async function connectRobot(){ try{ const ip=document.getElementById('ip').value.trim(); show('statusBox', await api('/api/connect',{method:'POST',body:JSON.stringify({ip})})); setConnBadge(true); await refreshStatus(); }catch(e){setConnBadge(false); show('statusBox', e.message);} }
async function disconnectRobot(){ try{ show('statusBox', await api('/api/disconnect',{method:'POST'})); }catch(e){show('statusBox', e.message);} setConnBadge(false); }
async function refreshStatus(){
  try{
    const d = await api('/api/status');
    show('statusBox', d);
    const joints = (d && Array.isArray(d.joints)) ? d.joints : [];
    if(joints.length === 6){
      setSliderDeg(joints.map(rad2deg));
      document.getElementById('joints').value = JSON.stringify(joints.map(x => Number(x.toFixed(6))));
      updateTwinFromJoints(joints);
    }
    setConnBadge(true);
  }catch(e){
    setConnBadge(false);
    show('statusBox', e.message);
  }
}
async function movej(){
  try{
    syncFromInput();
    const joints=JSON.parse(document.getElementById('joints').value);
    show('movejBox', await api('/api/movej',{method:'POST',body:JSON.stringify({joints})}));
  }catch(e){show('movejBox', e.message);}
}
async function startCameraStream(){
  try{
    await api('/api/camera_stream/toggle',{method:'POST',body:JSON.stringify({enabled:true})});
    const img=document.getElementById('streamImg');
    img.style.display='block';
    img.src='/api/camera_stream.mjpg?t='+Date.now();
    document.getElementById('streamState').textContent='流状态: 运行中';
  }catch(e){ alert(e.message); }
}
async function stopCameraStream(){
  try{
    await api('/api/camera_stream/toggle',{method:'POST',body:JSON.stringify({enabled:false})});
  }catch(_e){}
  const img=document.getElementById('streamImg');
  img.src='';
  img.style.display='none';
  document.getElementById('streamState').textContent='流状态: 已关闭';
}
async function loadCameras(){ try{ const d=await api('/api/cameras'); const sel=document.getElementById('cameraSelect'); sel.innerHTML=''; (d.devices||[]).forEach(x=>{ const o=document.createElement('option'); o.value=x.serial||''; o.textContent=x.label; sel.appendChild(o); }); show('camBox', d); }catch(e){show('camBox', e.message);} }
async function applyCamera(){ try{ const serial=document.getElementById('cameraSelect').value||''; show('camBox', await api('/api/cameras/select',{method:'POST',body:JSON.stringify({serial})})); }catch(e){show('camBox', e.message);} }
async function capturePhoto(){ try{ show('captureBox', await api('/api/capture/photo',{method:'POST'})); await loadMedia(); }catch(e){show('captureBox', e.message);} }
async function captureVideo(sec){ try{ show('captureBox', await api('/api/capture/video',{method:'POST',body:JSON.stringify({duration_sec:sec})})); await loadMedia(); }catch(e){show('captureBox', e.message);} }
async function captureDepthPhoto(){ try{ show('captureBox', await api('/api/capture/depth_photo',{method:'POST'})); await loadMedia(); }catch(e){show('captureBox', e.message);} }
async function captureDepthVideo(sec){ try{ show('captureBox', await api('/api/capture/depth_video',{method:'POST',body:JSON.stringify({duration_sec:sec})})); await loadMedia(); }catch(e){show('captureBox', e.message);} }
async function loadMedia(){
  try{
    const d=await api('/api/media');
    const body=document.getElementById('mediaBody');
    body.innerHTML='';
    (d.items||[]).forEach(m=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${m.id}</td><td>${m.media_type}</td><td>${m.file_name}</td><td>${m.duration_sec}s</td><td>${m.width}x${m.height}</td><td>${Number(m.fps).toFixed(1)}</td><td>${m.extra_info||''}</td><td><a href="/api/media/${m.id}/file" target="_blank">打开</a> <button class="danger" onclick="delMedia(${m.id})">删除</button></td>`;
      body.appendChild(tr);
    });
  }catch(e){ console.error(e); }
}
async function delMedia(id){ try{ await api('/api/media/'+id,{method:'DELETE'}); await loadMedia(); }catch(e){ alert(e.message);} }

let twin = {
  scene: null, camera: null, renderer: null, controls: null,
  joints: [0,0,0,0,0,0], rig: [], modelFrame: null, ready: false, THREE: null,
  jointGroups: [], jointAxisNames: [], linksBound: false
};
async function initTwin(){
  let THREE = null;
  let OrbitControls = null;
  let GLTFLoader = null;
  try{
    THREE = await import('three');
    const orbitMod = await import('three/addons/controls/OrbitControls.js');
    const gltfMod = await import('three/addons/loaders/GLTFLoader.js');
    OrbitControls = orbitMod.OrbitControls;
    GLTFLoader = gltfMod.GLTFLoader;
  }catch(e){
    const box = document.getElementById('twinState');
    if (box) box.textContent = '状态: 3D 资源加载失败（不影响连接/控制功能）';
    console.error(e);
    return;
  }

  const host = document.getElementById('twinViewport');
  if(!host) return;
  host.innerHTML = '';
  const w = host.clientWidth || 960;
  const h = host.clientHeight || 420;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b1220);
  const camera = new THREE.PerspectiveCamera(42, w/h, 0.01, 100);
  camera.position.set(2.2, 1.6, 2.8);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(w, h);
  host.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.7, 0);
  controls.update();

  scene.add(new THREE.AmbientLight(0xffffff, 0.65));
  const dl = new THREE.DirectionalLight(0xffffff, 0.85);
  dl.position.set(2.2, 3.0, 2.4);
  scene.add(dl);
  scene.add(new THREE.GridHelper(4, 24, 0x334155, 0x1e293b));

  // 运动骨架（仅用于驱动与校准，可见度较低）
  const rigMat = new THREE.MeshStandardMaterial({ color: 0x60a5fa, metalness: 0.28, roughness: 0.55, transparent: true, opacity: 0.22 });
  const base = new THREE.Group();
  scene.add(base);
  const baseMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.16, 40), rigMat);
  baseMesh.position.y = 0.08;
  base.add(baseMesh);
  const j1 = new THREE.Group(); j1.position.set(0, 0.16, 0); base.add(j1);
  const l1 = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.34, 0.22), rigMat); l1.position.y = 0.17; j1.add(l1);
  const j2 = new THREE.Group(); j2.position.set(0, 0.34, 0); j1.add(j2);
  const l2 = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.52, 0.18), rigMat); l2.position.y = 0.26; j2.add(l2);
  const j3 = new THREE.Group(); j3.position.set(0, 0.52, 0); j2.add(j3);
  const l3 = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.44, 0.16), rigMat); l3.position.y = 0.22; j3.add(l3);
  const j4 = new THREE.Group(); j4.position.set(0, 0.44, 0); j3.add(j4);
  const l4 = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.28, 24), rigMat); l4.rotation.z = Math.PI/2; l4.position.set(0.14, 0, 0); j4.add(l4);
  const j5 = new THREE.Group(); j5.position.set(0.28, 0, 0); j4.add(j5);
  const l5 = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 0.12), rigMat); j5.add(l5);
  const j6 = new THREE.Group(); j6.position.set(0.12, 0, 0); j5.add(j6);
  const tcp = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.16, 20), new THREE.MeshStandardMaterial({ color: 0x34d399 }));
  tcp.rotation.z = -Math.PI/2;
  tcp.position.x = 0.10;
  j6.add(tcp);

  // STEP 转换后的 GLB 分段模型（按关节绑定，单位mm，Z朝上）
  const modelFrame = new THREE.Group();
  modelFrame.rotation.x = -Math.PI / 2; // CAD Z-up -> three Y-up
  modelFrame.scale.setScalar(0.001); // mm -> m
  scene.add(modelFrame);

  // 关节中心（CAD 坐标，mm）与轴向（在 CAD 坐标下）
  const jointPivots = [
    new THREE.Vector3(0, 0, 171),
    new THREE.Vector3(0, -197, 503),
    new THREE.Vector3(0, -203, 806),
    new THREE.Vector3(0, -78, 1407),
    new THREE.Vector3(0, -198, 1510),
    new THREE.Vector3(0, -275, 1517),
  ];
  const jointAxes = [
    new THREE.Vector3(0, 0, 1),   // J1
    new THREE.Vector3(1, 0, 0),   // J2
    new THREE.Vector3(1, 0, 0),   // J3
    new THREE.Vector3(0, 0, 1),   // J4
    new THREE.Vector3(1, 0, 0),   // J5
    new THREE.Vector3(0, 0, 1),   // J6
  ];
  // 方向校正：根据实机对比先整体翻转一版，后续再逐轴微调
  const jointSigns = [-1, 1, 1, -1, 1, -1];

  const modelLinks = [];
  const jointAxisNames = ["z", "x", "x", "z", "x", "z"];
  const jointGroups = [];
  for (let i = 0; i < 6; i++) {
    const g = new THREE.Group();
    g.position.copy(jointPivots[i]);
    jointGroups.push(g);
  }
  modelFrame.add(jointGroups[0]);
  for (let i = 1; i < 6; i++) {
    jointGroups[i - 1].add(jointGroups[i]);
  }

  function bindLinksToJointGroups() {
    if (modelLinks.length < 6) return;
    // 让 attach 基于当前世界位姿重新挂载，避免散架
    modelFrame.updateMatrixWorld(true);
    for (let i = 0; i < 6; i++) {
      jointGroups[i].updateMatrixWorld(true);
    }
    if (modelLinks[0]) modelFrame.attach(modelLinks[0]);
    if (modelLinks[1]) jointGroups[0].attach(modelLinks[1]); // J1
    if (modelLinks[2]) jointGroups[1].attach(modelLinks[2]); // J2
    if (modelLinks[3]) jointGroups[2].attach(modelLinks[3]); // J3
    if (modelLinks[4]) jointGroups[3].attach(modelLinks[4]); // J4
    if (modelLinks[5]) jointGroups[4].attach(modelLinks[5]); // J5/J6 末端段
    twin.linksBound = true;
  }
  const loader = new GLTFLoader();
  let loadedCount = 0;
  for(let i=0;i<6;i++){
    loader.load('/api/twin/links/' + i + '.glb?t=' + Date.now(), (gltf) => {
      const m = gltf.scene;
      m.traverse((obj) => {
        if (obj.isMesh) {
          obj.castShadow = false;
          obj.receiveShadow = false;
          obj.material = new THREE.MeshStandardMaterial({
            color: 0x94a3b8, metalness: 0.2, roughness: 0.72, transparent: false, opacity: 1.0
          });
        }
      });
      // 保持 CAD 原始装配位姿；后续通过矩阵围绕关节轴驱动
      modelFrame.add(m);
      m.matrixAutoUpdate = false;
      m.updateMatrix();
      modelLinks[i] = m;
      m.matrixAutoUpdate = true;
      loadedCount += 1;
      if (loadedCount >= 6) {
        bindLinksToJointGroups();
      }
      const box = document.getElementById('twinState');
      if (box) box.textContent = '状态: 3D模型已加载 ' + loadedCount + '/6';
    }, undefined, (_err) => {});
  }

  twin = {
    scene, camera, renderer, controls,
    joints: [0,0,0,0,0,0],
    rig: [j1,j2,j3,j4,j5,j6],
    modelFrame, modelLinks,
    jointGroups, jointAxisNames, linksBound: false,
    jointPivots, jointAxes, jointSigns,
    THREE,
    ready: true
  };
  const animate = () => {
    if (!twin.ready) return;
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  };
  animate();
  window.addEventListener('resize', () => {
    if(!twin.ready) return;
    const nw = host.clientWidth || 960;
    const nh = host.clientHeight || 420;
    twin.camera.aspect = nw / nh;
    twin.camera.updateProjectionMatrix();
    twin.renderer.setSize(nw, nh);
  });
}

function updateTwinFromJoints(j){
  if(!twin.ready || !twin.THREE || !Array.isArray(j) || j.length !== 6) return;
  const THREE = twin.THREE;
  const v = j.map(x => Number(x) || 0);
  twin.joints = v;
  // 骨架联动（用于调试）
  twin.rig[0].rotation.y = v[0];
  twin.rig[1].rotation.z = v[1];
  twin.rig[2].rotation.z = v[2];
  twin.rig[3].rotation.x = v[3];
  twin.rig[4].rotation.z = v[4];
  twin.rig[5].rotation.x = v[5];

  // 模型联动：关节组层级驱动（避免分段矩阵叠加导致散架）
  if (twin.linksBound && twin.jointGroups && twin.jointGroups.length === 6) {
    for (let i = 0; i < 6; i++) {
      const g = twin.jointGroups[i];
      const axisName = twin.jointAxisNames[i];
      const a = v[i] * twin.jointSigns[i];
      g.rotation.set(0, 0, 0);
      if (axisName === "x") g.rotation.x = a;
      else if (axisName === "y") g.rotation.y = a;
      else g.rotation.z = a;
    }
  }
}
window.updateTwinFromJoints = updateTwinFromJoints;

async function updateTwinState(){
  const box = document.getElementById('twinState');
  if(!robotConnected){
    box.textContent = '状态: 机械臂未连接';
    return;
  }
  try{
    const d = await api('/api/status');
    updateTwinFromJoints(d.joints || []);
    box.textContent = '状态: 已同步 | joints(rad)= ' + JSON.stringify(d.joints || []);
  }catch(e){
    if((e && e.message && e.message.indexOf('机械臂未连接') >= 0) || (e && e.message && e.message.indexOf('400') >= 0)){
      setConnBadge(false);
      box.textContent = '状态: 机械臂未连接';
      return;
    }
    box.textContent = '状态: 读取失败';
  }
}

document.getElementById('joints').addEventListener('change', syncFromInput);
loadPointNames();
syncFromSliders();
loadCameras(); loadMedia(); refreshStatus();
stopCameraStream();
// 数字孪生功能已按需关闭（不影响真实控制与相机能力）

window.connectRobot = connectRobot;
window.disconnectRobot = disconnectRobot;
window.refreshStatus = refreshStatus;
window.movej = movej;
window.savePoint = savePoint;
window.loadPoint = loadPoint;
window.syncFromSliders = syncFromSliders;
window.loadCameras = loadCameras;
window.applyCamera = applyCamera;
window.startCameraStream = startCameraStream;
window.stopCameraStream = stopCameraStream;
window.capturePhoto = capturePhoto;
window.captureVideo = captureVideo;
window.captureDepthPhoto = captureDepthPhoto;
window.captureDepthVideo = captureDepthVideo;
window.loadMedia = loadMedia;
window.delMedia = delMedia;
window.updateTwinState = updateTwinState;
</script>
</body>
</html>
"""


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/api/info")
def get_info():
    robot = core_state.get_robot()
    cam = core_state.get_camera_service()
    return {
        "status": "online",
        "robot_connected": robot.connected if robot else False,
        "robot_ip": robot.current_ip if robot and robot.connected else None,
        "camera_mode": cam.mode_name if cam else None,
        "camera_stream_enabled": _is_camera_stream_enabled(),
    }


@app.post("/api/connect")
def connect_robot(req: ConnectRequest):
    robot = _robot_or_raise()
    success, msg = robot.connect(req.ip, req.port)
    if not success:
        raise HTTPException(status_code=500, detail=f"连接失败: {msg}")
    return {"status": "success", "message": "已成功连接机械臂"}


@app.post("/api/disconnect")
def disconnect_robot():
    robot = _robot_or_raise()
    if robot.connected:
        robot.disconnect()
        return {"status": "success", "message": "已断开连接"}
    return {"status": "ignored", "message": "机械臂本来就没有连接"}


@app.get("/api/status")
def get_robot_status():
    robot = _robot_or_raise()
    if not robot.connected:
        raise HTTPException(status_code=400, detail="机械臂未连接")
    wp = robot.get_waypoint()
    if not wp:
        raise HTTPException(status_code=500, detail="无法读取当前位姿，请检查连接")
    return {
        "connected": True,
        "joints": list(wp.jointpos),
        "pose": {
            "position": {"x": wp.cartPos.x, "y": wp.cartPos.y, "z": wp.cartPos.z},
            "orientation": {"w": wp.orientation.w, "x": wp.orientation.x, "y": wp.orientation.y, "z": wp.orientation.z},
        },
    }


@app.post("/api/movej")
def movej(req: MoveJRequest):
    robot = _robot_or_raise()
    if not robot.connected:
        raise HTTPException(status_code=400, detail="机械臂未连接")
    if len(req.joints) != 6:
        raise HTTPException(status_code=400, detail="必须提供正好 6 个关节的数组")
    success, msg = robot.movej_safe(req.joints)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": "MoveJ 运动完成"}


@app.get("/api/cameras")
def list_cameras():
    cam = _camera_or_raise()
    devices = cam.list_camera_devices()
    return {
        "mode": cam.mode_name,
        "selected_serial": cam.selected_device_serial,
        "devices": [{"index": i, "serial": sn, "label": label} for i, sn, label in devices],
    }


@app.post("/api/cameras/select")
def select_camera(req: CameraSelectRequest):
    cam = _camera_or_raise()
    cam.select_camera_by_serial(req.serial)
    return {"status": "success", "selected_serial": req.serial, "mode": cam.mode_name}


@app.post("/api/camera_stream/toggle")
def toggle_camera_stream(req: StreamToggleRequest):
    _set_camera_stream_enabled(req.enabled)
    return {"status": "success", "enabled": _is_camera_stream_enabled()}


@app.get("/api/camera_stream/state")
def camera_stream_state():
    return {"enabled": _is_camera_stream_enabled()}


@app.get("/api/camera_stream.mjpg")
def camera_stream_mjpg():
    cam = _camera_or_raise()
    if not _is_camera_stream_enabled():
        raise HTTPException(status_code=400, detail="实时相机流未开启")

    def _gen():
        pipeline = cam._create_pipeline()
        try:
            while _is_camera_stream_enabled():
                frame = cam._try_get_pyorbbec_frame(pipeline, timeout_ms=80)
                if frame is None:
                    continue
                ok, buf = cam.cv2.imencode(".jpg", frame, [int(cam.cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    continue
                jpg = buf.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                )
        finally:
            try:
                pipeline.stop()
            except Exception:
                pass

    return StreamingResponse(_gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/capture/photo")
def capture_photo():
    cam = _camera_or_raise()
    store = _media_store_or_raise()
    file_path, w, h = cam.capture_photo(store.media_dir)
    store.add_record("photo", file_path, duration_sec=0, width=w, height=h, fps=0)
    return {"status": "success", "file_path": file_path, "width": w, "height": h}


@app.post("/api/capture/video")
def capture_video(req: CaptureVideoRequest):
    cam = _camera_or_raise()
    store = _media_store_or_raise()
    sec = max(1, min(60, int(req.duration_sec)))
    file_path, w, h, real_duration, real_fps = cam.capture_video(store.media_dir, duration_sec=sec, target_fps=20)
    store.add_record("video", file_path, duration_sec=real_duration, width=w, height=h, fps=real_fps)
    return {
        "status": "success",
        "file_path": file_path,
        "width": w,
        "height": h,
        "duration_sec": real_duration,
        "fps": real_fps,
    }


@app.post("/api/capture/depth_photo")
def capture_depth_photo():
    cam = _camera_or_raise()
    store = _media_store_or_raise()
    file_path, w, h, hint = cam.capture_depth_photo(store.media_dir)
    store.add_record("depth_photo", file_path, duration_sec=0, width=w, height=h, fps=0, extra_info=hint)
    return {"status": "success", "file_path": file_path, "width": w, "height": h, "extra_info": hint}


@app.post("/api/capture/depth_video")
def capture_depth_video(req: CaptureVideoRequest):
    cam = _camera_or_raise()
    store = _media_store_or_raise()
    sec = max(1, min(60, int(req.duration_sec)))
    file_path, w, h, real_duration, real_fps, hint = cam.capture_depth_video(
        store.media_dir, duration_sec=sec, target_fps=30
    )
    store.add_record(
        "depth_video",
        file_path,
        duration_sec=real_duration,
        width=w,
        height=h,
        fps=real_fps,
        extra_info=hint,
    )
    return {
        "status": "success",
        "file_path": file_path,
        "width": w,
        "height": h,
        "duration_sec": real_duration,
        "fps": real_fps,
        "extra_info": hint,
    }


@app.get("/api/media")
def list_media():
    store = _media_store_or_raise()
    items = []
    for rec in store.list_records(limit=200):
        rec_id, media_type, file_path, duration_sec, width, height, fps, extra_info, created_at = rec
        items.append(
            {
                "id": rec_id,
                "media_type": media_type,
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "duration_sec": duration_sec,
                "width": width,
                "height": height,
                "fps": fps,
                "extra_info": extra_info,
                "created_at": created_at,
            }
        )
    return {"items": items}


@app.get("/api/media/{record_id}/file")
def open_media_file(record_id: int):
    store = _media_store_or_raise()
    for rec in store.list_records(limit=500):
        if rec[0] == record_id:
            file_path = rec[2]
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="媒体文件不存在")
            return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="媒体记录不存在")


@app.delete("/api/media/{record_id}")
def delete_media(record_id: int):
    store = _media_store_or_raise()
    store.delete_record(record_id)
    return {"status": "success", "message": f"已删除记录 {record_id}"}


@app.get("/api/twin/step")
def get_twin_step():
    step_path = _resource_path("assets", "i10H.STEP")
    if not os.path.exists(step_path):
        step_path = r"d:\aubo\i10H.STEP"
    if os.path.exists(step_path):
        return FileResponse(
            step_path,
            media_type="application/octet-stream",
            filename="i10H.STEP",
        )
    # 兜底：无外部 STEP 时返回内置占位 STEP，保证 exe 单文件可运行。
    embedded_step = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('AUBO_EMBEDDED_STEP_PLACEHOLDER'),'2;1');
FILE_NAME('AUBO_I10_EMBEDDED.STEP','2026-01-01T00:00:00',('AUBO'),('AUBO'),'','','');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;
DATA;
ENDSEC;
END-ISO-10303-21;"""
    return Response(
        content=embedded_step,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=i10H_embedded_placeholder.STEP"},
    )


@app.get("/api/twin/model.glb")
def get_twin_glb():
    glb_path = _resource_path("assets", "i10H.glb")
    if not os.path.exists(glb_path):
        raise HTTPException(status_code=404, detail="GLB 模型不存在，请先执行 STEP 转换并重新打包")
    return FileResponse(
        glb_path,
        media_type="model/gltf-binary",
        filename="i10H.glb",
    )


@app.get("/api/twin/links/{idx}.glb")
def get_twin_link_glb(idx: int):
    if idx < 0 or idx > 6:
        raise HTTPException(status_code=400, detail="非法 link 索引")
    link_path = _resource_path("assets", "twin_links", f"link{idx}.glb")
    if not os.path.exists(link_path):
        raise HTTPException(status_code=404, detail="link 模型不存在")
    return FileResponse(
        link_path,
        media_type="model/gltf-binary",
        filename=f"link{idx}.glb",
    )


@app.get("/static/three/{file_path:path}")
def get_three_static(file_path: str):
    safe_rel = os.path.normpath(file_path).replace("\\", "/")
    if safe_rel.startswith("../") or safe_rel.startswith("..\\"):
        raise HTTPException(status_code=400, detail="非法路径")
    static_root = _resource_path("static", "three")
    abs_path = os.path.normpath(os.path.join(static_root, safe_rel))
    if not abs_path.startswith(os.path.normpath(static_root)):
        raise HTTPException(status_code=400, detail="非法路径")
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="静态资源不存在")
    if abs_path.endswith(".js"):
        media_type = "text/javascript; charset=utf-8"
    else:
        media_type = "application/octet-stream"
    return FileResponse(abs_path, media_type=media_type)
