import React from 'react';
import { motion } from 'framer-motion';

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({ children, hoverEffect = false, className = '', ...props }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.99 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={hoverEffect ? { borderColor: "rgba(139, 92, 246, 0.35)" } : undefined}
      className={`bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-5 shadow-2xl ${className}`}
      {...(props as any)}
    >
      {children}
    </motion.div>
  );
};
