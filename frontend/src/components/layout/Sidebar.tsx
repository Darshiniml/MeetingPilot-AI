import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  PlayCircle,
  History,
  MessageSquare,
  Users,
  CalendarRange,
  Settings,
  Menu,
  ChevronLeft,
  LogOut,
  Cpu,
  GitBranch,
  CheckSquare,
  Database,
  Network
} from 'lucide-react';

interface SidebarProps {
  activeView: string;
  onSelectView: (view: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeView, onSelectView }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { logout, user } = useAuth();

  const sections = [
    {
      title: "Core",
      items: [
        { id: 'Dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
        { id: 'Live Meeting', label: 'Live Meeting', icon: <PlayCircle size={16} /> },
        { id: 'Meeting History', label: 'Meeting History', icon: <History size={16} /> },
        { id: 'Meeting Chat', label: 'AI Assistant', icon: <MessageSquare size={16} /> },
        { id: 'Scheduler', label: 'Scheduler', icon: <CalendarRange size={16} /> },
        { id: 'Contacts', label: 'Contacts', icon: <Users size={16} /> }
      ]
    },
    {
      title: "Platform OS",
      items: [
        { id: 'Agent Control Center', label: 'Mission Control', icon: <Cpu size={16} /> },
        { id: 'Agents', label: 'Agent Center', icon: <Cpu size={16} /> },
        { id: 'Workflows', label: 'Workflow Center', icon: <GitBranch size={16} /> },
        { id: 'Approvals', label: 'Approvals', icon: <CheckSquare size={16} /> }
      ]
    },
    {
      title: "Enterprise Connectors",
      items: [
        { id: 'MCP', label: 'MCP Registry', icon: <Database size={16} /> },
        { id: 'A2A', label: 'A2A Router', icon: <Network size={16} /> },
        { id: 'Settings', label: 'Settings', icon: <Settings size={16} /> }
      ]
    }
  ];

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 76 : 256 }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      className="h-screen bg-zinc-950 border-r border-zinc-900 flex flex-col justify-between select-none shrink-0"
    >
      {/* Top Header */}
      <div>
        <div className={`h-16 flex items-center px-4 border-b border-zinc-900/50 ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2.5"
            >
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20 text-sm">
                MP
              </div>
              <span className="font-display font-bold text-sm tracking-wide text-slate-100 uppercase">
                MeetingPilot
              </span>
            </motion.div>
          )}

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="w-8 h-8 rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-slate-100 flex items-center justify-center transition-colors cursor-pointer"
          >
            {isCollapsed ? <Menu size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Menu Navigation */}
        <nav className="p-3 space-y-4 mt-2 overflow-y-auto max-h-[calc(100vh-140px)]">
          {sections.map((section) => (
            <div key={section.title} className="space-y-1">
              {!isCollapsed && (
                <span className="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-1">
                  {section.title}
                </span>
              )}
              {section.items.map((item) => {
                const isActive = activeView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectView(item.id)}
                    className={`relative w-full rounded-lg px-3 py-2 flex items-center gap-3 transition-all text-xs font-semibold cursor-pointer ${
                      isActive
                        ? 'text-white bg-indigo-600/10 border border-indigo-500/25 shadow-lg shadow-indigo-500/5'
                        : 'text-zinc-400 hover:bg-zinc-900 hover:text-slate-100 border border-transparent'
                    }`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="sidebarActiveBackground"
                        className="absolute inset-0 bg-indigo-600/5 rounded-lg -z-10"
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      />
                    )}
                    <span className={isActive ? 'text-indigo-400' : 'text-zinc-500'}>{item.icon}</span>
                    {!isCollapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="truncate"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer Profile & Logout */}
      <div className="p-3 border-t border-zinc-900/50">
        {!isCollapsed ? (
          <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-900/40 border border-zinc-900">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-xs font-bold text-white uppercase">
                {user?.name?.slice(0, 2) || 'US'}
              </div>
              <div className="flex flex-col text-left overflow-hidden">
                <span className="text-xs font-bold text-slate-200 truncate">{user?.name || 'User'}</span>
                <span className="text-[10px] text-zinc-500 truncate">{user?.email || 'user@example.com'}</span>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-zinc-500 hover:text-red-400 p-1 rounded transition-colors cursor-pointer"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <button
            onClick={logout}
            className="w-full flex items-center justify-center py-3 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        )}
      </div>
    </motion.aside>
  );
};

export default Sidebar;
