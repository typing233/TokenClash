from typing import Dict, Set, Optional
from datetime import datetime
import socketio


class SocketManager:
    """Socket.IO连接管理器"""
    
    def __init__(self):
        # 存储辩论房间的用户
        self.debate_rooms: Dict[str, Set[str]] = {}  # {debate_id: {sid1, sid2, ...}}
        
        # 存储用户所在的房间
        self.user_rooms: Dict[str, str] = {}  # {sid: debate_id}
        
        # 存储用户信息
        self.user_info: Dict[str, Dict] = {}  # {sid: {"user_id": ..., "user_name": ...}}
    
    def join_debate_room(self, sid: str, debate_id: str, user_info: Optional[Dict] = None):
        """
        用户加入辩论房间
        
        Args:
            sid: 用户的Socket.IO SID
            debate_id: 辩论ID
            user_info: 用户信息（可选）
        """
        # 记录辩论房间
        if debate_id not in self.debate_rooms:
            self.debate_rooms[debate_id] = set()
        self.debate_rooms[debate_id].add(sid)
        
        # 记录用户所在房间
        self.user_rooms[sid] = debate_id
        
        # 记录用户信息
        if user_info:
            self.user_info[sid] = user_info
    
    def leave_debate_room(self, sid: str) -> Optional[str]:
        """
        用户离开辩论房间
        
        Args:
            sid: 用户的Socket.IO SID
        
        Returns:
            离开的辩论ID，如果没有加入任何房间则返回None
        """
        debate_id = self.user_rooms.get(sid)
        
        if debate_id:
            # 从辩论房间移除
            if debate_id in self.debate_rooms:
                self.debate_rooms[debate_id].discard(sid)
                
                # 如果房间为空，删除房间记录
                if not self.debate_rooms[debate_id]:
                    del self.debate_rooms[debate_id]
            
            # 从用户房间记录移除
            del self.user_rooms[sid]
        
        # 移除用户信息
        if sid in self.user_info:
            del self.user_info[sid]
        
        return debate_id
    
    def get_room_viewers(self, debate_id: str) -> int:
        """
        获取辩论房间的观众数量
        
        Args:
            debate_id: 辩论ID
        
        Returns:
            观众数量
        """
        if debate_id in self.debate_rooms:
            return len(self.debate_rooms[debate_id])
        return 0
    
    def get_user_debate(self, sid: str) -> Optional[str]:
        """
        获取用户所在的辩论ID
        
        Args:
            sid: 用户的Socket.IO SID
        
        Returns:
            辩论ID，如果没有加入任何房间则返回None
        """
        return self.user_rooms.get(sid)
    
    def get_user_info(self, sid: str) -> Optional[Dict]:
        """
        获取用户信息
        
        Args:
            sid: 用户的Socket.IO SID
        
        Returns:
            用户信息
        """
        return self.user_info.get(sid)
    
    def get_all_active_debates(self) -> Dict[str, int]:
        """
        获取所有活跃的辩论及其观众数量
        
        Returns:
            {debate_id: viewer_count}
        """
        return {
            debate_id: len(viewers)
            for debate_id, viewers in self.debate_rooms.items()
        }
    
    def set_user_info(self, sid: str, user_info: Dict):
        """
        设置用户信息
        
        Args:
            sid: 用户的Socket.IO SID
            user_info: 用户信息
        """
        self.user_info[sid] = user_info


# 创建全局Socket管理器实例
socket_manager = SocketManager()


def get_socket_manager() -> SocketManager:
    """获取Socket管理器实例"""
    return socket_manager
