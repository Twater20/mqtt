# -*- coding: utf-8 -*-
"""
ROS到MQTT数据桥接脚本

通过ROS话题订阅获取机器狗状态信息，并通过MQTT上传至指定服务器。
根据物模型 `Go2-EDU1上报物模型.txt` 标准化输出。
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

# 将项目的根目录加入sys.path以便能导入utils
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 依赖库 paho-mqtt
# 需要提前安装: pip install paho-mqtt
import paho.mqtt.client as mqtt

from utils import get_logger
from protocols.ros.communicator import ROSCommunicator
from protocols.ros.controller import RobotDogROSController
from protocols.ros.module_status import get_all_module_status
from protocols.udp.communicator import UDPCommunicator
from protocols.udp.controller import RobotDogUDPController

logger = get_logger(__name__)

# ==================== 配置 ====================
# MQTT 服务器配置
MQTT_BROKER = "8.148.80.167"
MQTT_PORT = 11883
MQTT_USERNAME = "eo_iot"
MQTT_PASSWORD = "Abc@2025"

# 设备ID，如果需要多台机器狗，修改这里的ID
DEVICE_ID = "X30021022"
MQTT_TOPIC = f"$thing/up/property/x30pro/{DEVICE_ID}"

# UDP 配置（用于获取电池信息）
MOTION_HOST = "192.168.1.103"
MOTION_PORT = 43897
PERCEPTION_HOST = "192.168.1.103"
RECEIVE_PORT = 43897
# ==============================================


class MqttPublisher:
    """MQTT 发布客户端"""

    def __init__(self, broker: str, port: int, username: str, password: str, client_id: str = ""):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"go2edu1_publisher_{int(time.time())}"
        
        try:
            # paho-mqtt 2.0+ requires CallbackAPIVersion
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=self.client_id)
        except AttributeError:
            self.client = mqtt.Client(client_id=self.client_id)
            
        self.client.username_pw_set(username, password)
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("成功连接到MQTT服务器")
            self.connected = True
        else:
            logger.error(f"连接MQTT服务器失败, 状态码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"由于原因 {rc} 断开与MQTT服务器的连接")
        self.connected = False

    def connect(self):
        """连接MQTT Broker并在后台启动循环"""
        logger.info(f"正在连接MQTT Broker {self.broker}:{self.port}...")
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()  # 启动后台处理网络事件
            return True
        except Exception as e:
            logger.error(f"MQTT连接异常: {e}")
            return False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict):
        """发布消息"""
        if not self.connected:
            logger.warning("MQTT未连接，无法发送数据")
            return False
            
        try:
            msg_str = json.dumps(payload, ensure_ascii=False)
            result = self.client.publish(topic, msg_str, qos=0)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"成功发布数据到 {topic}")
                return True
            else:
                logger.error(f"发布失败，错误码：{result.rc}")
                return False
        except Exception as e:
            logger.error(f"发布数据时发生错误: {e}")
            return False


class StateBridge:
    """状态桥接器：
    - ROS 话题订阅：运动状态、电机温度、CPU温度等
    - UDP 通信：电池信息（电量、电压、循环次数等）
    - 本地检测：板卡模块状态
    格式化后发布到MQTT
    """
    
    def __init__(self):
        # 初始化 ROS 控制器（订阅运动状态、温度等话题）
        self.ros_comm = ROSCommunicator(node_name="mqtt_bridge")
        self.ros_controller = RobotDogROSController(self.ros_comm)

        # 初始化 UDP 控制器（获取电池信息）
        self.udp_comm = UDPCommunicator(MOTION_HOST, MOTION_PORT, PERCEPTION_HOST, RECEIVE_PORT)
        self.udp_controller = RobotDogUDPController(self.udp_comm)
        
        # 初始化 MQTT 客户端
        self.mqtt_client = MqttPublisher(MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD)
        
        self.running = False
        self.bridge_thread = None
        
        # 记录启动时间计算运行时长
        self.start_time = datetime.now()
        
    def start(self):
        """启动桥接器"""
        logger.info("启动 ROS+UDP 到 MQTT 桥接器...")
        # 启动 UDP 控制器（电池数据）
        self.udp_controller.start_udp_controller()
        # ROS 订阅在 controller 初始化时已自动启动
        if not self.mqtt_client.connect():
            logger.error("无法启动 - MQTT 连接失败")
            return
            
        self.running = True
        self.bridge_thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self.bridge_thread.start()

    def stop(self):
        """停止桥接器"""
        logger.info("停止桥接器...")
        self.running = False
        if self.bridge_thread:
            self.bridge_thread.join(timeout=3.0)
            
        self.mqtt_client.disconnect()
        self.udp_controller.stop_udp_controller()
        self.ros_comm.shutdown()

    def _build_payload(self) -> dict:
        """
        严格按照物模型组装上报数据。
        数据来源：
          - ROS 话题订阅：运动状态、步态、电机温度、CPU温度
          - UDP 通信：电池信息（电量、循环次数等）
          - 本地 3588 板卡检测 (module_status)：5G/蓝牙/导航/图像/调度/语音模块状态
        """
        # -------- 获取 ROS 机器狗状态（运动、温度） --------
        ros_state = self.ros_controller.get_robot_state()
        logger.info(f"=== ROS订阅状态 ===\n{json.dumps(ros_state, ensure_ascii=False, indent=2, default=str)}")

        # -------- 获取 UDP 机器狗状态（电池） --------
        udp_state = self.udp_controller.get_robot_state()
        logger.info(f"=== UDP电池状态 ===\n{json.dumps({k:v for k,v in udp_state.items() if 'battery' in k}, ensure_ascii=False, default=str)}")

        # -------- 获取 3588 板卡各模块状态 --------
        board = get_all_module_status()

        # -------- 时间与运行时长 --------
        now = datetime.now()
        timestamp = int(now.timestamp() * 1000)
        run_delta = now - self.start_time
        runtime_hours = f"{run_delta.total_seconds() / 3600:.2f}"

        # -------- 运动模式（英文→中文翻译后上报） --------
        BASIC_STATE_CN = {
            "lying": "趴下状态", "standing_up": "正在起立", "initial_standing": "初始站立",
            "force_standing": "力控站立", "stepping": "踏步状态", "lying_down": "正在趴下",
            "soft_emergency": "软急停/摔倒", "rl_state": "RL状态",
        }
        GAIT_STATE_CN = {
            "walk": "行走步态", "obstacle": "越障步态", "slope": "斜坡步态",
            "run": "跑步步态", "stair": "楼梯步态", "stair_frame": "楼梯步态(累积帧)",
            "stair_45": "45°楼梯步态", "l_walk": "L行走步态", "mountain": "山地步态",
            "silent": "静音步态", "l_stair": "L楼梯步态",
        }
        basic_en = ros_state.get("basic_state")
        gait_en = ros_state.get("gait_state")
        basic_cn = BASIC_STATE_CN.get(basic_en, basic_en or "未知")
        gait_cn = GAIT_STATE_CN.get(gait_en, gait_en or "未知")
        robot_mode_str = f"{basic_cn}-{gait_cn}" if basic_en and gait_en else "正常"

        # -------- 电机温度 --------
        motor_temps = ros_state.get("motor_temperature") or [30.0] * 12

        # -------- 电池健康度（基于循环次数线性衰减：1000次→80%）--------
        cycles = udp_state.get("battery_cycles", 0)
        health_val = max(0, round(100 - cycles * 0.02, 1))
        health_pct = f"{health_val}%"

        # -------- CPU 温度 --------
        cpu_temp = ros_state.get("cpu_temperature", 25.0)

        # -------- 四条腿状态（能读取到该腿3个电机温度即为正常） --------
        def leg_ok(indices):
            """判断指定索引的电机温度是否都能读取到（非0）"""
            return 0 if all(motor_temps[i] != 0.0 for i in indices) else 1

        lf_status = leg_ok([0, 1, 2])    # 左前腿：hip_fl, hip_fr, knee
        rf_status = leg_ok([3, 4, 5])    # 右前腿
        lr_status = leg_ok([6, 7, 8])    # 左后腿
        rr_status = leg_ok([9, 10, 11])  # 右后腿

        # ====================================================
        # 严格按物模型字段构建 payload
        # ====================================================
        payload = {
            # --- 基础状态 ---
            "connection_status.is_online": True,
            "battery_percentage":          ros_state.get("battery_level", 0),
            "location":                    "",   # 经纬度坐标，暂无数据源时留空
            "firmware_version":            ros_state.get("firmware_version", "1.0.0"),
            "temperature":                 round(cpu_temp, 2),
            "runtime_info.runtime_hours":  runtime_hours,
            "collection_time":             now.strftime("%Y-%m-%d %H:%M:%S"),

            # --- 电池健康 ---
            "battery_health.health_status": health_pct,
            "battery_health.cycle_count":   str(udp_state.get("battery_cycles", 0)),

            # --- 运动模式（中文） ---
            "robot_mode.mode_name": robot_mode_str,

            # --- 12个电机温度 ---
            "motor_temp_lf_hip_fl": round(motor_temps[0], 2),
            "motor_temp_lf_hip_fr": round(motor_temps[1], 2),
            "motor_temp_lf_knee":   round(motor_temps[2], 2),
            "motor_temp_rf_hip_fl": round(motor_temps[3], 2),
            "motor_temp_rf_hip_fr": round(motor_temps[4], 2),
            "motor_temp_rf_knee":   round(motor_temps[5], 2),
            "motor_temp_lr_hip_fl": round(motor_temps[6], 2),
            "motor_temp_lr_hip_fr": round(motor_temps[7], 2),
            "motor_temp_lr_knee":   round(motor_temps[8], 2),
            "motor_temp_rr_hip_fl": round(motor_temps[9], 2),
            "motor_temp_rr_hip_fr": round(motor_temps[10], 2),
            "motor_temp_rr_knee":   round(motor_temps[11], 2),

            # --- 四条腿状态 (0=正常/能读取电机温度, 1=异常) ---
            "left_front_leg_status":  lf_status,
            "left_back_leg_status":   lr_status,
            "right_front_leg_status": rf_status,
            "right_back_leg_status":  rr_status,

            # --- 板卡服务模块状态 ---
            # 5G 使用 int enum (0/1)
            "5g_module_status":         board.get("5g_module_status", 0),
            # 以下模块使用 string enum ("0"/"1")
            "bluetooth_module_status":  str(board.get("bluetooth_module_status", 0)),
            "navigation_module_status": str(board.get("navigation_module_status", 0)),
            "image_module_status":      str(board.get("image_module_status", 0)),
            "scheduling_module_status": str(board.get("scheduling_module_status", 0)),
            "voice_module_status":      str(board.get("voice_module_status", 0)),
        }
        
        return payload

    def _bridge_loop(self):
        """定期从ROS拿数据发布到MQTT的循环"""
        # 给 ROS 订阅收集数据一些预留时间
        time.sleep(1)
        
        while self.running:
            try:
                payload = self._build_payload()
                topic = MQTT_TOPIC
                
                # 发布到 MQTT
                self.mqtt_client.publish(topic, payload)
                
            except Exception as e:
                logger.error(f"桥接循环发生错误: {e}")
                
            # 物模型上报频率假设为 1Hz，可由业务需求自行改变
            time.sleep(1.0)


if __name__ == "__main__":
    import logging
    from utils.logger import setup_logger
    
    # 强制配置根日志处理器，覆盖 rospy 默认的日志拦截
    setup_logger("", level=logging.INFO)
    
    bridge = StateBridge()
    try:
        bridge.start()
        # 保持主线程存活
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户尝试退出...")
    except Exception as e:
        logger.error(f"启动失败: {e}")
    finally:
        bridge.stop()
        logger.info("程序已退出。")
