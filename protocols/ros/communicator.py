"""ROS通信模块"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    import rospy
except ImportError as e:
    raise ImportError("ROS未安装，无法使用ROS功能") from e

from utils import get_logger, setup_logger

logger = get_logger(__name__)


class ROSCommunicator:
    """ROS通信管理类 - 负责ROS节点初始化和话题管理"""

    def __init__(self, node_name: str = "robot_dog_server"):
        """
        初始化ROS通信

        Args:
            node_name: ROS节点名称
        """
        try:
            rospy.init_node(node_name, anonymous=True, disable_signals=True)
            logger.info(f"ROS节点初始化成功: {node_name}")
        except rospy.exceptions.ROSException as e:
            logger.warning(f"ROS节点可能已初始化: {e}")

        setup_logger("", level=logging.INFO)

        self.publishers: Dict[str, rospy.Publisher] = {}

        # 订阅器字典
        self.subscribers: Dict[str, rospy.Subscriber] = {}

        # 缓存最新的话题数据
        self.topic_data_cache: Dict[str, Any] = {}

        self.ros_spin_thread = None

        self.start_ros()

    def start_ros(self):
        """启动ROS通信 - 保持节点活跃"""
        logger.info("ROS通信已启动")
        self.ros_spin_thread = threading.Thread(target=rospy.spin, daemon=True)
        self.ros_spin_thread.start()
        # ROS节点在初始化时即开始运行，无需额外启动逻辑

    def create_publisher(
        self, topic: str, msg_type: type, queue_size: int = 10
    ) -> rospy.Publisher:
        """
        创建发布器

        Args:
            topic: 话题名称
            msg_type: 消息类型
            queue_size: 队列大小

        Returns:
            发布器对象
        """
        if topic not in self.publishers:
            pub = rospy.Publisher(topic, msg_type, queue_size=queue_size)
            self.publishers[topic] = pub
            logger.info(f"创建发布器: {topic} ({msg_type.__name__})")
            time.sleep(0.2)  # 新创建的发布器需要一点时间建立连接，避免第一条消息丢失
        return self.publishers[topic]

    def create_subscriber(
        self, topic: str, msg_type: type, callback: Optional[Callable] = None
    ) -> rospy.Subscriber:
        """
        创建订阅器

        Args:
            topic: 话题名称
            msg_type: 消息类型
            callback: 回调函数(可选，默认缓存数据)

        Returns:
            订阅器对象
        """
        if topic not in self.subscribers:
            if callback is None:
                # 默认回调：缓存数据
                callback = lambda msg: self._cache_topic_data(topic, msg)

            sub = rospy.Subscriber(topic, msg_type, callback)
            self.subscribers[topic] = sub
            logger.info(f"创建订阅器: {topic} ({msg_type.__name__})")
        return self.subscribers[topic]

    def _cache_topic_data(self, topic: str, data: Any):
        """缓存话题数据"""
        self.topic_data_cache[topic] = data

    def get_cached_data(self, topic: str) -> Optional[Any]:
        """获取缓存的话题数据"""
        return self.topic_data_cache.get(topic)

    def publish(self, topic: str, msg_type: type, data: Any) -> bool:
        """
        发布消息

        Args:
            topic: 话题名称
            msg_type: 消息类型
            data: 要发布的消息对象

        Returns:
            是否成功
        """
        try:
            pub = self.create_publisher(topic, msg_type)
            pub.publish(data)
            logger.debug(f"发布消息到话题: {topic}")
            return True
        except Exception as e:
            logger.error(f"发布消息失败 {topic}: {e}")
            return False

    def shutdown(self):
        """关闭ROS通信"""
        for topic, sub in self.subscribers.items():
            sub.unregister()
            logger.debug(f"取消订阅话题: {topic}")
        for topic, pub in self.publishers.items():
            pub.unregister()
            logger.debug(f"取消发布话题: {topic}")
        rospy.signal_shutdown("ROSCommunicator关闭")
        logger.info("ROS通信已关闭")
