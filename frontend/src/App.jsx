import { useState } from 'react';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { BreathingOrb } from './components/BreathingOrb';
import { ChatTranscript } from './components/ChatTranscript';
import './index.css';

function App() {
  const { status, micEnergy, transcript, connect, disconnect } = useVoiceAgent();
  const [showChat, setShowChat] = useState(false);

  return (
    <div className="app-container">
      <header className="header">
        <h1>Cascade Voice</h1>
        <div className={`status-indicator status-${status}`}>
          {status.toUpperCase()}
        </div>
      </header>
      
      <main className="main-content">
        <div className={`orb-section ${showChat ? 'shrink' : ''}`}>
          <BreathingOrb status={status} energy={micEnergy} />
          
          <div className="controls">
            {status === 'disconnected' ? (
              <button className="btn btn-primary" onClick={connect}>Start Conversation</button>
            ) : (
              <button className="btn btn-danger" onClick={disconnect}>End Conversation</button>
            )}
            
            <button className="btn btn-secondary" onClick={() => setShowChat(!showChat)}>
              {showChat ? 'Hide Transcript' : 'Show Transcript'}
            </button>
          </div>
        </div>

        {showChat && (
          <div className="chat-section">
            <ChatTranscript transcript={transcript} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
