import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { CalendarCheck, CalendarX, Bell, Search, Command } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  title?: string;
  onOpenSearch?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ title = "Dashboard", onOpenSearch }) => {
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const { user } = useAuth();

  useEffect(() => {
    const fetchGoogleStatus = async () => {
      try {
        const response = await api.get('/integrations/google/status');
        setGoogleConnected(response.data.is_connected);
        setGoogleEmail(response.data.google_email || '');
      } catch (err) {
        console.error("Failed to load Google status in header:", err);
      }
    };
    fetchGoogleStatus();
    // Poll every 30s
    const interval = setInterval(fetchGoogleStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-zinc-900 bg-zinc-950/40 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-40 select-none">
      {/* Title / Path */}
      <div className="flex items-center gap-3">
        <span className="text-zinc-600 text-xs font-semibold uppercase tracking-wider">Workspace</span>
        <span className="text-zinc-400 text-xs font-bold">/</span>
        <h2 className="font-display text-slate-100 text-sm font-bold tracking-wide uppercase">
          {title}
        </h2>
      </div>

      {/* Center connection status & search bar button */}
      <div className="flex items-center gap-4">
        {/* Search bar button */}
        <button
          onClick={onOpenSearch}
          className="flex items-center gap-5 px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 text-xs transition-colors duration-150 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Search size={14} />
            <span>Search commands...</span>
          </div>
          <div className="flex items-center gap-1 font-bold text-[10px] text-zinc-600">
            <Command size={10} />
            <span>K</span>
          </div>
        </button>

        {/* Google Status Badge */}
        {googleConnected ? (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold cursor-help" title={`Synced: ${googleEmail}`}>
            <CalendarCheck size={14} className="animate-pulse" />
            <span className="hidden md:inline">Google Synced</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-500 text-xs font-bold">
            <CalendarX size={14} />
            <span className="hidden md:inline">Google Disconnected</span>
          </div>
        )}
      </div>

      {/* User profile info & notifications */}
      <div className="flex items-center gap-4">
        {/* Notifications mock icon */}
        <button className="relative w-8 h-8 rounded-lg border border-zinc-900 bg-zinc-950 text-zinc-400 hover:text-slate-100 flex items-center justify-center transition-colors cursor-pointer">
          <Bell size={16} />
          <span className="absolute top-1 right-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500" />
        </button>

        {/* User Card */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-xs font-bold text-white uppercase shadow-md shadow-indigo-500/10">
            {user?.name?.slice(0, 2) || 'US'}
          </div>
          <span className="text-xs font-bold text-slate-300 hidden sm:inline">{user?.name || 'User'}</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
