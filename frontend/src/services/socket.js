import { io } from 'socket.io-client';

class SocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.eventListeners = new Map();
  }

  connect() {
    if (this.socket && this.isConnected) {
      return this.socket;
    }

    // 创建Socket.IO连接
    this.socket = io({
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    // 连接事件
    this.socket.on('connect', () => {
      this.isConnected = true;
      console.log('Socket connected:', this.socket.id);
      this.emit('connected', { sid: this.socket.id });
    });

    this.socket.on('disconnect', () => {
      this.isConnected = false;
      console.log('Socket disconnected');
      this.emit('disconnected', {});
    });

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      this.emit('error', { message: error.message });
    });

    // 通用事件转发
    this.socket.onAny((event, ...args) => {
      this.emit(event, ...args);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }

  // 加入辩论房间
  joinDebate(debateId) {
    if (!this.socket) {
      this.connect();
    }
    this.socket.emit('join_debate', { debate_id: debateId });
  }

  // 离开辩论房间
  leaveDebate(debateId) {
    if (this.socket) {
      this.socket.emit('leave_debate', { debate_id: debateId });
    }
  }

  // 发送弹幕
  sendDanmaku(data) {
    if (this.socket) {
      this.socket.emit('send_danmaku', data);
    }
  }

  // 获取最近消息
  getRecentMessages(debateId, limit = 50) {
    if (this.socket) {
      this.socket.emit('get_recent_messages', { debate_id: debateId, limit });
    }
  }

  // 事件监听
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);

    // 同时添加到socket的监听
    if (this.socket) {
      this.socket.on(event, callback);
    }

    return () => this.off(event, callback);
  }

  off(event, callback) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }

    if (this.socket) {
      this.socket.off(event, callback);
    }
  }

  emit(event, ...args) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(...args);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }

    // 同时通过socket发送
    if (this.socket && this.isConnected) {
      this.socket.emit(event, ...args);
    }
  }

  // 获取当前连接状态
  getConnectionState() {
    return {
      isConnected: this.isConnected,
      id: this.socket?.id || null,
    };
  }
}

// 创建全局实例
const socketService = new SocketService();

export default socketService;
