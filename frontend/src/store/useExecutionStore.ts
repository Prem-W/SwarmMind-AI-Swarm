import { create } from 'zustand';

export interface ExecutionLog {
  id: string;
  timestamp: string;
  level: string;
  event_type: string;
  message: string;
  agent_id?: string;
  task_id?: string;
  details: Record<string, unknown>;
}

interface ExecutionState {
  logs: ExecutionLog[];
  isConnected: boolean;
  socket: WebSocket | null;
  connect: (executionId: string) => void;
  disconnect: () => void;
  sendMessage: (msg: Record<string, unknown>) => void;
  clearLogs: () => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'ws://localhost:8000';

const getToken = () => {
  const state = JSON.parse(localStorage.getItem('swarmmind-auth') || '{}');
  return state.state?.token;
};

export const useExecutionStore = create<ExecutionState>((set, get) => ({
  logs: [],
  isConnected: false,
  socket: null,

  connect: (executionId: string) => {
    const wsUrl = API_URL.replace(/^http/, 'ws');
    const socket = new WebSocket(`${wsUrl}/api/v1/ws/execution/${executionId}?token=${getToken()}`);

    socket.onopen = () => {
      set({ isConnected: true, socket });
      socket.send(JSON.stringify({ type: 'ping' }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'execution_event' || data.type === 'execution_update') {
        set((state) => ({
          logs: [...state.logs, {
            id: crypto.randomUUID(),
            timestamp: data.timestamp || new Date().toISOString(),
            level: data.event?.level || 'INFO',
            event_type: data.event?.event_type || 'update',
            message: data.event?.message || JSON.stringify(data),
            details: data.event?.details || data,
          }],
        }));
      }
    };

    socket.onclose = () => {
      set({ isConnected: false, socket: null });
    };

    socket.onerror = () => {
      set({ isConnected: false, socket: null });
    };
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.close();
      set({ isConnected: false, socket: null });
    }
  },

  sendMessage: (msg) => {
    const { socket } = get();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(msg));
    }
  },

  clearLogs: () => set({ logs: [] }),
}));
