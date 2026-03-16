"""UDP协议数据结构定义"""

import ctypes

# ==================== C结构体定义 (使用1字节对齐，与嵌入式端保持一致) ====================


class CommandHead(ctypes.Structure):
    """简单指令头结构"""

    _pack_ = 1
    _fields_ = [
        ("code", ctypes.c_uint32),
        ("parameters_size", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
    ]


class Command(ctypes.Structure):
    """复杂指令结构"""

    _pack_ = 1
    _fields_ = [("head", CommandHead), ("data", ctypes.c_uint32 * 256)]


class RobotJointVel(ctypes.Structure):
    """关节速度结构"""

    _pack_ = 1
    _fields_ = [("joint_vel", ctypes.c_double * 12)]


class ImuSensorData(ctypes.Structure):
    """IMU传感器数据结构"""

    _pack_ = 1
    _fields_ = [
        ("timestamp", ctypes.c_int32),
        ("roll", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("yaw", ctypes.c_float),
        ("omega_x", ctypes.c_float),
        ("omega_y", ctypes.c_float),
        ("omega_z", ctypes.c_float),
        ("acc_x", ctypes.c_float),
        ("acc_y", ctypes.c_float),
        ("acc_z", ctypes.c_float),
    ]


class LegJointData(ctypes.Structure):
    """关节数据结构"""

    _pack_ = 1
    _fields_ = [("data", ctypes.c_float * 12)]


class ControllerSensorData(ctypes.Structure):
    """运动控制传感器数据"""

    _pack_ = 1
    _fields_ = [
        ("imu_data", ImuSensorData),
        ("joint_pos", LegJointData),
        ("joint_vel", LegJointData),
        ("joint_tau", LegJointData),
    ]


class RcsData(ctypes.Structure):
    """机器人运行状态信息"""

    _pack_ = 1
    _fields_ = [
        ("robot_name", ctypes.c_char * 15),
        ("current_mileage", ctypes.c_int32),
        ("total_mileage", ctypes.c_int32),
        ("current_run_time", ctypes.c_long),
        ("total_run_time", ctypes.c_long),
        ("current_motion_time", ctypes.c_long),
        ("total_motion_time", ctypes.c_long),
        ("joystick", ctypes.c_float * 4),
        ("rcs_state", ctypes.c_uint8 * 10),
        ("error_state", ctypes.c_uint32),
    ]


class MotionStateData(ctypes.Structure):
    """机器人运动状态信息"""

    _pack_ = 1
    _fields_ = [
        ("basic_state", ctypes.c_uint8),
        ("gait_state", ctypes.c_uint8),
        ("max_forward_vel", ctypes.c_float),
        ("max_backward_vel", ctypes.c_float),
        ("leg_odom_pos", ctypes.c_float * 3),
        ("leg_odom_vel", ctypes.c_float * 3),
        ("robot_distance", ctypes.c_float),
        ("touch_state", ctypes.c_uint),
        ("control_state", ctypes.c_uint32),
        ("task_state", ctypes.c_uint8 * 10),
    ]


class CpuInfo(ctypes.Structure):
    """CPU状态信息"""

    _pack_ = 1
    _fields_ = [("temperature", ctypes.c_float), ("frequency", ctypes.c_float)]


class ControllerSafeData(ctypes.Structure):
    """运动控制系统状态"""

    _pack_ = 1
    _fields_ = [
        ("motor_temperature", ctypes.c_float * 12),
        ("driver_temperature", ctypes.c_uint8 * 12),
        ("cpu_info", CpuInfo),
    ]


class BatterySensorData(ctypes.Structure):
    """电池信息"""

    _pack_ = 1
    _fields_ = [
        ("voltage", ctypes.c_uint16),
        ("current", ctypes.c_int16),
        ("remaining_capacity", ctypes.c_uint16),
        ("nominal_capacity", ctypes.c_uint16),
        ("cycles", ctypes.c_uint16),
        ("production_date", ctypes.c_uint16),
        ("balanced_low", ctypes.c_uint16),
        ("balanced_high", ctypes.c_uint16),
        ("protected_state", ctypes.c_uint16),
        ("software_version", ctypes.c_uint8),
        ("battery_level", ctypes.c_uint8),
        ("mos_state", ctypes.c_uint8),
        ("battery_quantity", ctypes.c_uint8),
        ("battery_ntc", ctypes.c_uint8),
        ("battery_temperature", ctypes.c_float * 4),
    ]
