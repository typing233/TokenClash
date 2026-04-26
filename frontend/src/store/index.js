import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 用户状态
export const useUserStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        set({ token });
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
      },
      login: (user, token) => {
        set({ user, token, isAuthenticated: true });
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
      },
      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      },
      initializeFromStorage: () => {
        const token = localStorage.getItem('token');
        const userStr = localStorage.getItem('user');
        if (token && userStr) {
          try {
            const user = JSON.parse(userStr);
            set({ user, token, isAuthenticated: true });
          } catch (e) {
            console.error('Failed to parse user from storage:', e);
          }
        }
      },
    }),
    {
      name: 'user-storage',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);

// 辩论状态
export const useDebateStore = create((set, get) => ({
  currentDebate: null,
  messages: [],
  danmakus: [],
  stage: 'waiting',
  currentRound: 0,
  currentSpeaker: null,
  viewerCount: 0,
  isJoined: false,
  
  setCurrentDebate: (debate) => set({ currentDebate: debate }),
  setStage: (stage) => set({ stage }),
  setCurrentRound: (round) => set({ currentRound: round }),
  setCurrentSpeaker: (speaker) => set({ currentSpeaker: speaker }),
  setViewerCount: (count) => set({ viewerCount: count }),
  setIsJoined: (joined) => set({ isJoined: joined }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  setMessages: (messages) => set({ messages }),
  
  addDanmaku: (danmaku) => set((state) => ({
    danmakus: [...state.danmakus.slice(-100), danmaku]
  })),
  setDanmakus: (danmakus) => set({ danmakus }),
  
  clearDebate: () => set({
    currentDebate: null,
    messages: [],
    danmakus: [],
    stage: 'waiting',
    currentRound: 0,
    currentSpeaker: null,
    viewerCount: 0,
    isJoined: false,
  }),
}));

// 排行榜状态
export const useRankingStore = create((set, get) => ({
  overallRanking: [],
  categoryRankings: {},
  currentCategory: 'overall',
  isLoading: false,
  
  setOverallRanking: (ranking) => set({ overallRanking: ranking }),
  setCategoryRanking: (category, ranking) => set((state) => ({
    categoryRankings: { ...state.categoryRankings, [category]: ranking }
  })),
  setCurrentCategory: (category) => set({ currentCategory: category }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));

// 全局UI状态
export const useUIStore = create((set, get) => ({
  sidebarOpen: true,
  darkMode: true,
  notifications: [],
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
  
  addNotification: (notification) => set((state) => ({
    notifications: [...state.notifications, { ...notification, id: Date.now() }]
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter(n => n.id !== id)
  })),
  clearNotifications: () => set({ notifications: [] }),
}));
