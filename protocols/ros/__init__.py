"""ROS协议模块 - 可选加载

注意: ROS模块是可选的，如果系统没有ROS环境，可以正常运行UDP功能
"""

# 尝试导入ROS相关模块
ROS_AVAILABLE = False
try:
    import rospy

    from .communicator import ROSCommunicator
    from .controller import RobotDogROSController
    from .state_mapper import StateMapper

    ROS_AVAILABLE = True

    __all__ = [
        "ROS_AVAILABLE",
        "ROSCommunicator",
        "RobotDogROSController",
        "StateMapper",
    ]
except ImportError as e:
    import warnings

    warnings.warn(
        f"ROS模块不可用: {e}. 系统将仅使用UDP功能。如需ROS功能，请安装ROS环境。",
        ImportWarning,
    )

    # 提供占位符类
    class ROSCommunicator:
        def __init__(self, *args, **kwargs):
            raise ImportError("ROS未安装，无法使用ROS功能")

    class RobotDogROSController:
        def __init__(self, *args, **kwargs):
            raise ImportError("ROS未安装，无法使用ROS功能")

    class StateMapper:
        pass

    __all__ = [
        "ROS_AVAILABLE",
        "ROSCommunicator",
        "RobotDogROSController",
        "StateMapper",
    ]
