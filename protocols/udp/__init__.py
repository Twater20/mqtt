"""UDP协议模块"""

from .cmd_code import (
    BASIC_STATE,
    BASIC_STATE_REVERSE,
    BODY_HEIGHT,
    CONTROL_STATE,
    GAIT_MAX_VELOCITY,
    GAIT_MODE,
    GAIT_STATE,
    GAIT_STATE_REVERSE,
    TERRAIN_BRAKE_MODE,
    TERRAIN_MODE,
    TERRAIN_OBSTACLE_THRESHOLD,
    TERRAIN_VEL_SOURCE,
    CommandCode,
)
from .communicator import UDPCommunicator
from .controller import RobotDogUDPController
from .structs import (
    BatterySensorData,
    Command,
    CommandHead,
    ControllerSafeData,
    ControllerSensorData,
    CpuInfo,
    ImuSensorData,
    LegJointData,
    MotionStateData,
    RcsData,
    RobotJointVel,
)

__all__ = [
    # 数据结构
    "CommandHead",
    "Command",
    "RobotJointVel",
    "ImuSensorData",
    "LegJointData",
    "ControllerSensorData",
    "RcsData",
    "MotionStateData",
    "CpuInfo",
    "ControllerSafeData",
    "BatterySensorData",
    # 指令码和枚举
    "CommandCode",
    "BASIC_STATE",
    "BASIC_STATE_REVERSE",
    "GAIT_STATE",
    "GAIT_STATE_REVERSE",
    "CONTROL_STATE",
    "GAIT_MODE",
    "BODY_HEIGHT",
    "TERRAIN_MODE",
    "TERRAIN_BRAKE_MODE",
    "TERRAIN_VEL_SOURCE",
    "TERRAIN_OBSTACLE_THRESHOLD",
    "GAIT_MAX_VELOCITY",
    # 通信和控制
    "UDPCommunicator",
    "RobotDogUDPController",
]
