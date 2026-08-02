import React from 'react';

export function BreathingOrb({ status, energy }) {
  const statusClass = `orb--${status}`;
  
  // Exaggerate energy for visual effect when listening/speaking
  let scale = 1;
  if (status === 'listening') {
    scale = 1 + (energy * 15);
  } else if (status === 'speaking') {
    scale = 1.1 + (Math.random() * 0.1); // Fake speaking animation if energy isn't mapped
  }

  return (
    <div className="orb-container">
      <div 
        className={`orb ${statusClass}`} 
        style={{ transform: `scale(${scale})` }}
      >
        <div className="orb-core"></div>
      </div>
    </div>
  );
}
