import React, { useEffect, useRef } from 'react';

export function ChatTranscript({ transcript }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  return (
    <div className="chat-container">
      {transcript.map((msg, i) => (
        <div key={i} className={`chat-message chat-message--${msg.role}`}>
          <div className="chat-bubble">
            {msg.text}
            {msg.role === 'agent' && !msg.is_final && <span className="typing-indicator">...</span>}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
