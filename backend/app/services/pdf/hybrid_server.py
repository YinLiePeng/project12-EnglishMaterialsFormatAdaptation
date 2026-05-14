"""Hybrid PDF Server 管理器

负责在应用生命周期内管理 opendataloader-pdf-hybrid 服务器进程。
提供启动、停止、健康检查、懒加载等功能。
"""

import subprocess
import time
import signal
import os
import requests
import threading
from pathlib import Path
from typing import Optional
from enum import Enum

from app.core.config import settings


class HybridServerStatus(str, Enum):
    """Hybrid Server 状态"""
    RUNNING = "running"           # 运行中且健康
    STARTING = "starting"         # 启动中
    STOPPED = "stopped"           # 已停止
    NOT_INSTALLED = "not_installed"  # 未安装
    ERROR = "error"               # 出错


class HybridServerManager:
    """Hybrid Server 管理器

    支持两种启动方式：
    1. 预启动：应用启动时自动启动（需设置 HYBRID_SERVER_ENABLED=True）
    2. 懒加载：首次需要时自动启动（推荐，节省启动时间）
    """

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.server_url = f"http://{settings.HYBRID_SERVER_HOST}:{settings.HYBRID_SERVER_PORT}"
        self._is_available = False
        self._status = HybridServerStatus.STOPPED
        self._lock = threading.Lock()
        self._start_error: Optional[str] = None

    def start(self) -> bool:
        """启动 hybrid server（同步阻塞，适用于预启动）

        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            return self._do_start()

    def _do_start(self) -> bool:
        """内部启动逻辑（需在锁内调用）"""
        # 已经运行中
        if self._check_existing_server():
            self._is_available = True
            self._status = HybridServerStatus.RUNNING
            return True

        self._status = HybridServerStatus.STARTING
        self._start_error = None

        try:
            # 构建启动命令
            cmd = [
                "opendataloader-pdf-hybrid",
                "--host", settings.HYBRID_SERVER_HOST,
                "--port", str(settings.HYBRID_SERVER_PORT),
                "--log-level", settings.HYBRID_SERVER_LOG_LEVEL,
            ]

            print(f"🚀 启动 Hybrid server: {' '.join(cmd)}")

            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )

            # 等待服务就绪
            if self._wait_for_ready():
                print(f"✅ Hybrid server 启动成功 ({self.server_url})")
                self._is_available = True
                self._status = HybridServerStatus.RUNNING
                return True
            else:
                print("❌ Hybrid server 启动超时")
                self._start_error = "启动超时"
                self._do_stop()
                self._status = HybridServerStatus.ERROR
                return False

        except FileNotFoundError:
            error_msg = "未找到 opendataloader-pdf-hybrid 命令，请确认已安装: pip install 'opendataloader-pdf[hybrid]'"
            print(f"❌ {error_msg}")
            self._start_error = error_msg
            self._status = HybridServerStatus.NOT_INSTALLED
            return False
        except Exception as e:
            error_msg = f"启动失败: {str(e)}"
            print(f"❌ {error_msg}")
            self._start_error = error_msg
            self._status = HybridServerStatus.ERROR
            return False

    def lazy_start(self) -> bool:
        """懒加载启动（线程安全，非阻塞检查 + 同步启动）

        如果 server 已经在运行，立即返回 True。
        如果未运行，尝试启动并等待就绪。

        Returns:
            bool: 是否可用
        """
        with self._lock:
            # 快速路径：已经在运行
            if self._is_available and self._check_health():
                return True

            # 尝试启动
            return self._do_start()

    def stop(self):
        """停止 hybrid server（线程安全）"""
        with self._lock:
            self._do_stop()

    def _do_stop(self):
        """内部停止逻辑（需在锁内调用）"""
        if self.process:
            try:
                if os.name != 'nt':
                    # Unix: 发送信号到进程组
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    # Windows: 终止进程
                    self.process.terminate()

                # 等待进程结束
                self.process.wait(timeout=5)
                print("🛑 Hybrid server 已停止")
            except subprocess.TimeoutExpired:
                # 强制终止
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
                print("🛑 Hybrid server 已强制停止")
            except Exception as e:
                print(f"⚠️ 停止 Hybrid server 时出错: {e}")
            finally:
                self.process = None
                self._is_available = False
                self._status = HybridServerStatus.STOPPED

    def is_available(self) -> bool:
        """检查 hybrid server 是否可用

        Returns:
            bool: 是否可用
        """
        if not self._is_available:
            self._is_available = self._check_health()
        return self._is_available

    def get_status(self) -> dict:
        """获取 hybrid server 详细状态

        Returns:
            dict: 状态信息
        """
        health = self._check_health()

        # 如果 health 为真但状态不是 RUNNING，更新状态
        if health and self._status != HybridServerStatus.RUNNING:
            self._status = HybridServerStatus.RUNNING
            self._is_available = True

        # 如果 health 为假但之前认为是 RUNNING，更新状态
        if not health and self._status == HybridServerStatus.RUNNING:
            self._status = HybridServerStatus.STOPPED
            self._is_available = False

        return {
            "status": self._status.value,
            "available": health,
            "server_url": self.server_url,
            "error": self._start_error,
            "pre_start_enabled": settings.HYBRID_SERVER_ENABLED,
        }

    def _check_existing_server(self) -> bool:
        """检查是否已有 server 在运行"""
        return self._check_health()

    def _check_health(self) -> bool:
        """健康检查

        Returns:
            bool: 是否健康
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def _wait_for_ready(self) -> bool:
        """等待服务就绪

        Returns:
            bool: 是否在超时前就绪
        """
        start_time = time.time()
        timeout = settings.HYBRID_SERVER_TIMEOUT

        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            time.sleep(1)

        return False


# 全局管理器实例
hybrid_server_manager = HybridServerManager()
