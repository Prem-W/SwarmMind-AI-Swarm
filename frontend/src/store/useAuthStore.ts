import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        const res = await fetch(`${API_URL}/api/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });

        if (!res.ok) throw new Error('Invalid credentials');

        const data = await res.json();
        set({ token: data.access_token, isAuthenticated: true });

        // Fetch user profile
        const userRes = await fetch(`${API_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        const userData = await userRes.json();
        set({ user: userData });
      },

      register: async (email: string, password: string, full_name: string) => {
        const res = await fetch(`${API_URL}/api/v1/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, full_name }),
        });

        if (!res.ok) throw new Error('Registration failed');
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      setToken: (token: string) => {
        set({ token, isAuthenticated: true });
      },
    }),
    {
      name: 'swarmmind-auth',
      partialize: (state) => ({ token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
