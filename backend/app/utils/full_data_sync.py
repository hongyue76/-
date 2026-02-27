"""
全量数据同步服务
处理用户首次登录或清空缓存后的数据拉取
"""

import asyncio
from typing import List, Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SyncEntity:
    """同步实体"""
    entity_type: str  # todos, comments, assignments, shared_lists
    endpoint: str     # API端点
    local_store_key: str  # 本地存储键名
    batch_size: int = 100

@dataclass
class FullSyncProgress:
    """全量同步进度"""
    total_entities: int
    completed_entities: int
    current_entity: Optional[str] = None
    current_page: int = 0
    total_pages: int = 0
    percentage: float = 0.0
    is_background: bool = True

class FullDataSyncService:
    """全量数据同步服务"""
    
    def __init__(self):
        self.entities = [
            SyncEntity("todos", "/api/todos", "todos", 50),
            SyncEntity("comments", "/api/comments", "comments", 100),
            SyncEntity("assignments", "/api/task-assignments", "assignments", 50),
            SyncEntity("shared_lists", "/api/shared-lists", "sharedLists", 20),
            SyncEntity("list_members", "/api/shared-lists/members", "listMembers", 50)
        ]
        
        self.progress = FullSyncProgress(
            total_entities=len(self.entities),
            completed_entities=0
        )
        
        self.callbacks = {
            'progress': [],
            'complete': [],
            'error': [],
            'entity_start': [],
            'entity_complete': []
        }
        
        self.is_syncing = False
        self.background_sync_task = None
    
    def add_callback(self, event_type: str, callback: Callable):
        """添加事件回调"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def remove_callback(self, event_type: str, callback: Callable):
        """移除事件回调"""
        if event_type in self.callbacks:
            self.callbacks[event_type] = [
                cb for cb in self.callbacks[event_type] if cb != callback
            ]
    
    async def start_full_sync(
        self, 
        api_client,
        local_storage,
        background: bool = True,
        incremental_only: bool = False
    ):
        """开始全量同步"""
        if self.is_syncing:
            logger.warning("同步已在进行中")
            return False
        
        self.is_syncing = True
        self.progress.is_background = background
        
        try:
            if not incremental_only:
                # 清空本地数据（首次同步）
                await self._clear_local_data(local_storage)
            
            # 执行同步
            await self._execute_sync(api_client, local_storage)
            
            self._notify_complete()
            return True
            
        except Exception as e:
            logger.error(f"全量同步失败: {e}")
            self._notify_error(str(e))
            return False
        finally:
            self.is_syncing = False
    
    async def _clear_local_data(self, local_storage):
        """清空本地数据"""
        for entity in self.entities:
            await local_storage.removeItem(entity.local_store_key)
            logger.info(f"已清空本地 {entity.entity_type} 数据")
    
    async def _execute_sync(self, api_client, local_storage):
        """执行同步逻辑"""
        for i, entity in enumerate(self.entities):
            if not self.is_syncing:  # 允许中断
                break
            
            self.progress.current_entity = entity.entity_type
            self.progress.current_page = 0
            self.progress.total_pages = 0
            
            self._notify_entity_start(entity.entity_type)
            
            try:
                await self._sync_entity(entity, api_client, local_storage)
                self.progress.completed_entities = i + 1
                self.progress.percentage = (i + 1) / len(self.entities) * 100
                
                self._notify_entity_complete(entity.entity_type)
                self._notify_progress()
                
            except Exception as e:
                logger.error(f"同步实体 {entity.entity_type} 失败: {e}")
                # 继续同步其他实体
                continue
    
    async def _sync_entity(self, entity: SyncEntity, api_client, local_storage):
        """同步单个实体"""
        all_data = []
        page = 1
        
        while True:
            # 分页获取数据
            response = await api_client.get(
                f"{entity.endpoint}?page={page}&size={entity.batch_size}"
            )
            
            if response.status_code != 200:
                raise Exception(f"获取 {entity.entity_type} 数据失败: {response.status_code}")
            
            data = response.json()
            items = data.get('items', []) if isinstance(data, dict) else data
            
            if not items:
                break
            
            all_data.extend(items)
            
            # 更新进度
            self.progress.current_page = page
            self.progress.total_pages = data.get('total_pages', page)
            self._notify_progress()
            
            # 如果是最后一页，跳出循环
            if len(items) < entity.batch_size:
                break
                
            page += 1
            
            # 后台同步时添加延迟，避免影响其他操作
            if self.progress.is_background:
                await asyncio.sleep(0.1)  # 100ms延迟
        
        # 保存到本地存储
        await local_storage.setItem(entity.local_store_key, all_data)
        logger.info(f"已同步 {len(all_data)} 条 {entity.entity_type} 数据")
    
    def cancel_sync(self):
        """取消同步"""
        self.is_syncing = False
        if self.background_sync_task:
            self.background_sync_task.cancel()
    
    def get_progress(self) -> FullSyncProgress:
        """获取当前进度"""
        return self.progress
    
    def is_currently_syncing(self) -> bool:
        """检查是否正在同步"""
        return self.is_syncing
    
    def _notify_progress(self):
        """通知进度更新"""
        for callback in self.callbacks['progress']:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"进度回调错误: {e}")
    
    def _notify_complete(self):
        """通知同步完成"""
        for callback in self.callbacks['complete']:
            try:
                callback()
            except Exception as e:
                logger.error(f"完成回调错误: {e}")
    
    def _notify_error(self, error_message: str):
        """通知错误"""
        for callback in self.callbacks['error']:
            try:
                callback(error_message)
            except Exception as e:
                logger.error(f"错误回调错误: {e}")
    
    def _notify_entity_start(self, entity_type: str):
        """通知实体开始同步"""
        for callback in self.callbacks['entity_start']:
            try:
                callback(entity_type)
            except Exception as e:
                logger.error(f"实体开始回调错误: {e}")
    
    def _notify_entity_complete(self, entity_type: str):
        """通知实体同步完成"""
        for callback in self.callbacks['entity_complete']:
            try:
                callback(entity_type)
            except Exception as e:
                logger.error(f"实体完成回调错误: {e}")

class IncrementalSyncScheduler:
    """增量同步调度器"""
    
    def __init__(self, full_sync_service: FullDataSyncService):
        self.full_sync_service = full_sync_service
        self.last_sync_time = None
        self.sync_interval = 300  # 5分钟检查一次
    
    async def schedule_incremental_sync(self, api_client, local_storage):
        """调度增量同步"""
        while True:
            try:
                # 检查是否需要同步
                if await self._should_sync():
                    # 执行增量同步而不是全量同步
                    await self._perform_incremental_sync(api_client, local_storage)
                
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"增量同步调度失败: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
    
    async def _should_sync(self) -> bool:
        """判断是否需要同步"""
        if not self.last_sync_time:
            return True
        
        # 检查距离上次同步是否超过间隔时间
        time_since_last = (datetime.now() - self.last_sync_time).total_seconds()
        return time_since_last >= self.sync_interval
    
    async def _perform_incremental_sync(self, api_client, local_storage):
        """执行增量同步"""
        # 这里可以实现更智能的增量同步逻辑
        # 例如：只同步自上次同步以来发生变化的数据
        
        logger.info("执行增量同步检查...")
        self.last_sync_time = datetime.now()

# 使用示例
async def demo_full_sync():
    """演示全量同步"""
    print("=== 全量数据同步演示 ===\n")
    
    # 模拟服务
    sync_service = FullDataSyncService()
    
    # 进度回调
    def on_progress(progress):
        bar_length = 30
        filled_length = int(bar_length * progress.percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        entity_info = f" ({progress.current_entity})" if progress.current_entity else ""
        page_info = f" [{progress.current_page}/{progress.total_pages}]" if progress.total_pages > 0 else ""
        
        print(f"\r[{bar}] {progress.percentage:.1f}%{entity_info}{page_info}", end='', flush=True)
    
    def on_complete():
        print("\n✅ 全量同步完成!")
    
    def on_error(error):
        print(f"\n❌ 同步错误: {error}")
    
    def on_entity_start(entity_type):
        print(f"\n📥 开始同步 {entity_type}...")
    
    def on_entity_complete(entity_type):
        print(f" ✅ {entity_type} 同步完成")
    
    # 注册回调
    sync_service.add_callback('progress', on_progress)
    sync_service.add_callback('complete', on_complete)
    sync_service.add_callback('error', on_error)
    sync_service.add_callback('entity_start', on_entity_start)
    sync_service.add_callback('entity_complete', on_entity_complete)
    
    # 模拟API客户端和本地存储
    class MockApiClient:
        async def get(self, url):
            # 模拟API响应
            await asyncio.sleep(0.1)  # 模拟网络延迟
            return type('Response', (), {
                'status_code': 200,
                'json': lambda: {
                    'items': [{'id': i, 'title': f'Item {i}'} for i in range(10)],
                    'total_pages': 1
                }
            })()
    
    class MockLocalStorage:
        async def setItem(self, key, value):
            print(f"  保存 {len(value)} 条 {key} 数据到本地")
        
        async def removeItem(self, key):
            print(f"  清空本地 {key} 数据")
    
    # 开始同步
    print("开始全量数据同步...")
    await sync_service.start_full_sync(
        MockApiClient(),
        MockLocalStorage(),
        background=True
    )

if __name__ == "__main__":
    asyncio.run(demo_full_sync())