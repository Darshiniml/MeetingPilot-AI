import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToastStore } from '../../store/useToastStore';
import { CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';

export const Toaster: React.FC = () => {
  const { toasts, removeToast } = useToastStore();

  const icons = {
    success: <CheckCircle2 size={18} className="text-emerald-400" />,
    error: <AlertCircle size={18} className="text-red-400" />,
    info: <Info size={18} className="text-sky-400" />,
    warning: <AlertTriangle size={18} className="text-amber-400" />
  };

  const borders = {
    success: "border-emerald-500/20",
    error: "border-red-500/20",
    info: "border-sky-500/20",
    warning: "border-amber-500/20"
  };

  return (
    <div className="fixed top-4 right-4 z-55 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, y: -10 }}
            className={`pointer-events-auto flex items-start gap-3 p-4 bg-zinc-900 border ${borders[toast.type]} rounded-xl shadow-2xl overflow-hidden`}
          >
            <div className="mt-0.5 shrink-0">{icons[toast.type]}</div>
            <div className="flex-1 text-left">
              <h4 className="text-sm font-bold text-slate-100">{toast.title}</h4>
              <p className="text-xs text-zinc-400 mt-1">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-zinc-500 hover:text-slate-100 cursor-pointer text-xs self-start"
            >
              ✕
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
