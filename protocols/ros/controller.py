"""ROS控制器模块 - 封装所有ROS话题操作"""

from typing import Optional

try:
    import rospy
    import tf
    from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu, JointState, PointCloud2
    from std_msgs.msg import Float32, Float32MultiArray, Float64, Int8, Int32, String, UInt8
except ImportError as e:
    raise ImportError("ROS未安装，无法使用ROS功能") from e

from utils import get_logger

from .communicator import ROSCommunicator

logger = get_logger(__name__)


class RobotDogROSController:
    """机器狗ROS控制器 - 封装所有ROS话题操作

    注意: 只有UDP无法实现的功能才使用ROS，优先使用UDP
    """

    def __init__(self, communicator: ROSCommunicator):
        """
        初始化ROS控制器

        Args:
            communicator: ROS通信器实例
        """
        self.comm = communicator
        # 初始化常用订阅器(用于状态获取)
        self._init_status_subscribers()

        # 初始化常用发布器(避免首次发布丢失)
        self._init_publishers()

        logger.info("ROS控制器初始化完成")

    def _init_status_subscribers(self):
        """初始化状态订阅器 - 订阅所有可用的ROS状态话题"""
        # 电池信息（从UDP获取，ROS不再订阅）
        self.comm.create_subscriber("/battery/level", UInt8)
        self.comm.create_subscriber("/battery/current", Float32)
        self.comm.create_subscriber("/battery/voltage", Float32)

        # 运动状态
        self.comm.create_subscriber("/control_mode", UInt8)
        self.comm.create_subscriber("/robot_basic_state", Int32)
        self.comm.create_subscriber("/robot_gait_state", Int32)
        self.comm.create_subscriber("/robot_velocity", Twist)
        self.comm.create_subscriber("/leg_odom", Odometry)

        # IMU数据
        # self.comm.create_subscriber("/imu/data", Imu)

        # 关节状态
        # self.comm.create_subscriber("/joint_states", JointState)

        # 点云数据
        # self.comm.create_subscriber("/lidar_points", PointCloud2)

        # 电机温度 (12个关节) 和 CPU 温度
        self.comm.create_subscriber("/motor_temperature", Float32MultiArray)
        self.comm.create_subscriber("/motion_cpu/temperature", Float32)

        # 运动距离
        self.comm.create_subscriber("/mileage/current_mileage", Int32)

        # 导航相关 (仅ROS可用)
        self.comm.create_subscriber("/location_status", Int8)
        self.comm.create_subscriber("/move_base/obs_state", Int32)
        self.comm.create_subscriber("/odom", Odometry)

    def _init_publishers(self):
        """初始化常用发布器"""
        self.comm.create_publisher("/yzrt_navigation/waypoints", String)
        self.comm.create_publisher("/cmd_vel", Twist)
        self.comm.create_publisher("/brake_mode", Int32)
        self.comm.create_publisher("/vel_source", Int32)
        self.comm.create_publisher("/height_map_mode", Int32)
        self.comm.create_publisher("/step_z_max", Float64)
        self.comm.create_publisher("/slow_t", Float64)
        self.comm.create_publisher("/stop_t", Float64)
        self.comm.create_publisher("/move_base_simple/goal", PoseStamped)
        self.comm.create_publisher("/initialpose", PoseWithCovarianceStamped)
        self.comm.create_publisher("/map_request/pcd", String)

        self.comm.create_publisher("/yzrt_navigation/command", String)

    # ========== 速度控制 (UDP无法实现的精确速度控制) ==========

    def publish_cmd_vel(
        self,
        linear_x: float,
        linear_y: float,
        angular_z: float,
    ) -> bool:
        """
        发布速度指令 - 仅在需要精确速度控制时使用

        Args:
            linear_x: 线速度X (m/s)
            linear_y: 线速度Y (m/s)
            angular_z: 角速度Z (rad/s)
        """
        msg = Twist()
        msg.linear.x = linear_x
        msg.linear.y = linear_y
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = angular_z
        return self.comm.publish("/cmd_vel", Twist, msg)

    # ========== 地形图相关 (部分功能UDP可实现，优先UDP) ==========

    def set_brake_mode(self, mode: int) -> bool:
        """设置停避障模式 - 注意: UDP也可实现此功能"""
        msg = Int32()
        msg.data = mode
        return self.comm.publish("/brake_mode", Int32, msg)

    def set_vel_source(self, source: int) -> bool:
        """设置速度输入源 - 注意: UDP也可实现此功能"""
        msg = Int32()
        msg.data = source
        return self.comm.publish("/vel_source", Int32, msg)

    def set_height_map_mode(self, mode: int) -> bool:
        """设置地形图模式 - 注意: UDP也可实现此功能"""
        msg = Int32()
        msg.data = mode
        return self.comm.publish("/height_map_mode", Int32, msg)

    def set_step_z_max(self, height_m: float) -> bool:
        """设置障碍物高度阈值 - 注意: UDP也可实现此功能"""
        msg = Float64()
        msg.data = height_m
        return self.comm.publish("/step_z_max", Float64, msg)

    def set_slow_t(self, time_s: float) -> bool:
        """设置触发修正的碰撞时间 - ROS专用"""
        msg = Float64()
        msg.data = time_s
        return self.comm.publish("/slow_t", Float64, msg)

    def set_stop_t(self, time_s: float) -> bool:
        """设置触发期望速度置零的碰撞时间 - ROS专用"""
        msg = Float64()
        msg.data = time_s
        return self.comm.publish("/stop_t", Float64, msg)

    # ========== 导航相关 (UDP无法实现) ==========

    def send_nav_goal(self, x: float, y: float, z: float, yaw: float) -> bool:
        """
        下发普通导航目标点 - 仅ROS可用
        Args:
            x: 位置X (米)
            y: 位置Y (米)
            z: 位置Z (米)
            yaw: 朝向角Yaw (弧度)
        """
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        quaternion = tf.transformations.quaternion_from_euler(0, 0, yaw)
        msg.pose.orientation.x = quaternion[0]
        msg.pose.orientation.y = quaternion[1]
        msg.pose.orientation.z = quaternion[2]
        msg.pose.orientation.w = quaternion[3]
        logger.warning("导航目标点功能需要move_base_msgs，这里使用简化版本")
        return self.comm.publish("/move_base_simple/goal", PoseStamped, msg)

    def reset_pose(self, x: float, y: float, z: float, yaw: float) -> bool:
        """
        重置定位位姿 - 仅ROS可用
        Args:
            x: 位置X (米)
            y: 位置Y (米)
            z: 位置Z (米)
            yaw: 朝向角Yaw (弧度)
        """
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.position.z = z
        quaternion = tf.transformations.quaternion_from_euler(0, 0, yaw)
        msg.pose.pose.orientation.x = quaternion[0]
        msg.pose.pose.orientation.y = quaternion[1]
        msg.pose.pose.orientation.z = quaternion[2]
        msg.pose.pose.orientation.w = quaternion[3]

        return self.comm.publish("/initialpose", PoseWithCovarianceStamped, msg)

    def switch_map(self, map_path: str) -> bool:
        """切换全局地图 - 仅ROS可用"""
        msg = String()
        msg.data = map_path
        return self.comm.publish("/map_request/pcd", String, msg)

    # ========== 状态查询 (仅保留UDP无法获取的导航相关状态) ==========
    # 注意: 电池、运动状态等应使用UDP获取，不要使用ROS

    def get_location_status(self) -> Optional[int]:
        """获取定位状态(0=正常, 1=丢失) - 仅ROS可用"""
        data = self.comm.get_cached_data("/location_status")
        return data.data if data else None

    def get_nav_obs_state(self) -> Optional[int]:
        """获取导航停避障状态(0=无碰撞风险, 1=正在停避障) - 仅ROS可用"""
        data = self.comm.get_cached_data("/move_base/obs_state")
        return data.data if data else None

    def get_position_ros(self) -> Optional[list[float]]:
        """
        获取里程计信息 - 仅ROS可用
        returns: [x, y, z, yaw] 或 None
        """
        data = self.comm.get_cached_data("/odom")
        if data:
            position = data.pose.pose.position
            orientation = data.pose.pose.orientation
            yaw = tf.transformations.euler_from_quaternion(
                [orientation.x, orientation.y, orientation.z, orientation.w]
            )[2]
            return [position.x, position.y, position.z, yaw]
        return None

    def get_robot_state(self) -> dict:
        """获取当前机器狗状态 - 从ROS话题获取所有状态信息
        
        返回字段与 mqtt_publisher 物模型 payload 所需字段对齐。
        """
        state = {
            "basic_state": None,
            "gait_state": None,
            "control_mode": None,
            "battery_level": 0,
            "battery_current": 0.0,
            "battery_voltage": 0.0,
            "motor_temperature": [0.0] * 12,
            "cpu_temperature": 0.0,
            "firmware_version": "1.0.0",
            "odometry_world": None,
        }

        # 电池相关信息
        battery_level = self.comm.get_cached_data("/battery/level")
        if battery_level:
            state["battery_level"] = battery_level.data
            
        battery_current = self.comm.get_cached_data("/battery/current")
        if battery_current:
            state["battery_current"] = battery_current.data
            
        battery_voltage = self.comm.get_cached_data("/battery/voltage")
        if battery_voltage:
            state["battery_voltage"] = battery_voltage.data

        # 基本状态
        basic_state = self.comm.get_cached_data("/robot_basic_state")
        if basic_state:
            # 映射基本状态值到描述
            state_map = {
                0: "lying",
                1: "standing_up",
                2: "initial_standing",
                3: "force_standing",
                4: "stepping",
                5: "lying_down",
                6: "soft_emergency",
                16: "rl_state",
            }
            state["basic_state"] = state_map.get(
                basic_state.data, f"unknown_{basic_state.data}"
            )

        # 步态状态
        gait_state = self.comm.get_cached_data("/robot_gait_state")
        if gait_state:
            # 映射步态值到描述
            gait_map = {
                0: "walk",
                1: "obstacle",
                2: "slope",
                3: "run",
                6: "stair",
                7: "stair_frame",
                8: "stair_45",
                32: "l_walk",
                33: "mountain",
                34: "silent",
            }
            state["gait_state"] = gait_map.get(
                gait_state.data, f"unknown_{gait_state.data}"
            )

        # 控制模式
        control_mode = self.comm.get_cached_data("/control_mode")
        if control_mode:
            state["control_mode"] = "manual" if control_mode.data == 0 else "non_manual"

        # 里程计信息 - 从/leg_odom获取
        leg_odom = self.comm.get_cached_data("/leg_odom")
        robot_distance = self.comm.get_cached_data("/mileage/current_mileage")
        if leg_odom and robot_distance:
            position = leg_odom.pose.pose.position
            orientation = leg_odom.pose.pose.orientation
            velocity = leg_odom.twist.twist

            # 计算yaw角
            yaw = tf.transformations.euler_from_quaternion(
                [orientation.x, orientation.y, orientation.z, orientation.w]
            )[2]

            state["odometry_world"] = {
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "yaw": yaw,
                },
                "velocity": {
                    "x": velocity.linear.x,
                    "y": velocity.linear.y,
                    "yaw": velocity.angular.z,
                },
                "distance": robot_distance.data / 100.0,  # 转换为米
            }

        # 电机温度 (12个关节)
        motor_temp = self.comm.get_cached_data("/motor_temperature")
        if motor_temp and hasattr(motor_temp, 'data') and len(motor_temp.data) >= 12:
            state["motor_temperature"] = list(motor_temp.data[:12])

        # CPU 温度
        cpu_temp = self.comm.get_cached_data("/motion_cpu/temperature")
        if cpu_temp:
            state["cpu_temperature"] = cpu_temp.data

        return state
