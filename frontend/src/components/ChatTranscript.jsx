import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export function ChatTranscript({ transcript }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#ffffff' }}>
      <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ fontSize: '0.875rem', fontWeight: 500, margin: 0, color: 'var(--text-main)' }}>Transcript</h2>
      </div>
      
      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '2rem 1.5rem', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '1.5rem',
          scrollBehavior: 'smooth'
        }}
      >
        <AnimatePresence>
          {transcript.length === 0 && (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }}
              style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '4rem', fontSize: '0.875rem' }}
            >
              Listening...
            </motion.div>
          )}
          
          {transcript.map((msg, i) => {
            const isAgent = msg.role === 'agent';
            return (
              <motion.div 
                key={i} 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: isAgent ? 'flex-start' : 'flex-end',
                  maxWidth: '100%' 
                }}
              >
                <div style={{ 
                  padding: '0.875rem 1.25rem', 
                  borderRadius: '12px',
                  background: isAgent ? '#f3f4f6' : '#111827',
                  color: isAgent ? '#111827' : '#ffffff',
                  lineHeight: 1.5,
                  fontSize: '0.9rem',
                  maxWidth: '85%',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                }}>
                  {msg.text}
                  {isAgent && !msg.is_final && (
                    <motion.span 
                      animate={{ opacity: [0.2, 1, 0.2] }} 
                      transition={{ duration: 1.5, repeat: Infinity }}
                      style={{ display: 'inline-block', marginLeft: '8px' }}
                    >
                      ●
                    </motion.span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={endRef} />
      </div>
    </div>
  );
}
