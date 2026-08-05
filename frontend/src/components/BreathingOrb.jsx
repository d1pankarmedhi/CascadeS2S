import React from 'react';
import { motion } from 'framer-motion';

export function BreathingOrb({ status, energy }) {
  // Minimalist light theme colors
  const colors = {
    disconnected: '#e5e7eb', // gray-200
    idle: '#111827', // gray-900 (black)
    listening: '#2563eb', // blue-600
    thinking: '#8b5cf6', // purple-500
    speaking: '#10b981', // green-500
  };

  const currentColor = colors[status] || colors.disconnected;
  
  // Calculate dynamic scales based on energy and status
  const baseScale = status === 'disconnected' ? 0.9 : 1;
  const energyScale = (energy || 0) * 0.05; 
  
  // Speed of the fluid animation based on state
  const duration = status === 'listening' ? 1.5 :
                   status === 'speaking' ? 1.2 :
                   status === 'thinking' ? 2 : 
                   4;

  return (
    <div style={{ position: 'relative', width: 200, height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      
      {/* Outer blurred fluid aura */}
      <motion.div
        animate={{
          scale: status === 'listening' ? 1.3 + energyScale : 1.1,
          opacity: status === 'disconnected' ? 0 : [0.05, 0.1, 0.05],
          borderRadius: [
            "40% 60% 70% 30% / 40% 50% 60% 50%",
            "60% 40% 30% 70% / 60% 30% 70% 40%",
            "40% 60% 70% 30% / 40% 50% 60% 50%"
          ]
        }}
        transition={{
          scale: { type: 'spring', stiffness: 100, damping: 10 },
          opacity: { duration: duration * 1.5, repeat: Infinity, ease: 'easeInOut' },
          borderRadius: { duration: duration * 1.5, repeat: Infinity, ease: 'easeInOut' }
        }}
        style={{
          position: 'absolute',
          inset: -20,
          background: currentColor,
          filter: 'blur(15px)',
        }}
      />
      
      {/* Main Fluid Orb */}
      <motion.div
        animate={{
          scale: baseScale + (status === 'listening' ? energyScale * 0.3 : 0),
          borderRadius: [
            "60% 40% 30% 70% / 60% 30% 70% 40%",
            "30% 70% 70% 30% / 30% 30% 70% 70%",
            "50% 50% 20% 80% / 25% 80% 20% 75%",
            "60% 40% 30% 70% / 60% 30% 70% 40%"
          ],
          rotate: status === 'thinking' ? 360 : 0
        }}
        transition={{
          scale: { type: 'spring', stiffness: 300, damping: 20 },
          borderRadius: { duration, repeat: Infinity, ease: 'easeInOut' },
          rotate: { duration: 4, repeat: Infinity, ease: 'linear' }
        }}
        style={{
          position: 'relative',
          width: 100,
          height: 100,
          background: currentColor,
          boxShadow: status === 'disconnected' ? 'none' : 'inset -10px -10px 20px rgba(0,0,0,0.1), 0 10px 20px -5px ' + currentColor + '60',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          zIndex: 10,
        }}
      >
        {/* Specular highlight for a liquid/glassy surface feel */}
        <div style={{
          position: 'absolute',
          top: '15%',
          left: '15%',
          width: '30%',
          height: '30%',
          background: 'radial-gradient(circle, rgba(255,255,255,0.4) 0%, transparent 60%)',
          borderRadius: '50%',
          filter: 'blur(2px)',
        }} />
      </motion.div>
    </div>
  );
}
