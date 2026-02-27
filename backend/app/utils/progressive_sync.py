"""
渐进式数据同步服务
处理大量离线数据的分批加载和进度显示
"""

import asyncio
import math
from typing import List, Dict, Callable, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class SyncBatch:
    """同步批次"""
    batch_id: int
    items: List[Dict]
    total_items: int
    processed: int = 0
    status: str = "pending"  # pending, processing, completed, failed

@dataclass
class SyncProgress:
    """同步进度"""
    total_items: int
    completed_items: int
    current_batch: int
    total_batches: int
    percentage: float
    estimated_time: Optional[float] = None
    speed: Optional[float] = None  # items/second

class ProgressiveSyncService:
    """渐进式同步服务"""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        self.is_syncing = False
        self.current_progress = None
    
    def add_progress_listener(self, callback: Callable):
        """添加进度监听器"""
        self.progress_callbacks.append(callback)
    
    def add_completion_listener(self, callback: Callable):
        """添加完成监听器"""
        self.completion_callbacks.append(callback)
    
    def add_error_listener(self, callback: Callable):
        """添加错误监听器"""
        self.error_callbacks.append(callback)
    
    async def sync_large_dataset(
        self, 
        data_items: List[Dict], 
        process_item_func: Callable,
        delay_between_batches: float = 0.1
    ):
        """同步大数据集"""
        if self.is_syncing:
            raise RuntimeError("同步已在进行中")
        
        self.is_syncing = True
        start_time = datetime.now()
        
        try:
            # 计算批次信息
            total_items = len(data_items)
            total_batches = math.ceil(total_items / self.batch_size)
            
            # 初始化进度
            self.current_progress = SyncProgress(
                total_items=total_items,
                completed_items=0,
                current_batch=0,
                total_batches=total_batches,
                percentage=0.0
            )
            
            self._notify_progress()
            
            # 分批处理
            for batch_index in range(total_batches):
                if not self.is_syncing:  # 允许中断
                    break
                
                # 计算当前批次
                start_idx = batch_index * self.batch_size
                end_idx = min(start_idx + self.batch_size, total_items)
                batch_items = data_items[start_idx:end_idx]
                
                batch = SyncBatch(
                    batch_id=batch_index + 1,
                    items=batch_items,
                    total_items=len(batch_items),
                    status="processing"
                )
                
                # 更新进度
                self.current_progress.current_batch = batch_index + 1
                self._notify_progress()
                
                # 处理当前批次
                try:
                    await self._process_batch(batch, process_item_func)
                    
                    # 更新总体进度
                    self.current_progress.completed_items += len(batch_items)
                    self.current_progress.percentage = (
                        self.current_progress.completed_items / self.current_progress.total_items
                    ) * 100
                    
                    # 计算速度和预计剩余时间
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    if elapsed_time > 0:
                        speed = self.current_progress.completed_items / elapsed_time
                        self.current_progress.speed = speed
                        remaining_items = self.current_progress.total_items - self.current_progress.completed_items
                        self.current_progress.estimated_time = remaining_items / speed if speed > 0 else None
                    
                    batch.status = "completed"
                    self._notify_progress()
                    
                    # 批次间短暂延迟，避免UI阻塞
                    if batch_index < total_batches - 1:  # 不是最后一个批次
                        await asyncio.sleep(delay_between_batches)
                        
                except Exception as e:
                    batch.status = "failed"
                    self._notify_error(f"批次 {batch.batch_id} 处理失败: {str(e)}")
                    # 继续处理下一个批次而不是中断整个同步
                    continue
            
            # 同步完成
            self.is_syncing = False
            if self.current_progress.completed_items == self.current_progress.total_items:
                self._notify_completion()
            else:
                self._notify_error("同步未完成，部分数据处理失败")
                
        except Exception as e:
            self.is_syncing = False
            self._notify_error(f"同步过程中发生错误: {str(e)}")
    
    async def _process_batch(self, batch: SyncBatch, process_item_func: Callable):
        """处理单个批次"""
        semaphore = asyncio.Semaphore(10)  # 限制并发数
        
        async def process_single_item(item):
            async with semaphore:
                try:
                    await process_item_func(item)
                    batch.processed += 1
                except Exception as e:
                    print(f"处理项目失败: {e}")
                    # 不抛出异常，继续处理其他项目
        
        # 并发处理批次内的项目
        tasks = [process_single_item(item) for item in batch.items]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def cancel_sync(self):
        """取消当前同步"""
        self.is_syncing = False
    
    def get_current_progress(self) -> Optional[SyncProgress]:
        """获取当前进度"""
        return self.current_progress
    
    def _notify_progress(self):
        """通知进度更新"""
        if self.current_progress:
            for callback in self.progress_callbacks:
                try:
                    callback(self.current_progress)
                except Exception as e:
                    print(f"进度回调错误: {e}")
    
    def _notify_completion(self):
        """通知同步完成"""
        for callback in self.completion_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"完成回调错误: {e}")
    
    def _notify_error(self, error_message: str):
        """通知错误"""
        for callback in self.error_callbacks:
            try:
                callback(error_message)
            except Exception as e:
                print(f"错误回调错误: {e}")

class BatchUpdateManager:
    """批量更新管理器"""
    
    def __init__(self):
        self.pending_updates = []
        self.is_processing = False
        self.update_interval = 100  # 毫秒
        self.max_batch_size = 100
    
    def queue_update(self, update_data: Dict):
        """排队更新"""
        self.pending_updates.append(update_data)
        
        # 如果不是正在处理且队列达到阈值，则开始处理
        if not self.is_processing and len(self.pending_updates) >= self.max_batch_size:
            asyncio.create_task(self._process_updates())
    
    async def _process_updates(self):
        """处理排队的更新"""
        if self.is_processing:
            return
            
        self.is_processing = True
        
        try:
            while self.pending_updates:
                # 取出一批更新
                batch = self.pending_updates[:self.max_batch_size]
                self.pending_updates = self.pending_updates[self.max_batch_size:]
                
                # 批量应用更新
                await self._apply_batch_updates(batch)
                
                # 短暂休息，让UI有机会更新
                await asyncio.sleep(self.update_interval / 1000)
                
        finally:
            self.is_processing = False
    
    async def _apply_batch_updates(self, updates: List[Dict]):
        """应用批量更新到UI"""
        # 这里应该调用实际的UI更新方法
        # 例如：更新Vue store或触发React状态更新
        
        # 模拟批量更新
        print(f"应用 {len(updates)} 个批量更新")
        
        # 实际应用中应该是类似这样的代码：
        # store.commit('ADD_BATCH_TASKS', updates)
        # 或者
        # this.$emit('batch-update', updates)

# 使用示例和测试
async def demo_progressive_sync():
    """演示渐进式同步"""
    print("=== 渐进式同步演示 ===\n")
    
    # 模拟大量数据
    large_dataset = [
        {"id": i, "title": f"任务 {i}", "content": f"内容 {i}"}
        for i in range(1, 201)  # 200个任务
    ]
    
    # 创建同步服务
    sync_service = ProgressiveSyncService(batch_size=25)
    
    # 进度回调
    def on_progress(progress: SyncProgress):
        bar_length = 30
        filled_length = int(bar_length * progress.percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        speed_info = f" ({progress.speed:.1f}项/秒)" if progress.speed else ""
        time_info = f" 预计剩余: {progress.estimated_time:.0f}秒" if progress.estimated_time else ""
        
        print(f"\r批次 {progress.current_batch}/{progress.total_batches} "
              f"[{bar}] {progress.percentage:.1f}% "
              f"({progress.completed_items}/{progress.total_items})"
              f"{speed_info}{time_info}", end='', flush=True)
    
    def on_complete():
        print("\n✅ 同步完成!")
    
    def on_error(error):
        print(f"\n❌ 同步错误: {error}")
    
    # 注册回调
    sync_service.add_progress_listener(on_progress)
    sync_service.add_completion_listener(on_complete)
    sync_service.add_error_listener(on_error)
    
    # 模拟处理函数
    async def process_item(item):
        # 模拟处理耗时
        await asyncio.sleep(0.01)  # 10ms per item
        # 实际应用中这里是真正的数据处理逻辑
        pass
    
    # 开始同步
    print("开始同步 200 个项目...")
    await sync_service.sync_large_dataset(
        large_dataset, 
        process_item,
        delay_between_batches=0.05  # 50ms 批次间隔
    )

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_progressive_sync())