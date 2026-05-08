import os
import sqlite3
import time
from datetime import datetime


class CameraFeatureError(Exception):
    pass


class MediaStore:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.media_dir = os.path.join(base_dir, "media")
        os.makedirs(self.media_dir, exist_ok=True)
        self.db_path = os.path.join(base_dir, "media.db")
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    duration_sec INTEGER DEFAULT 0,
                    width INTEGER DEFAULT 0,
                    height INTEGER DEFAULT 0,
                    fps REAL DEFAULT 0,
                    extra_info TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            # 兼容旧版本数据库：缺列时自动补齐
            cur = conn.execute("PRAGMA table_info(media_records)")
            cols = [row[1] for row in cur.fetchall()]
            if "extra_info" not in cols:
                conn.execute("ALTER TABLE media_records ADD COLUMN extra_info TEXT DEFAULT ''")
            conn.commit()
        finally:
            conn.close()

    def add_record(self, media_type, file_path, duration_sec=0, width=0, height=0, fps=0, extra_info=""):
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO media_records(media_type, file_path, duration_sec, width, height, fps, extra_info, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_type,
                    file_path,
                    int(duration_sec),
                    int(width),
                    int(height),
                    float(fps),
                    str(extra_info or ""),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_records(self, limit=100):
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT id, media_type, file_path, duration_sec, width, height, fps, extra_info, created_at
                FROM media_records
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    def delete_record(self, record_id):
        conn = self._connect()
        try:
            cur = conn.execute("SELECT file_path FROM media_records WHERE id=?", (record_id,))
            row = cur.fetchone()
            if row and os.path.exists(row[0]):
                try:
                    os.remove(row[0])
                except OSError:
                    pass
            conn.execute("DELETE FROM media_records WHERE id=?", (record_id,))
            conn.commit()
        finally:
            conn.close()


class OrbbecCameraService:
    def __init__(self):
        import importlib.util
        import cv2
        import numpy as np

        self.cv2 = cv2
        self.np = np
        self.mode_name = "pyorbbecsdk"
        self.ob = None
        self.use_pyorbbec = True
        self.camera_index = 0
        self.selected_device_serial = None

        # 强制 pyorbbecsdk 模式：不可用则直接报错
        try:
            import pyorbbecsdk as ob  # type: ignore
            self.ob = ob
        except Exception as e:
            spec = importlib.util.find_spec("pyorbbecsdk")
            if spec is None:
                raise CameraFeatureError(
                    "未检测到 pyorbbecsdk。请安装官方 Windows 版包，并完成 obsensor metadata 注册。"
                ) from e
            raise CameraFeatureError(
                f"pyorbbecsdk 导入失败: {e}。请确认安装的是 Windows 版（非 darwin/linux），并执行 metadata 注册脚本。"
            ) from e

    def list_camera_devices(self):
        devices = []
        try:
            ctx = self.ob.Context()
            dev_list = ctx.query_devices()
            count = dev_list.get_count()
            for i in range(count):
                dev = dev_list.get_device_by_index(i)
                info = dev.get_device_info()
                name = ""
                sn = ""
                try:
                    name = info.get_name()
                except Exception:
                    name = "OrbbecDevice"
                try:
                    sn = info.get_serial_number()
                except Exception:
                    sn = f"index_{i}"
                label = f"{name} ({sn})"
                devices.append((i, sn, label))
        except Exception:
            pass
        return devices

    def select_camera_by_serial(self, serial: str):
        self.selected_device_serial = serial
        if serial:
            self.mode_name = f"pyorbbecsdk[{serial}]"
        else:
            self.mode_name = "pyorbbecsdk"

    def _create_pipeline(self):
        ob = self.ob
        pipeline = ob.Pipeline()
        config = ob.Config()
        if self.selected_device_serial:
            try:
                if hasattr(config, "set_device_serial_number"):
                    config.set_device_serial_number(self.selected_device_serial)
                elif hasattr(config, "enable_device"):
                    config.enable_device(self.selected_device_serial)
            except Exception:
                pass
        profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
        profile = profiles.get_default_video_stream_profile()
        config.enable_stream(profile)
        pipeline.start(config)
        return pipeline

    def _create_depth_pipeline(self):
        ob = self.ob
        pipeline = ob.Pipeline()
        config = ob.Config()
        if self.selected_device_serial:
            try:
                if hasattr(config, "set_device_serial_number"):
                    config.set_device_serial_number(self.selected_device_serial)
                elif hasattr(config, "enable_device"):
                    config.enable_device(self.selected_device_serial)
            except Exception:
                pass
        depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
        depth_profile = depth_profiles.get_default_video_stream_profile()
        config.enable_stream(depth_profile)
        # 如果有彩色流，就并行打开，便于 RGBD 同屏
        try:
            color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
            color_profile = color_profiles.get_default_video_stream_profile()
            config.enable_stream(color_profile)
        except Exception:
            pass
        pipeline.start(config)
        return pipeline

    def _to_bgr(self, color_frame):
        ob = self.ob
        cv2 = self.cv2
        np = self.np

        width = color_frame.get_width()
        height = color_frame.get_height()
        fmt = color_frame.get_format()
        data = np.frombuffer(color_frame.get_data(), dtype=np.uint8)

        # 常见格式兼容
        if fmt == ob.OBFormat.BGR:
            return data.reshape((height, width, 3))
        if fmt == ob.OBFormat.RGB:
            rgb = data.reshape((height, width, 3))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if fmt == ob.OBFormat.YUYV:
            yuyv = data.reshape((height, width, 2))
            return cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2)
        if fmt == ob.OBFormat.NV12:
            nv12 = data.reshape((height * 3 // 2, width))
            return cv2.cvtColor(nv12, cv2.COLOR_YUV2BGR_NV12)
        if fmt == ob.OBFormat.MJPG:
            return cv2.imdecode(data, cv2.IMREAD_COLOR)

        raise CameraFeatureError(f"暂不支持的颜色格式: {fmt}")

    def _wait_color_bgr(self, pipeline, retry=80):
        for _ in range(retry):
            frames = pipeline.wait_for_frames(100)
            if frames is None:
                continue
            color = frames.get_color_frame()
            if color is None:
                continue
            frame = self._to_bgr(color)
            if frame is not None:
                return frame
        raise CameraFeatureError("未获取到有效彩色帧，请检查相机连接和驱动。")

    def _try_get_pyorbbec_frame(self, pipeline, timeout_ms=40):
        frames = pipeline.wait_for_frames(timeout_ms)
        if frames is None:
            return None
        color = frames.get_color_frame()
        if color is None:
            return None
        return self._to_bgr(color)

    def _depth_frame_to_mm(self, depth_frame):
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        data = self.np.frombuffer(depth_frame.get_data(), dtype=self.np.uint16)
        if data.size != width * height:
            raise CameraFeatureError("深度帧数据尺寸异常。")
        depth_mm = data.reshape((height, width))
        return depth_mm

    def _render_depth_with_hint(self, depth_mm):
        cv2 = self.cv2
        np = self.np
        valid = depth_mm > 0
        if not np.any(valid):
            raise CameraFeatureError("深度帧无有效数据。")

        valid_mm = depth_mm[valid]
        dmin = int(np.min(valid_mm))
        dmax = int(np.max(valid_mm))
        center_mm = int(depth_mm[depth_mm.shape[0] // 2, depth_mm.shape[1] // 2])

        lo = int(np.percentile(valid_mm, 2))
        hi = int(np.percentile(valid_mm, 98))
        if hi <= lo:
            hi = lo + 1

        clipped = np.clip(depth_mm, lo, hi)
        norm = ((clipped - lo) * (255.0 / (hi - lo))).astype(np.uint8)
        depth_vis = cv2.applyColorMap(norm, cv2.COLORMAP_TURBO)
        depth_vis[~valid] = (0, 0, 0)

        hint = f"Depth(mm) Min:{dmin} Max:{dmax} Center:{center_mm}"
        cv2.putText(depth_vis, hint, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(depth_vis, hint, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1, cv2.LINE_AA)
        return depth_vis, hint

    def _try_get_depth_vis(self, pipeline, timeout_ms=40):
        if not self.use_pyorbbec:
            return None, None
        frames = pipeline.wait_for_frames(timeout_ms)
        if frames is None:
            return None, None
        depth_frame = frames.get_depth_frame()
        if depth_frame is None:
            return None, None
        depth_mm = self._depth_frame_to_mm(depth_frame)
        depth_vis, hint = self._render_depth_with_hint(depth_mm)
        return depth_vis, hint

    def capture_photo(self, output_dir):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"photo_{ts}.png")
        pipeline = self._create_pipeline()
        try:
            frame = self._wait_color_bgr(pipeline)
            ok = self.cv2.imwrite(file_path, frame)
            if not ok:
                raise CameraFeatureError("保存图片失败。")
            h, w = frame.shape[:2]
            return file_path, w, h
        finally:
            try:
                pipeline.stop()
            except Exception:
                pass

    def capture_video(self, output_dir, duration_sec=3, target_fps=30):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"video_{duration_sec}s_{ts}.mp4")
        writer = None
        frame_count = 0
        started_at = time.monotonic()

        pipeline = self._create_pipeline()
        try:
            # 先拿到第一帧，避免写入器尺寸不确定
            first = None
            warmup_deadline = time.monotonic() + 2.0
            while first is None and time.monotonic() < warmup_deadline:
                first = self._try_get_pyorbbec_frame(pipeline, timeout_ms=40)
            if first is None:
                raise CameraFeatureError("未获取到首帧，录像启动失败。")

            h, w = first.shape[:2]
            fourcc = self.cv2.VideoWriter_fourcc(*"mp4v")
            writer = self.cv2.VideoWriter(file_path, fourcc, float(target_fps), (w, h))
            if not writer.isOpened():
                raise CameraFeatureError("视频写入器初始化失败。")

            writer.write(first)
            frame_count += 1
            end_at = started_at + float(duration_sec)
            while time.monotonic() < end_at:
                frame = self._try_get_pyorbbec_frame(pipeline, timeout_ms=40)
                if frame is None:
                    continue
                writer.write(frame)
                frame_count += 1
            elapsed = max(0.001, time.monotonic() - started_at)
            actual_duration = max(1, int(round(elapsed)))
            actual_fps = frame_count / elapsed
            return file_path, w, h, actual_duration, actual_fps
        finally:
            if writer is not None:
                writer.release()
            try:
                pipeline.stop()
            except Exception:
                pass

    def capture_depth_photo(self, output_dir):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"depth_{ts}.png")

        pipeline = self._create_depth_pipeline()
        try:
            frame = None
            hint = ""
            deadline = time.monotonic() + 2.0
            while frame is None and time.monotonic() < deadline:
                frame, hint = self._try_get_depth_vis(pipeline, timeout_ms=40)
            if frame is None:
                raise CameraFeatureError("未获取到有效深度帧。")
            ok = self.cv2.imwrite(file_path, frame)
            if not ok:
                raise CameraFeatureError("保存深度图片失败。")
            h, w = frame.shape[:2]
            return file_path, w, h, hint
        finally:
            try:
                pipeline.stop()
            except Exception:
                pass

    def capture_depth_video(self, output_dir, duration_sec=3, target_fps=30):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"depth_{duration_sec}s_{ts}.mp4")

        pipeline = self._create_depth_pipeline()
        writer = None
        frame_count = 0
        started_at = time.monotonic()
        last_hint = ""
        try:
            first = None
            deadline = time.monotonic() + 2.0
            while first is None and time.monotonic() < deadline:
                first, last_hint = self._try_get_depth_vis(pipeline, timeout_ms=40)
            if first is None:
                raise CameraFeatureError("未获取到首帧深度数据，录像启动失败。")

            h, w = first.shape[:2]
            fourcc = self.cv2.VideoWriter_fourcc(*"mp4v")
            writer = self.cv2.VideoWriter(file_path, fourcc, float(target_fps), (w, h))
            if not writer.isOpened():
                raise CameraFeatureError("深度视频写入器初始化失败。")
            writer.write(first)
            frame_count += 1

            end_at = started_at + float(duration_sec)
            while time.monotonic() < end_at:
                frame, hint = self._try_get_depth_vis(pipeline, timeout_ms=40)
                if frame is None:
                    continue
                last_hint = hint or last_hint
                writer.write(frame)
                frame_count += 1

            elapsed = max(0.001, time.monotonic() - started_at)
            actual_duration = max(1, int(round(elapsed)))
            actual_fps = frame_count / elapsed
            return file_path, w, h, actual_duration, actual_fps, last_hint
        finally:
            if writer is not None:
                writer.release()
            try:
                pipeline.stop()
            except Exception:
                pass

    def play_media(self, file_path):
        cv2 = self.cv2
        if not os.path.exists(file_path):
            raise CameraFeatureError("文件不存在。")

        ext = os.path.splitext(file_path)[1].lower()
        win_name = f"MediaPlayer - {os.path.basename(file_path)}"

        if ext in (".png", ".jpg", ".jpeg", ".bmp"):
            img = cv2.imread(file_path)
            if img is None:
                raise CameraFeatureError("图片读取失败。")
            cv2.imshow(win_name, img)
            cv2.waitKey(0)
            cv2.destroyWindow(win_name)
            return

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise CameraFeatureError("视频打开失败。")
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                cv2.imshow(win_name, frame)
                key = cv2.waitKey(30) & 0xFF
                if key in (27, ord("q")):
                    break
            cv2.destroyWindow(win_name)
        finally:
            cap.release()
