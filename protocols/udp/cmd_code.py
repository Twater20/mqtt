# ==================== 指令码枚举 ====================
from enum import IntEnum


class CommandCode(IntEnum):
    """UDP指令码定义"""

    # 心跳指令
    HEARTBEAT_MAINTAIN = 0x21040001  # 维持心跳
    HEARTBEAT_CONFIRM = 0x21020001  # 确认连接

    # 基本状态转换
    STAND_DOWN = 0x21010202  # 起立/趴下
    FORCE_CONTROL = 0x2101020A  # 力控模式
    START_STOP_MOTION = 0x21010201  # 开始/停止运动

    # 轴指令 - 力控站立或踏步状态
    AXIS_LEFT_X_FORCE_MOTION = 0x21010131  # 左摇杆X轴(Roll角或Y轴速度)
    AXIS_LEFT_Y_FORCE_MOTION = 0x21010130  # 左摇杆Y轴(身体高度或X轴速度)
    AXIS_RIGHT_X_FORCE_MOTION = 0x21010135  # 右摇杆X轴(Yaw角或Yaw角速度)
    AXIS_RIGHT_Y_FORCE_MOTION = 0x21010102  # 右摇杆Y轴(Pitch角)

    # 控制模式切换
    MANUAL_MODE = 0x21010C02  # 手动模式
    NON_MANUAL_MODE = 0x21010C03  # 非手动模式

    # 身体高度切换
    BODY_HEIGHT = 0x21010406  # 0=匍匐, 2=正常

    # 步态指令
    GAIT_WALK = 0x21010300  # 行走步态
    GAIT_SLOPE = 0x21010402  # 斜坡步态
    GAIT_OBSTACLE = 0x21010401  # 越障步态
    GAIT_STAIRS = 0x21010405  # 楼梯步态(实心/镂空/无踢面)
    GAIT_STAIRS_CUMULATIVE = 0x2101040A  # 楼梯步态(累积帧)
    GAIT_STAIRS_45 = 0x2101040B  # 45°楼梯步态(累积帧)
    GAIT_L_WALK = 0x21010420  # L行走步态
    GAIT_MOUNTAIN = 0x21010421  # 山地步态
    GAIT_SILENT = 0x21010422  # 静音步态

    # 保存数据
    SAVE_DATA = 0x010C01  # 保存数据(v2.2.45+)

    # 软急停
    SOFT_EMERGENCY = 0x21010C0E  # 软急停

    # 接收信息指令
    RECEIVE_RCS_DATA = 0x1008  # 机器人运行状态
    RECEIVE_MOTION_STATE = 0x1009  # 机器人运动状态
    RECEIVE_SENSOR_DATA = 0x100A  # 传感器数据
    RECEIVE_SAFE_DATA = 0x100B  # 系统状态
    RECEIVE_BATTERY = 0x21050F0A  # 电池信息
    RECEIVE_BODY_HEIGHT = 0x11050F08  # 身体高度状态

    # 自主充电指令 (发送到192.168.1.105:3333)
    CHARGE_START = 0x91910250  # value=1 开始充电
    CHARGE_END = 0x91910250  # value=0 结束充电
    CHARGE_RESET = 0x91910250  # value=2 重置任务
    CHARGE_QUERY = 0x91910253  # value=0 查询状态

    # 地形图指令 (发送到192.168.1.105:43899)
    TERRAIN_VEL_SOURCE = 0x3101EE03  # 速度输入源: 1=手柄, 2=导航
    TERRAIN_MODE = 0x3101EE01  # 地形图模式: 3=实心, 4=镂空, 5=无踢面, 20=累积帧
    TERRAIN_BRAKE_MODE = 0x3101EE02  # 停避障模式: 1=停障, 2=避障
    TERRAIN_OBSTACLE_THRESHOLD = 0x3101EE04  # 障碍物高度: 1=8cm, 2=28cm

    # 激光里程计 (发送到192.168.1.105:60000)
    LIDAR_ODOM = 0x0BAA0001  # 0=关闭, 1=开启


# 机器人基本状态
BASIC_STATE = {
    "lying_down": 0,  # 趴下状态
    "standing_up": 1,  # 正在起立状态
    "init_stand": 2,  # 初始站立状态
    "force_stand": 3,  # 力控站立状态
    "stepping": 4,  # 踏步状态
    "lying_down_in_progress": 5,  # 正在趴下状态
    "soft_estop_fall": 6,  # 软急停/摔倒状态
    "rl_state": 16,  # RL状态
}


# 基本状态反向映射
BASIC_STATE_REVERSE = {v: k for k, v in BASIC_STATE.items()}


# 控制模式
CONTROL_STATE = {
    "manual": 0,  # 手动模式
    "non_manual": 1,  # 非手动模式
}

# 控制模式反向映射
CONTROL_STATE_REVERSE = {v: k for k, v in CONTROL_STATE.items()}


# 步态状态
GAIT_STATE = {
    "walk": 0,  # 行走步态
    "obstacle": 1,  # 越障步态
    "slope": 2,  # 斜坡步态
    "run": 3,  # 跑步步态
    "stairs": 6,  # 楼梯步态（实心/镂空/无踢面）
    "stairs_acc": 7,  # 楼梯步态（累积帧）
    "stairs_45": 8,  # 45度楼梯步态（累积帧）
    "l_walk": 32,  # L行走步态
    "mountain": 33,  # 山地步态
    "silent": 34,  # 静音步态
}

# 步态状态反向映射
GAIT_STATE_REVERSE = {v: k for k, v in GAIT_STATE.items()}


# 步态模式
GAIT_MODE = {
    "walk": CommandCode.GAIT_WALK,  # 行走步态
    "obstacle": CommandCode.GAIT_OBSTACLE,  # 越障步态
    "slope": CommandCode.GAIT_SLOPE,  # 斜坡步态
    "stairs_solid": CommandCode.GAIT_STAIRS,  # 楼梯步态（实心/镂空/无踢面）
    "stairs_cumulative": CommandCode.GAIT_STAIRS_CUMULATIVE,  # 楼梯步态（累积帧）
    "stairs_45_cumulative": CommandCode.GAIT_STAIRS_45,  # 45度楼梯步态（累积帧）
    "l_walk": CommandCode.GAIT_L_WALK,  # L行走步
    "mountain": CommandCode.GAIT_MOUNTAIN,  # 山地步态
    "silent": CommandCode.GAIT_SILENT,  # 静音步态
}

# 身体高度模式
BODY_HEIGHT = {
    "crouch": 0,  # 匍匐
    "normal": 2,  # 正常
}

# 地形图模式
TERRAIN_MODE = {
    "solid_ground": 3,  # 实心地面
    "hollow_ground": 4,  # 镂空地面
    "no_riser_stairs": 5,  # 无踢面楼梯
    "cumulative_frame_prepare": 18,  # 累积帧准备状态
    "cumulative_frame": 20,  # 累积帧模式
}

# 停避障模式
TERRAIN_BRAKE_MODE = {
    "stop": 1,  # 停障
    "avoid": 2,  # 避障
}

# 速度输入源
TERRAIN_VEL_SOURCE = {
    "joystick": 1,  # 手柄摇杆
    "navigation": 2,  # 导航模块
}

TERRAIN_OBSTACLE_THRESHOLD = {
    "low": 1,  # 低障碍物 (8cm)
    "high": 2,  # 高障碍物 (28cm)
}

# 各步态最大速度限制（正常高度）
GAIT_MAX_VELOCITY = {
    "WALK": {
        "forward": 1.2,  # m/s
        "backward": 0.75,
        "lateral": 0.45,  # rad/s
        "yaw": 0.75,
    },
    "SLOPE": {"forward": 0.7, "backward": 0.15, "lateral": 0.25, "yaw": 0.5},
    "OBSTACLE": {"forward": 0.3, "backward": 0.4, "lateral": 0.1, "yaw": 0.5},
    "STAIRS": {"forward": 0.3, "backward": 0.3, "lateral": 0.2, "yaw": 0.8},
    "STAIRS_ACC": {"forward": 0.6, "backward": 0.3, "lateral": 0.2, "yaw": 0.8},
    "STAIRS_45": {"forward": 0.3, "backward": 0.3, "lateral": 0.2, "yaw": 0.8},
    "L_WALK": {"forward": 1.0, "backward": 1.0, "lateral": 0.5, "yaw": 1.2},
    "MOUNTAIN": {"forward": 1.0, "backward": 1.0, "lateral": 0.8, "yaw": 1.2},
}
