"""UDP控制器模块 - 封装所有UDP指令"""

import ctypes
import threading
import time
from typing import Optional

from utils import get_logger
from utils.constants import HEARTBEAT_RATE

from .cmd_code import (
    BASIC_STATE_REVERSE,
    BODY_HEIGHT,
    CONTROL_STATE_REVERSE,
    GAIT_MODE,
    GAIT_STATE_REVERSE,
    TERRAIN_BRAKE_MODE,
    TERRAIN_MODE,
    TERRAIN_OBSTACLE_THRESHOLD,
    TERRAIN_VEL_SOURCE,
    CommandCode,
)
from .communicator import UDPCommunicator
from .structs import (
    BatterySensorData,
    ControllerSafeData,
    ControllerSensorData,
    MotionStateData,
    RcsData,
)

logger = get_logger(__name__)


class RobotDogUDPController:
    """机器狗UDP控制器 - 封装所有UDP指令"""

    def __init__(self, communicator: UDPCommunicator):
        """
        初始化控制器

        Args:
            communicator: UDP通信器实例
        """
        self.comm = communicator

        self.heartbeat_thread = None
        self.heartbeat_running = False

        self.state_update_thread = None
        self.state_update_running = False

        self.robot_state = {
            "basic_state": None,
            "gait_state": None,
            "control_mode": None,
            "battery_level": 0,           # 剩余百分比 (%)
            "battery_voltage": 0.0,       # 电压 (V)
            "battery_cycles": 0.0,       # 循环次数 (A)
            "remaining_capacity": 0.0,    # 剩余容量 (Ah)
            "nominal_capacity": 0.0,      # 标称容量 (Ah)
            "odometry_world": None,
            "body_height": None,
            "imu": None,
            "motor_temperature": [0.0] * 12,
            "cpu_temperature": 0.0,
            "cpu_frequency": 0.0,
            "firmware_version": "1.0.0",
        }

    def start_udp_controller(self):
        """启动UDP控制器相关功能"""
        self._start_heartbeat()
        self._start_state_update()
        logger.info("UDP控制器已启动")

    def stop_udp_controller(self):
        """停止UDP控制器相关功能"""
        self._stop_heartbeat()
        self._stop_state_update()
        logger.info("UDP控制器已停止")

    # 机器狗消息更新部分
    def get_robot_state(self) -> dict:
        """获取当前机器狗状态"""
        logger.info(f"udp当前机器狗状态: {self.robot_state}")
        return self.robot_state.copy()

    def _start_state_update(self):
        """启动状态更新线程"""
        self.state_update_running = True
        self.state_update_thread = threading.Thread(
            target=self._state_update_loop, daemon=True
        )
        self.state_update_thread.start()
        logger.info("状态更新线程已启动")

    def _stop_state_update(self):
        """停止状态更新线程"""
        self.state_update_running = False
        if self.state_update_thread:
            self.state_update_thread.join(timeout=2.0)
        logger.info("状态更新线程已停止")

    def _state_update_loop(self):
        """状态更新循环"""
        while self.state_update_running:
            result = self.comm.receive_data()
            if result:
                head, data = result
                # ==== 新增：打印未经解析的原始 UDP 报文信息 ====
                # logger.info(f"[Raw UDP Data] Code: 0x{head.code:08X}, Size: {len(data)} bytes, Hex: {data.hex().upper()}")

                if head.code == CommandCode.RECEIVE_RCS_DATA:
                    if len(data) >= ctypes.sizeof(RcsData):
                        rcs_data = RcsData.from_buffer_copy(data)
                        is_nav = rcs_data.rcs_state[0]
                        self.robot_state["control_mode"] = CONTROL_STATE_REVERSE.get(
                            is_nav
                        )

                elif head.code == CommandCode.RECEIVE_MOTION_STATE:
                    if len(data) >= ctypes.sizeof(MotionStateData):
                        motion_state = MotionStateData.from_buffer_copy(data)
                        self.robot_state["basic_state"] = BASIC_STATE_REVERSE[
                            motion_state.basic_state
                        ]
                        self.robot_state["gait_state"] = GAIT_STATE_REVERSE[
                            motion_state.gait_state
                        ]
                        self.robot_state["odometry_world"] = {
                            "position": {
                                "x": motion_state.leg_odom_pos[0],
                                "y": motion_state.leg_odom_pos[1],
                                "yaw": motion_state.leg_odom_pos[2],
                            },
                            "velocity": {
                                "x": motion_state.leg_odom_vel[0],
                                "y": motion_state.leg_odom_vel[1],
                                "yaw": motion_state.leg_odom_vel[2],
                            },
                            "distance": motion_state.robot_distance,
                        }

                elif head.code == CommandCode.RECEIVE_BATTERY:
                    if len(data) >= ctypes.sizeof(BatterySensorData):
                        battery_data = BatterySensorData.from_buffer_copy(data)
                        self.robot_state["battery_level"] = battery_data.battery_level
                        self.robot_state["battery_voltage"] = battery_data.voltage
                        self.robot_state["battery_current"] = battery_data.current
                        self.robot_state["battery_cycles"] = battery_data.cycles
                        self.robot_state["battery_protected"] = battery_data.protected_state

                elif head.code == CommandCode.RECEIVE_SENSOR_DATA:
                    if len(data) >= ctypes.sizeof(ControllerSensorData):
                        sensor_data = ControllerSensorData.from_buffer_copy(data)
                        self.robot_state["imu"] = {
                            "roll": sensor_data.imu_data.roll,
                            "pitch": sensor_data.imu_data.pitch,
                            "yaw": sensor_data.imu_data.yaw,
                            "acc_x": sensor_data.imu_data.acc_x,
                            "acc_y": sensor_data.imu_data.acc_y,
                            "acc_z": sensor_data.imu_data.acc_z,
                        }

                elif head.code == CommandCode.RECEIVE_SAFE_DATA:
                    if len(data) >= ctypes.sizeof(ControllerSafeData):
                        safe_data = ControllerSafeData.from_buffer_copy(data)
                        self.robot_state["motor_temperature"] = list(safe_data.motor_temperature)
                        self.robot_state["cpu_temperature"] = safe_data.cpu_info.temperature
                        self.robot_state["cpu_frequency"] = safe_data.cpu_info.frequency

                elif head.code == CommandCode.RECEIVE_BODY_HEIGHT:
                    self.robot_state["body_height"] = head.parameters_size

            time.sleep(0.03)  # 调整更新频率

    # ========== 心跳相关 ==========
    def _start_heartbeat(self):
        """启动心跳线程"""
        if self.heartbeat_running:
            return

        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self.heartbeat_thread.start()
        logger.info(f"心跳线程已启动({HEARTBEAT_RATE}Hz)")

    def _stop_heartbeat(self):
        """停止心跳线程"""
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2.0)
        logger.info("心跳线程已停止")

    def _heartbeat_loop(self):
        """心跳循环"""
        self.send_heartbeat_maintain()
        time.sleep(1.0 / HEARTBEAT_RATE)
        # 首次发送确认连接
        self.send_heartbeat_confirm()

        while self.heartbeat_running:
            try:
                self.send_heartbeat_maintain()
                time.sleep(1.0 / HEARTBEAT_RATE)
            except Exception as e:
                if self.heartbeat_running:
                    logger.error(f"心跳发送失败: {e}")

    def send_heartbeat_maintain(self) -> bool:
        """发送维持心跳指令(应不低于2Hz)"""
        return self.comm.send_simple_command(CommandCode.HEARTBEAT_MAINTAIN)

    def send_heartbeat_confirm(self) -> bool:
        """发送确认连接指令(在开始维持心跳后发送一次)"""
        return self.comm.send_simple_command(CommandCode.HEARTBEAT_CONFIRM)

    # ========== 基本状态转换 ==========

    def stand_down(self) -> bool:
        """起立/趴下状态切换"""
        return self.comm.send_simple_command(CommandCode.STAND_DOWN)

    def force_control_mode(self) -> bool:
        """切换到力控模式"""
        return self.comm.send_simple_command(CommandCode.FORCE_CONTROL)

    def start_stop_motion(self) -> bool:
        """开始/停止运动"""
        return self.comm.send_simple_command(CommandCode.START_STOP_MOTION)

    # ========== 轴指令 ==========

    def send_axis_command(
        self, left_x: int = 0, left_y: int = 0, right_x: int = 0, right_y: int = 0
    ) -> bool:
        """
        发送轴指令(范围: -32767 ~ 32767)

        Args:
            left_x: 左摇杆X轴值
            left_y: 左摇杆Y轴值
            right_x: 右摇杆X轴值
            right_y: 右摇杆Y轴值
        """
        success = True
        if left_x != 0:
            success &= self.comm.send_simple_command(
                CommandCode.AXIS_LEFT_X_FORCE_MOTION, left_x
            )
        if left_y != 0:
            success &= self.comm.send_simple_command(
                CommandCode.AXIS_LEFT_Y_FORCE_MOTION, left_y
            )
        if right_x != 0:
            success &= self.comm.send_simple_command(
                CommandCode.AXIS_RIGHT_X_FORCE_MOTION, right_x
            )
        if right_y != 0:
            success &= self.comm.send_simple_command(
                CommandCode.AXIS_RIGHT_Y_FORCE_MOTION, right_y
            )
        return success

    # ========== 控制模式 ==========

    def set_manual_mode(self) -> bool:
        """切换到手动模式"""
        return self.comm.send_simple_command(CommandCode.MANUAL_MODE)

    def set_non_manual_mode(self) -> bool:
        """切换到非手动模式"""
        return self.comm.send_simple_command(CommandCode.NON_MANUAL_MODE)

    # ========== 身体高度 ==========

    def set_body_height(self, height: str) -> bool:
        """
        设置身体高度

        Args:
            height: "crouch"(匍匐) 或 "normal"(正常)
        """
        value = BODY_HEIGHT.get(height)
        if value is None:
            logger.error(f"未知身体高度模式: {height}")
            return False
        return self.comm.send_simple_command(CommandCode.BODY_HEIGHT, value)

    # ========== 步态切换 ==========

    def set_gait(self, gait: str) -> bool:
        """
        设置步态

        Args:
            gait: 步态名称 (walk/slope/obstacle/stairs_solid/stairs_cumulative等)
        """
        code = GAIT_MODE.get(gait)
        if code is None:
            logger.error(f"未知步态: {gait}")
            return False

        return self.comm.send_simple_command(code)

    # ========== 其他功能 ==========

    def save_data(self) -> bool:
        """保存数据"""
        return self.comm.send_simple_command(CommandCode.SAVE_DATA)

    def soft_emergency_stop(self) -> bool:
        """软急停"""
        return self.comm.send_simple_command(CommandCode.SOFT_EMERGENCY)

    # ========== 自主充电 ==========

    def auto_charge_start(self) -> bool:
        """开始自主充电"""
        return self.comm.send_simple_command(
            CommandCode.CHARGE_START,
            1,
            target_host=self.comm.perception_host,
            target_port=3333,
        )

    def auto_charge_end(self) -> bool:
        """结束自主充电"""
        return self.comm.send_simple_command(
            CommandCode.CHARGE_END,
            0,
            target_host=self.comm.perception_host,
            target_port=3333,
        )

    def auto_charge_reset(self) -> bool:
        """重置充电任务"""
        return self.comm.send_simple_command(
            CommandCode.CHARGE_RESET,
            2,
            target_host=self.comm.perception_host,
            target_port=3333,
        )

    def auto_charge_query(self) -> Optional[int]:
        """查询充电状态"""
        if self.comm.send_simple_command(
            CommandCode.CHARGE_QUERY,
            0,
            target_host=self.comm.perception_host,
            target_port=3333,
        ):
            head = self.comm.receive_simple_cmd_response()
            if head and head.code == CommandCode.CHARGE_QUERY:
                return head.parameters_size
        return None

    # ========== 地形图功能 ==========

    def set_terrain_vel_source(self, source: str) -> bool:
        """
        设置地形图速度输入源

        Args:
            source: "joystick"(手柄) 或 "navigation"(导航)
        """
        value = TERRAIN_VEL_SOURCE.get(source)
        if value is None:
            logger.error(f"未知速度输入源: {source}")
            return False
        return self.comm.send_simple_command(
            CommandCode.TERRAIN_VEL_SOURCE,
            value,
            target_host=self.comm.perception_host,
            target_port=43899,
        )

    def set_terrain_mode(self, mode: str) -> bool:
        """
        设置地形图模式

        Args:
            mode: solid_ground/hollow_ground/no_riser_stairs/cumulative_frame
        """
        value = TERRAIN_MODE.get(mode)
        if value is None:
            logger.error(f"未知地形图模式: {mode}")
            return False

        return self.comm.send_simple_command(
            CommandCode.TERRAIN_MODE,
            value,
            target_host=self.comm.perception_host,
            target_port=43899,
        )

    def set_terrain_brake_mode(self, mode: str) -> bool:
        """
        设置停避障模式

        Args:
            mode: "stop"(停障) 或 "avoid"(避障)
        """
        value = TERRAIN_BRAKE_MODE.get(mode)
        if value is None:
            logger.error(f"未知停避障模式: {mode}")
            return False
        return self.comm.send_simple_command(
            CommandCode.TERRAIN_BRAKE_MODE,
            value,
            target_host=self.comm.perception_host,
            target_port=43899,
        )

    def set_terrain_obstacle_threshold(self, height: str) -> bool:
        """
        设置障碍物高度阈值

        Args:
            height: low(8cm) 或 high(28cm)
        """
        value = TERRAIN_OBSTACLE_THRESHOLD.get(height)
        if value is None:
            logger.error(f"未知障碍物高度阈值: {height}")
            return False
        return self.comm.send_simple_command(
            CommandCode.TERRAIN_OBSTACLE_THRESHOLD,
            value,
            target_host=self.comm.perception_host,
            target_port=43899,
        )

    # ========== 激光里程计 ==========

    def enable_lidar_odom(self, enable: bool) -> Optional[int]:
        """
        开启/关闭激光里程计

        Args:
            enable: True=开启, False=关闭

        Returns:
            执行结果: 0=成功, -1=失败, None=超时
        """
        if not isinstance(enable, bool):
            logger.error("enable参数必须为布尔值")
            return None
        value = 1 if enable else 0
        if self.comm.send_simple_command(
            CommandCode.LIDAR_ODOM,
            value,
            target_host=self.comm.perception_host,
            target_port=60000,
        ):
            head = self.comm.receive_simple_cmd_response()
            if head and head.code == CommandCode.LIDAR_ODOM:
                return head.parameters_size
        return None
