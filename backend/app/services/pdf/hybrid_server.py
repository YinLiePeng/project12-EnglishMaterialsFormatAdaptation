"""Hybrid PDF Server 管理器

负责在应用生命周期内管理 opendataloader-pdf-hybrid 服务器进程。
提供启动、停止、健康检查等功能。
"""

import subprocess
import time
import signal
import os
import requests
from pathlib import Path
from typing import Optional

from app.core.config import settings


class HybridServerManager:
    """Hybrid Server 管理器"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.server_url = f"http://{settings.HYBRID_SERVER_HOST}:{settings.HYBRID_SERVER_PORT}"
        self._is_available = False

    def start(self) -> bool:
        """启动 hybrid server

        Returns:
            bool: 是否成功启动
        """
        if not settings.HYBRID_SERVER_ENABLED:
            print("⚠️ Hybrid server 已禁用 (HYBRID_SERVER_ENABLED=False)")
            return False

        # 检查是否已经有实例在运行
        if self._check_existing_server():
            print(f"✅ Hybrid server 已在运行 ({self.server_url})")
            self._is_available = True
            return True

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
                return True
            else:
                print("❌ Hybrid server 启动超时")
                self.stop()
                return False

        except FileNotFoundError:
            print("❌ 未找到 opendataloader-pdf-hybrid 命令，请确认已安装: pip install 'opendataloader-pdf[hybrid]'")
            return False
        except Exception as e:
            print(f"❌ 启动 Hybrid server 失败: {e}")
            return False

    def stop(self):
        """停止 hybrid server"""
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

    def is_available(self) -> bool:
        """检查 hybrid server 是否可用

        Returns:
            bool: 是否可用
        """
        if not self._is_available:
            self._is_available = self._check_health()
        return self._is_available

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
