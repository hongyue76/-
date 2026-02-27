"""
时间戳服务 - 确保LWW策略的时间准确性
"""

import time
import threading
from datetime import datetime
from typing import Dict, Optional

class TimestampService:
    """全局时间戳服务，确保严格的时序性"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_timestamp = 0
        self._sequence_counter = 0
        
    def get_timestamp(self) -> int:
        """
        获取严格递增的时间戳
        返回微秒级时间戳，保证单调递增
        """
        with self._lock:
            current_time = int(time.time() * 1000000)  # 微秒
            
            if current_time > self._last_timestamp:
                # 正常情况：当前时间大于上次时间戳
                self._last_timestamp = current_time
                self._sequence_counter = 0
            else:
                # 时间回退或相等：使用上次时间戳+序列号
                self._sequence_counter += 1
                self._last_timestamp += 1
                
            return self._last_timestamp
    
    def get_datetime_from_timestamp(self, timestamp: int) -> datetime:
        """将时间戳转换为datetime对象"""
        return datetime.fromtimestamp(timestamp / 1000000)
    
    def get_readable_timestamp(self) -> str:
        """获取人类可读的时间戳"""
        ts = self.get_timestamp()
        dt = self.get_datetime_from_timestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

# 全局时间戳服务实例
timestamp_service = TimestampService()

class LogicalClock:
    """逻辑时钟，用于分布式环境下的时序保证"""
    
    def __init__(self):
        self._clock = 0
        self._lock = threading.Lock()
        
    def tick(self) -> int:
        """时钟前进，返回新的时钟值"""
        with self._lock:
            self._clock += 1
            return self._clock
            
    def update(self, received_clock: int) -> int:
        """更新时钟到最大值"""
        with self._lock:
            self._clock = max(self._clock, received_clock) + 1
            return self._clock

# 逻辑时钟实例
logical_clock = LogicalClock()

def get_consistent_timestamp() -> Dict[str, any]:
    """
    获取一致性时间戳（包含物理时间和逻辑时间）
    """
    physical_ts = timestamp_service.get_timestamp()
    logical_ts = logical_clock.tick()
    
    return {
        "physical_timestamp": physical_ts,
        "logical_timestamp": logical_ts,
        "readable_time": timestamp_service.get_readable_timestamp()
    }

# 使用示例
if __name__ == "__main__":
    # 测试时间戳服务
    print("=== 时间戳服务测试 ===")
    
    timestamps = []
    for i in range(5):
        ts_info = get_consistent_timestamp()
        timestamps.append(ts_info)
        print(f"第{i+1}次: {ts_info['readable_time']} "
              f"(物理:{ts_info['physical_timestamp']}, 逻辑:{ts_info['logical_timestamp']})")
        
    print("\n=== 验证严格递增 ===")
    for i in range(1, len(timestamps)):
        prev = timestamps[i-1]
        curr = timestamps[i]
        assert curr['physical_timestamp'] > prev['physical_timestamp'], "时间戳未严格递增!"
    
    print("✓ 所有时间戳严格递增")