import { create } from 'zustand';

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  status: string;
  team_id: string;
  version: number;
  is_active: boolean;
  created_at: string;
}

export interface Execution {
  id: string;
  workflow_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  triggered_by: string;
}

interface WorkflowState {
  workflows: Workflow[];
  executions: Execution[];
  selectedWorkflow: Workflow | null;
  isLoading: boolean;
  error: string | null;
  fetchWorkflows: (teamId?: string) => Promise<void>;
  createWorkflow: (workflow: Partial<Workflow>) => Promise<void>;
  executeWorkflow: (id: string, data?: Record<string, unknown>) => Promise<void>;
  fetchExecutions: (workflowId: string) => Promise<void>;
  selectWorkflow: (workflow: Workflow | null) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getToken = () => {
  const state = JSON.parse(localStorage.getItem('swarmmind-auth') || '{}');
  return state.state?.token;
};

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflows: [],
  executions: [],
  selectedWorkflow: null,
  isLoading: false,
  error: null,

  fetchWorkflows: async (teamId) => {
    set({ isLoading: true, error: null });
    try {
      const params = teamId ? `?team_id=${teamId}` : '';
      const res = await fetch(`${API_URL}/api/v1/workflows${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      set({ workflows: data, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
    }
  },

  createWorkflow: async (workflow) => {
    const res = await fetch(`${API_URL}/api/v1/workflows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(workflow),
    });
    if (!res.ok) throw new Error('Failed to create workflow');
    await get().fetchWorkflows();
  },

  executeWorkflow: async (id, data) => {
    const res = await fetch(`${API_URL}/api/v1/workflows/${id}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(data || {}),
    });
    if (!res.ok) throw new Error('Failed to execute workflow');
    await get().fetchExecutions(id);
  },

  fetchExecutions: async (workflowId) => {
    const res = await fetch(`${API_URL}/api/v1/workflows/${workflowId}/executions`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const data = await res.json();
    set({ executions: data });
  },

  selectWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
}));
