"""UDP通信模块"""

import ctypes
import socket
from typing import Optional, Tuple

from utils import UDP_TIMEOUT, get_logger

from .structs import Command, CommandHead

logger = get_logger(__name__)


class UDPCommunicator:
    """UDP通信管理类 - 负责底层UDP数据收发"""

    def __init__(
        self,
        motion_host: str,
        motion_port: int,
        perception_host: str,
        receive_port: int,
    ):
        """
        初始化UDP通信

        Args:
            motion_host: 运动主机IP地址
            motion_port: 运动主机端口
            perception_host: 感知主机IP地址
            receive_port: 本地接收端口(用于接收机器人上报的状态数据)
        """
        self.motion_host = motion_host
        self.motion_port = motion_port
        self.perception_host = perception_host
        self.receive_port = receive_port

        # 创建UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(UDP_TIMEOUT)

        # 用于接收数据的socket
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receive_socket.settimeout(UDP_TIMEOUT)
        try:
            self.receive_socket.bind(("", receive_port))
            logger.info(
                f"UDP通信初始化完成: 运动主机={motion_host}:{motion_port}, 接收端口={receive_port}"
            )
        except Exception as e:
            logger.error(f"绑定接收端口{receive_port}失败: {e}")

    def send_simple_command(
        self,
        code: int,
        value: int = 0,
        target_host: Optional[str] = None,
        target_port: Optional[int] = None,
    ) -> bool:
        """
        发送简单指令

        Args:
            code: 指令码
            value: 指令值
            target_host: 目标主机(默认为运动主机)
            target_port: 目标端口(默认为运动主机端口)

        Returns:
            发送是否成功
        """
        try:
            cmd = CommandHead()
            cmd.code = code
            cmd.parameters_size = value
            cmd.type = 0  # 简单指令

            host = target_host or self.motion_host
            port = target_port or self.motion_port

            data = bytes(cmd)
            self.socket.sendto(data, (host, port))

            logger.debug(
                f"发送简单指令: code=0x{code:08X}, value={value} -> {host}:{port}"
            )
            return True

        except Exception as e:
            logger.error(f"发送简单指令失败: {e}")
            return False

    def send_complex_command(
        self,
        code: int,
        data_struct: ctypes.Structure,
        target_host: Optional[str] = None,
        target_port: Optional[int] = None,
    ) -> bool:
        """
        发送复杂指令

        Args:
            code: 指令码
            data_struct: 数据结构体
            target_host: 目标主机
            target_port: 目标端口

        Returns:
            发送是否成功
        """
        try:
            cmd = Command()
            cmd.head.code = code
            cmd.head.parameters_size = ctypes.sizeof(data_struct)
            cmd.head.type = 1  # 复杂指令

            # 复制数据
            data_bytes = bytes(data_struct)
            ctypes.memmove(ctypes.addressof(cmd.data), data_bytes, len(data_bytes))

            host = target_host or self.motion_host
            port = target_port or self.motion_port

            # 只发送头部和实际数据
            total_size = ctypes.sizeof(cmd.head) + cmd.head.parameters_size
            data = bytes(cmd)[:total_size]
            self.socket.sendto(data, (host, port))

            logger.debug(
                f"发送复杂指令: code=0x{code:08X}, size={cmd.head.parameters_size} -> {host}:{port}"
            )
            return True

        except Exception as e:
            logger.error(f"发送复杂指令失败: {e}")
            return False

    def receive_simple_cmd_response(self) -> Optional[CommandHead]:
        """
        接收简单指令
        Returns:
            指令头 或 None
        """
        try:
            data, _addr = self.socket.recvfrom(ctypes.sizeof(CommandHead))
            if len(data) < ctypes.sizeof(CommandHead):
                logger.warning("接收数据长度不足")
                return None
            # 解析指令头
            head = CommandHead.from_buffer_copy(data)
            logger.debug(
                f"接收简单指令: code=0x{head.code:08X}, type={head.type}, size={head.parameters_size}"
            )
            return head
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"接收简单指令失败: {e}")
            return None

    def receive_data(
        self, buffer_size: int = 4096
    ) -> Optional[Tuple[CommandHead, bytes]]:
        """
        接收UDP数据

        Args:
            buffer_size: 接收缓冲区大小

        Returns:
            (指令头, 数据字节) 或 None
        """
        _logger = get_logger(__name__)
        try:
            data, _addr = self.receive_socket.recvfrom(buffer_size)

            if len(data) < ctypes.sizeof(CommandHead):
                _logger.warning("接收数据长度不足")
                return None

            # 解析指令头
            head = CommandHead.from_buffer_copy(data[: ctypes.sizeof(CommandHead)])

            # 提取数据部分
            data_part = data[ctypes.sizeof(CommandHead) :]

            # _logger.info(
            #     f"接收数据: code=0x{head.code:08X}, type={head.type}, size={len(data_part)}"
            # )
            return (head, data_part)

        except socket.timeout:
            return None
        except Exception as e:
            _logger.error(f"接收数据失败: {e}")
            return None

    def close(self):
        """关闭socket连接"""
        try:
            self.socket.close()
            self.receive_socket.close()
            logger.info("UDP连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")
