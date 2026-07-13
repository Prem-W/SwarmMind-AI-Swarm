import { Menu, Bell, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/useAuthStore';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore();

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden text-slate-400 hover:text-white"
          onClick={onMenuClick}
        >
          <Menu className="w-5 h-5" />
        </Button>
        <div className="hidden sm:block">
          <h1 className="text-sm font-medium text-slate-300">SwarmMind Platform</h1>
          <p className="text-xs text-slate-500">Multi-Agent AI Orchestration</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full" />
        </Button>

        <div className="flex items-center gap-2 pl-3 border-l border-slate-700">
          <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-slate-400" />
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-medium text-slate-300">{user?.full_name || 'Guest'}</p>
            <p className="text-xs text-slate-500">{user?.role || 'Viewer'}</p>
          </div>
        </div>

        {user && (
          <Button
            variant="ghost"
            size="sm"
            className="text-slate-400 hover:text-white text-xs"
            onClick={logout}
          >
            Logout
          </Button>
        )}
      </div>
    </header>
  );
}
