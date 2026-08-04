import React from 'react';
import { motion } from 'framer-motion';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, hoverEffect = true, className = '', ...props }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      whileHover={hoverEffect ? { y: -2, borderColor: "rgba(99, 102, 241, 0.35)" } : undefined}
      className={`bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-xl transition-all duration-200 ${className}`}
      {...(props as any)}
    >
      {children}
    </motion.div>
  );
};
