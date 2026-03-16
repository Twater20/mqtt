"""执行状态管理器"""

import threading
from datetime import datetime
from typing import Any, Dict

from .constants import STATUS_FAILED, STATUS_IDLE, STATUS_RUNNING, STATUS_SUCCESS


class ExecutionStatusManager:
    """命令执行状态管理器"""

    def __init__(self):
        """初始化状态管理器"""
        self.status = {
            "current_command_type": None,
            "current_command": None,
            "status": STATUS_IDLE,
            "message": "",
            "timestamp": None,
        }
        self.lock = threading.Lock()

    def start_execution(self, command_type: str, command: str):
        """开始执行命令"""
        with self.lock:
            self.status["current_command_type"] = command_type
            self.status["current_command"] = command
            self.status["status"] = STATUS_RUNNING
            self.status["timestamp"] = datetime.now().isoformat()
            self.status["message"] = ""

    def complete_execution(self, success: bool, message: str = ""):
        """完成命令执行"""
        with self.lock:
            self.status["status"] = STATUS_SUCCESS if success else STATUS_FAILED
            self.status["message"] = message

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self.lock:
            return self.status.copy()

    def reset(self):
        """重置状态"""
        with self.lock:
            self.status["current_command_type"] = None
            self.status["current_command"] = None
            self.status["status"] = STATUS_IDLE
            self.status["message"] = ""
            self.status["timestamp"] = None
