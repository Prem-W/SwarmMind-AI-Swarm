import { create } from 'zustand';

export interface Agent {
  id: string;
  name: string;
  description?: string;
  agent_type: string;
  status: 'idle' | 'busy' | 'paused' | 'error' | 'offline' | 'leader';
  team_id: string;
  llm_provider: string;
  llm_model: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  capabilities: string[];
  total_tasks_completed: number;
  total_tasks_failed: number;
  is_active: boolean;
  created_at: string;
}

interface AgentState {
  agents: Agent[];
  selectedAgent: Agent | null;
  isLoading: boolean;
  error: string | null;
  fetchAgents: (filters?: Record<string, string>) => Promise<void>;
  createAgent: (agent: Partial<Agent>) => Promise<void>;
  updateAgent: (id: string, updates: Partial<Agent>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  selectAgent: (agent: Agent | null) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getToken = () => {
  const state = JSON.parse(localStorage.getItem('swarmmind-auth') || '{}');
  return state.state?.token;
};

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  selectedAgent: null,
  isLoading: false,
  error: null,

  fetchAgents: async (filters = {}) => {
    set({ isLoading: true, error: null });
    try {
      const params = new URLSearchParams(filters);
      const res = await fetch(`${API_URL}/api/v1/agents?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      set({ agents: data, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createAgent: async (agent) => {
    const res = await fetch(`${API_URL}/api/v1/agents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(agent),
    });
    if (!res.ok) throw new Error('Failed to create agent');
    await get().fetchAgents();
  },

  updateAgent: async (id, updates) => {
    const res = await fetch(`${API_URL}/api/v1/agents/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update agent');
    await get().fetchAgents();
  },

  deleteAgent: async (id) => {
    const res = await fetch(`${API_URL}/api/v1/agents/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error('Failed to delete agent');
    await get().fetchAgents();
  },

  selectAgent: (agent) => set({ selectedAgent: agent }),
}));
