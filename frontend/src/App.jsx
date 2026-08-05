import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Power, MessageSquare } from 'lucide-react';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { BreathingOrb } from './components/BreathingOrb';
import { ChatTranscript } from './components/ChatTranscript';
import './index.css';

function App() {
  const { status, micEnergy, transcript, connect, disconnect } = useVoiceAgent();
  const [showChat, setShowChat] = useState(false);

  return (
    <div className="app-layout">
      
      {/* Top Navigation */}
      <header style={{ 
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 50,
        padding: '2rem 3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--text-main)' }} />
          <h1 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, letterSpacing: '-0.01em' }}>Cascade</h1>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#f3f4f6', padding: '0.4rem 0.8rem', borderRadius: '999px' }}>
          <span className={`status-dot ${status}`}></span>
          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
            {status}
          </span>
        </div>
      </header>
      
      {/* Main Interface */}
      <main style={{ flex: 1, display: 'flex', zIndex: 10, width: '100%', height: '100%' }}>
        
        {/* Left Side: Orb & Controls */}
        <motion.div 
          layout
          style={{ 
            flex: showChat ? 0.6 : 1, 
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            position: 'relative',
            background: 'var(--bg-main)',
          }}
          transition={{ type: 'spring', damping: 30, stiffness: 200 }}
        >
          <motion.div 
            layout
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            style={{ marginBottom: '3rem' }}
          >
            <BreathingOrb status={status} energy={micEnergy} />
          </motion.div>
          
          <motion.div layout style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', zIndex: 20 }}>
            <motion.div 
              layout
              style={{ display: 'flex', gap: '0.75rem' }}
            >
              {status === 'disconnected' ? (
                <button className="btn-minimal" onClick={connect}>
                  Connect
                </button>
              ) : (
                <button className="btn-minimal btn-danger" onClick={disconnect}>
                  Disconnect
                </button>
              )}
              
              <button className={`btn-minimal ${showChat ? 'active' : ''}`} onClick={() => setShowChat(!showChat)}>
                <MessageSquare size={16} />
              </button>
            </motion.div>
            
            {/* Energy Bar */}
            <AnimatePresence>
              {status !== 'disconnected' && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 4 }}
                  exit={{ opacity: 0, height: 0 }}
                  style={{ width: '120px', background: 'var(--border-color)', borderRadius: '999px', overflow: 'hidden' }}
                >
                  <motion.div 
                    animate={{ width: `${Math.min(100, micEnergy * 5000)}%` }}
                    transition={{ type: 'tween', duration: 0.1, ease: 'linear' }}
                    style={{ height: '100%', background: 'var(--text-main)', borderRadius: '999px' }}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
        
        {/* Right Side: Chat Panel */}
        <AnimatePresence>
          {showChat && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: '400px', opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 250 }}
              style={{ 
                borderLeft: '1px solid var(--border-color)',
                background: 'var(--bg-surface)',
                zIndex: 20,
                overflow: 'hidden'
              }}
            >
              <div style={{ width: '400px', height: '100%' }}>
                <ChatTranscript transcript={transcript} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
      </main>
      
    </div>
  );
}

export default App;
