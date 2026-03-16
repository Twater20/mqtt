#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 RK3588 板卡各模块运行状态检查工具

检测方式概览：
  - 5G 模块      → 检查网卡 wwan0_1 是否获取到 IPv4 地址
  - 蓝牙模块    → systemd 服务 + 进程 + HCI 硬件适配器
  - 导航模块    → ping 导航设备 192.168.1.106
  - 图像模块    → ping 网络摄像头 192.168.1.64
  - 调度模块    → 默认强制正常（无需检测）
  - 语音模块    → ALSA 麦克风(XFMDPV0018) + 扬声器(rockchipes8388) 都就绪才算正常

对外接口：
  get_all_module_status()   → 返回所有模块状态的字典
  get_xxx_module_status()   → 返回单个模块状态 (0=正常, 1=异常)
"""

import os
import time
import shutil
import subprocess
from typing import Dict, Any, List, Optional, Tuple


# =========================================================
# 配置区：按实际板卡环境修改
# =========================================================
CONFIG = {
    "5g": {
        # 通过 ip addr show 查看 wwan0_1 是否有 IPv4 地址
        "net_iface": "wwan0_1",
    },
    "bluetooth": {
        # systemctl is-active 检查服务 + pgrep 检查进程 + hciconfig 检查硬件
        "systemd_services": ["bluetooth.service"],
        "process_keywords": ["bluetoothd"],
        "check_hci": True,
    },
    "navigation": {
        # ping 导航设备判断是否在线
        "ping_hosts": ["192.168.1.106"],
    },
    "image": {
        # ping 网络摄像头判断是否在线
        "ping_hosts": ["192.168.1.64"],
    },
    "scheduling": {
        # 调度模块无需检测，默认上报正常
        "always_ok": True,
    },
    "voice": {
        # 通过 arecord -l / aplay -l 检查麦克风和扬声器是否都存在（两个都就绪才算正常）
        "alsa_devices": ["XFMDPV0018", "rockchipes8388"],
    },
}


# =========================================================
# 底层检测工具类
# =========================================================
class _Checker:
    """封装各种系统探测方法，供 evaluate_module 调用"""

    @staticmethod
    def run_cmd(cmd: List[str], timeout: float = 3.0) -> Tuple[int, str]:
        """执行系统命令，返回 (返回码, stdout)"""
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, timeout=timeout)
            return p.returncode, p.stdout.strip()
        except Exception:
            return -1, ""

    @staticmethod
    def which(cmd: str) -> bool:
        """检查命令是否存在于 PATH 中"""
        return shutil.which(cmd) is not None

    @classmethod
    def systemd_active(cls, services: List[str]) -> Optional[str]:
        """通过 systemctl is-active 逐个检查服务列表，返回第一个 active 的服务名"""
        if not cls.which("systemctl") or not services:
            return None
        for s in services:
            code, out = cls.run_cmd(["systemctl", "is-active", s], timeout=2.0)
            if code == 0 and out == "active":
                return s
        return None

    @classmethod
    def process_alive(cls, keywords: List[str]) -> Optional[str]:
        """通过 pgrep（或 fallback ps -ef）按关键词搜索后台进程"""
        if not keywords:
            return None
        # 优先用 pgrep
        if cls.which("pgrep"):
            for kw in keywords:
                code, out = cls.run_cmd(["pgrep", "-fa", kw], timeout=2.0)
                if code == 0 and out:
                    return kw
        # fallback: ps -ef 全量搜索
        code, out = cls.run_cmd(["ps", "-ef"], timeout=3.0)
        if code == 0:
            for line in out.splitlines():
                for kw in keywords:
                    if kw in line and "grep" not in line and "pgrep" not in line:
                        return kw
        return None

    @classmethod
    def iface_ipv4(cls, iface: str) -> Optional[str]:
        """通过 ip -4 addr show 检查网卡是否获得了 IPv4 地址"""
        if not iface:
            return None
        code, out = cls.run_cmd(["ip", "-4", "addr", "show", iface], timeout=2.0)
        if code == 0 and out:
            for line in out.splitlines():
                if line.strip().startswith("inet "):
                    return line.strip().split()[1].split("/")[0]
        return None

    @classmethod
    def ping_ok(cls, host: str) -> bool:
        """ping -c1 -W1 检测目标主机是否可达"""
        code, _ = cls.run_cmd(["ping", "-c", "1", "-W", "1", host], timeout=2.0)
        return code == 0

    @classmethod
    def bluetooth_hci(cls) -> Optional[str]:
        """通过 hciconfig 或 /sys/class/bluetooth 检查蓝牙硬件适配器"""
        if cls.which("hciconfig"):
            code, out = cls.run_cmd(["hciconfig"], timeout=2.0)
            if code == 0 and out.strip():
                return out.splitlines()[0]
        elif os.path.exists("/sys/class/bluetooth"):
            items = os.listdir("/sys/class/bluetooth")
            if items:
                return ",".join(items)
        return None

    @classmethod
    def alsa_device_exists(cls, keyword: str) -> bool:
        """
        检查 ALSA 音频设备是否存在：
        1. arecord -l 查录音设备
        2. aplay -l   查播放设备
        3. /proc/asound/cards 兜底
        """
        for cmd in [["arecord", "-l"], ["aplay", "-l"], ["cat", "/proc/asound/cards"]]:
            code, out = cls.run_cmd(cmd, timeout=2.0)
            if code == 0 and keyword in out:
                return True
        return False


# =========================================================
# 统一检测入口
# =========================================================
def evaluate_module(module_name: str, config: dict) -> Dict[str, Any]:
    """
    根据 CONFIG 中的配置字段，自动选择对应的检测方法。
    返回 {"status": 0|1, "detail": {..., "reason": [...]}}
    """
    reasons: List[str] = []
    detail: Dict[str, Any] = {}
    strict_fail = False  # 标记关键设备缺失（如 ALSA 设备必须全部就绪）

    # ---------- 5G 网卡检测（特例，直接返回） ----------
    if module_name == "5g":
        iface = config.get("net_iface", "wwan0_1")
        ip_addr = _Checker.iface_ipv4(iface)
        ok = ip_addr is not None
        detail = {"iface": iface, "ip_addr": ip_addr}
        reasons.append(f"{iface} IP存在: {ip_addr}" if ok else f"{iface} 不存在IP")
        return {"status": 0 if ok else 1, "detail": {**detail, "reason": reasons}}

    # ---------- 默认强制正常 ----------
    if config.get("always_ok"):
        reasons.append("配置为默认强制正常")
        detail["always_ok"] = True

    # ---------- systemd 服务检测 ----------
    svc = _Checker.systemd_active(config.get("systemd_services", []))
    if svc:
        reasons.append(f"服务运行中: {svc}")
        detail["service_active"] = svc

    # ---------- 进程关键词检测 ----------
    proc = _Checker.process_alive(config.get("process_keywords", []))
    if proc:
        reasons.append(f"进程存在: {proc}")
        detail["process_found"] = proc

    # ---------- 蓝牙 HCI 硬件检测 ----------
    if config.get("check_hci"):
        hci = _Checker.bluetooth_hci()
        if hci:
            reasons.append("蓝牙HCI就绪")
            detail["hci_info"] = hci

    # ---------- Ping 网络设备检测 ----------
    for host in config.get("ping_hosts", []):
        if _Checker.ping_ok(host):
            reasons.append(f"网络设备在线: {host}")
            detail["ping_ok"] = host

    # ---------- ALSA 音频设备检测（必须全部就绪） ----------
    for dev_kw in config.get("alsa_devices", []):
        if _Checker.alsa_device_exists(dev_kw):
            reasons.append(f"音频设备就绪: {dev_kw}")
            detail[f"alsa_{dev_kw}"] = True
        else:
            detail[f"alsa_{dev_kw}"] = False
            strict_fail = True  # 任何一个设备缺失即判定异常

    # ---------- 最终判定 ----------
    ok = bool(reasons) and not strict_fail
    if not ok:
        reasons.append(f"未发现 {module_name} 模块正常运行证据，或关键设备缺失")

    detail["reason"] = reasons
    return {"status": 0 if ok else 1, "detail": detail}


# =========================================================
# 对外函数接口（返回 0=正常, 1=异常）
# =========================================================

def get_5g_module_status() -> int:
    return evaluate_module("5g", CONFIG["5g"])["status"]

def get_bluetooth_module_status() -> int:
    return evaluate_module("bluetooth", CONFIG["bluetooth"])["status"]

def get_navigation_module_status() -> int:
    return evaluate_module("navigation", CONFIG["navigation"])["status"]

def get_image_module_status() -> int:
    return evaluate_module("image", CONFIG["image"])["status"]

def get_scheduling_module_status() -> int:
    return evaluate_module("scheduling", CONFIG["scheduling"])["status"]

def get_voice_module_status() -> int:
    return evaluate_module("voice", CONFIG["voice"])["status"]

def get_all_module_status() -> Dict[str, Any]:
    """获取所有模块的全面诊断报告"""
    results = {name: evaluate_module(name, cfg) for name, cfg in CONFIG.items()}
    return {
        "timestamp": int(time.time()),
        **{f"{name}_module_status": r["status"] for name, r in results.items()},
        "detail": {name: r["detail"] for name, r in results.items()},
    }


# =========================================================
# 本地测试入口
# =========================================================
if __name__ == "__main__":
    import json
    print(json.dumps(get_all_module_status(), ensure_ascii=False, indent=2))