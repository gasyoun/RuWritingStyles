import React, { useState, useEffect } from 'react'

const MOCK_RUNS = [
  { id: 'etymology-check-1', source: 'pseudo-etymology.md', date: '2026-05-07' },
  { id: 'scholarly-review-2', source: 'article-zaliznyak.md', date: '2026-05-07' },
  { id: 'archival-migration-3', source: 'notes-19th-century.md', date: '2026-05-06' }
];

const MOCK_AGENTS = [
  { id: 'coordinator', name: 'Council Coordinator', status: 'Deliberating...' },
  { id: 'critic', name: 'The Rigorous Critic', status: 'Reviewing matches' },
  { id: 'mentor', name: 'The Scholarly Mentor', status: 'Verifying tone' }
];

const MOCK_ORIGINAL = `
Этимология слова "собака" в русском языке часто вызывает споры. 
Некоторые считают, что оно заимствовано из иранских языков, 
другие указывают на тюркские корни. 
В любительской лингвистике популярна версия о связи со словом "собь".
`;

const MOCK_REVISED = `
Этимология лексемы «собака» в русском языке остается предметом академической дискуссии. 
Традиционная гипотеза возводит данную форму к иранским источникам (ср. авест. spaka), 
в то время как тюркская версия признается менее обоснованной. 
Версии любительской лингвистике, постулирующие связь с праславянским *sobь, 
лишены системных филологических оснований.
`;

function App() {
  const [activeRun, setActiveRun] = useState(MOCK_RUNS[0]);
  const [systemStatus, setSystemStatus] = useState({ ready: false, provider: 'google' });

  useEffect(() => {
    fetch('http://localhost:8000/status?provider=google')
      .then(res => res.json())
      .then(data => {
        const google = data.find(p => p.provider === 'google');
        if (google) setSystemStatus(google);
      })
      .catch(err => console.error('API Offline', err));
  }, []);

  return (
    <div className="studio-container">
      <aside className="sidebar">
        <div className="sidebar-header">RuWritingStyles</div>
        <ul className="run-list">
          {MOCK_RUNS.map(run => (
            <li 
              key={run.id} 
              className={`run-item ${activeRun.id === run.id ? 'active' : ''}`}
              onClick={() => setActiveRun(run)}
            >
              <div>{run.id}</div>
              <div style={{fontSize: '0.75rem', opacity: 0.7}}>{run.source}</div>
            </li>
          ))}
        </ul>
        <div style={{marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.8rem'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem'}}>
            <div style={{width: 8, height: 8, borderRadius: '50%', background: systemStatus.ready ? '#3fb950' : '#f85149'}}></div>
            <span>Google Gemini: {systemStatus.ready ? 'READY' : 'OFFLINE'}</span>
          </div>
          {!systemStatus.ready && (
            <p style={{color: '#8b949e', fontSize: '0.7rem', lineHeight: 1.4}}>
              Key missing. Please set <b>GOOGLE_API_KEY</b> in your <b>.env</b> file and restart the Studio.
            </p>
          )}
        </div>
      </aside>

      <main className="workbench">
        <header className="workbench-header">
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <div style={{fontWeight: 600}}>Workbench: {activeRun.id}</div>
            {systemStatus.ready ? (
              <span style={{fontSize: '0.7rem', background: 'rgba(63, 185, 80, 0.15)', color: '#3fb950', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(63, 185, 80, 0.4)'}}>High Assurance Mode</span>
            ) : (
              <span style={{fontSize: '0.7rem', background: 'rgba(248, 81, 73, 0.15)', color: '#f85149', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(248, 81, 73, 0.4)'}}>Key Required</span>
            )}
          </div>
          <div style={{display: 'flex', gap: '1rem'}}>
            <button className="glass" style={{padding: '0.5rem 1rem', borderRadius: '6px', color: 'white', cursor: 'pointer'}}>Run Audit</button>
            <button style={{padding: '0.5rem 1rem', borderRadius: '6px', background: '#58a6ff', border: 'none', color: 'white', fontWeight: 600, cursor: 'pointer'}}>Apply Revision</button>
          </div>
        </header>

        <section className="council-chamber">
          {MOCK_AGENTS.map(agent => (
            <div key={agent.id} className="agent-card">
              <div className="agent-name">{agent.name}</div>
              <div className="agent-status">{agent.status}</div>
              <div style={{marginTop: 'auto', fontSize: '0.7rem', color: '#8b949e'}}>Weight: 1.0</div>
            </div>
          ))}
        </section>

        <section className="editor-grid">
          <div className="editor-pane">
            <div className="pane-label">Original Document</div>
            <div className="pane-content">{MOCK_ORIGINAL}</div>
          </div>
          <div className="editor-pane">
            <div className="pane-label">Council Revision</div>
            <div className="pane-content">{MOCK_REVISED}</div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
