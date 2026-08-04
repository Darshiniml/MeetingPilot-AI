import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, LayoutDashboard, Play, CalendarDays, History, Users, Settings, RefreshCw } from 'lucide-react';

interface CommandItem {
  id: string;
  label: string;
  category: string;
  icon: React.ReactNode;
  action: () => void;
}

interface CommandPaletteProps {
  onSelectView: (view: string) => void;
  onTriggerSync?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ onSelectView, onTriggerSync }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items: CommandItem[] = [
    {
      id: 'dashboard',
      label: 'Go to Dashboard',
      category: 'Navigation',
      icon: <LayoutDashboard size={16} />,
      action: () => onSelectView('Dashboard')
    },
    {
      id: 'live_meeting',
      label: 'Start Live Meeting',
      category: 'Navigation',
      icon: <Play size={16} className="text-emerald-400" />,
      action: () => onSelectView('Live Meeting')
    },
    {
      id: 'history',
      label: 'View Meeting History',
      category: 'Navigation',
      icon: <History size={16} />,
      action: () => onSelectView('Meeting History')
    },
    {
      id: 'chat',
      label: 'Open AI Chat Assistant',
      category: 'Navigation',
      icon: <CalendarDays size={16} />,
      action: () => onSelectView('Meeting Chat')
    },
    {
      id: 'contacts',
      label: 'View Contacts',
      category: 'Navigation',
      icon: <Users size={16} />,
      action: () => onSelectView('Contacts')
    },
    {
      id: 'scheduler',
      label: 'Open AI Meeting Scheduler',
      category: 'Navigation',
      icon: <CalendarDays size={16} />,
      action: () => onSelectView('Scheduler')
    },
    {
      id: 'settings',
      label: 'Open Settings',
      category: 'Navigation',
      icon: <Settings size={16} />,
      action: () => onSelectView('Settings')
    },
    {
      id: 'sync',
      label: 'Sync Google Contacts',
      category: 'Actions',
      icon: <RefreshCw size={16} className="text-indigo-400" />,
      action: () => onTriggerSync?.()
    }
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (isOpen) {
        if (e.key === 'Escape') {
          setIsOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
      setQuery('');
    }
  }, [isOpen]);

  const filteredItems = items.filter(item =>
    item.label.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
        setIsOpen(false);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -10 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-xl bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden z-10"
          >
            <div className="relative border-b border-zinc-800 p-4 flex items-center gap-3">
              <Search className="text-zinc-500 shrink-0" size={18} />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or search..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-transparent text-sm text-slate-100 placeholder-zinc-500 focus:outline-none"
              />
              <span className="text-[10px] bg-zinc-800 text-zinc-400 font-bold px-1.5 py-0.5 rounded border border-zinc-700">ESC</span>
            </div>

            <div className="max-h-[300px] overflow-y-auto p-2">
              {filteredItems.length === 0 ? (
                <div className="text-center text-zinc-500 text-xs py-8">No results found</div>
              ) : (
                filteredItems.map((item, index) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      item.action();
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm text-left transition-colors cursor-pointer ${
                      index === selectedIndex ? 'bg-indigo-600 text-white' : 'text-zinc-400 hover:bg-zinc-800 hover:text-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={index === selectedIndex ? 'text-white' : 'text-zinc-500'}>{item.icon}</span>
                      <span>{item.label}</span>
                    </div>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider ${index === selectedIndex ? 'text-indigo-200' : 'text-zinc-500'}`}>
                      {item.category}
                    </span>
                  </button>
                ))
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
