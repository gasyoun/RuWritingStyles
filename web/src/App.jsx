import { useCallback, useEffect, useState } from 'react'

function App() {
  const [runs, setRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [systemStatuses, setSystemStatuses] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('google');
  const [isNewRunModalOpen, setIsNewRunModalOpen] = useState(false);
  const [newRunPath, setNewRunPath] = useState('C:\\Users\\user\\Documents\\GitHub\\RuWritingStyles\\article.md');

  // 1. Fetch Runs List
  const fetchRuns = useCallback(() => {
    fetch('http://localhost:8000/runs')
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        if (data.length > 0) {
          setActiveRunId(current => current || data[0]);
        }
      });
  }, []);

  useEffect(() => {
    fetchRuns();
    fetch('http://localhost:8000/status')
      .then(res => res.json())
      .then(data => setSystemStatuses(data));
  }, [fetchRuns]);

  // 2. Fetch Active Run Data
  useEffect(() => {
    if (activeRunId) {
      fetch(`http://localhost:8000/runs/${activeRunId}`)
        .then(res => res.json())
        .then(data => setRunData(data));
    }
  }, [activeRunId]);

  const handleStartRun = () => {
    if (!newRunPath) return;
    fetch('http://localhost:8000/runs/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_path: newRunPath,
        provider: selectedProvider,
        execute: true
      })
    }).then(() => {
      setIsNewRunModalOpen(false);
      fetchRuns();
    });
  };

  const currentStatus = systemStatuses.find(p => p.provider === selectedProvider) || { ready: false };

  return (
    <div className="studio-container">
      <aside className="sidebar">
        <div className="sidebar-header">RuWritingStyles</div>
        
        <div style={{marginBottom: '1rem'}}>
          <button 
            onClick={() => setIsNewRunModalOpen(true)}
            style={{width: '100%', padding: '0.75rem', background: '#3fb950', border: 'none', color: 'white', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', marginBottom: '1rem'}}
          >
            + New Philological Audit
          </button>

          <label style={{fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase', marginBottom: '0.5rem', display: 'block'}}>Active Provider</label>
          <select 
            value={selectedProvider} 
            onChange={(e) => setSelectedProvider(e.target.value)}
            style={{width: '100%', padding: '0.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '4px'}}
          >
            <option value="google">Google Gemini</option>
            <option value="openrouter">OpenRouter (Free)</option>
            <option value="anthropic">Anthropic Claude</option>
          </select>
        </div>

        <ul className="run-list">
          {runs.map(runId => (
            <li 
              key={runId} 
              className={`run-item ${activeRunId === runId ? 'active' : ''}`}
              onClick={() => setActiveRunId(runId)}
            >
              <div>{runId}</div>
            </li>
          ))}
        </ul>
        
        <div style={{marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.8rem'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem'}}>
            <div style={{width: 8, height: 8, borderRadius: '50%', background: currentStatus.ready ? '#3fb950' : '#f85149'}}></div>
            <span>{selectedProvider.toUpperCase()}: {currentStatus.ready ? 'READY' : 'OFFLINE'}</span>
          </div>
        </div>
      </aside>

      <main className="workbench">
        <header className="workbench-header">
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <div style={{fontWeight: 600}}>Workbench: {activeRunId || 'No Run Selected'}</div>
            {currentStatus.ready && <span style={{fontSize: '0.7rem', background: 'rgba(63, 185, 80, 0.15)', color: '#3fb950', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(63, 185, 80, 0.4)'}}>High Assurance Mode</span>}
          </div>
          <div style={{display: 'flex', gap: '1rem'}}>
             <button style={{padding: '0.5rem 1rem', borderRadius: '6px', background: '#58a6ff', border: 'none', color: 'white', fontWeight: 600, cursor: 'pointer'}}>Finalize & Export</button>
          </div>
        </header>

        {runData ? (
          <>
            <section className="council-chamber">
              <div className="agent-card">
                <div className="agent-name">Council Coordinator</div>
                <div className="agent-status" style={{color: '#58a6ff'}}>Deliberation Completed</div>
                <div style={{marginTop: 'auto', fontSize: '0.7rem', color: '#8b949e'}}>Matches Found: {runData.revision?.applied_changes?.length || 0}</div>
              </div>
              <div className="agent-card">
                <div className="agent-name">Scholarly Sentiment</div>
                <div className="agent-status">Distance: {runData.sentiment?.deltas?.distance || 0}</div>
                <div style={{marginTop: 'auto', fontSize: '0.7rem', color: '#8b949e'}}>Tone shift verified</div>
              </div>
            </section>

            <section className="editor-grid">
              <div className="editor-pane">
                <div className="pane-label">Original Manuscript</div>
                <div className="pane-content">{runData.original_text || 'Loading text...'}</div>
              </div>
              <div className="editor-pane">
                <div className="pane-label">Philological Revision</div>
                <div className="pane-content" style={{color: '#c9d1d9'}}>{runData.revised_text || 'No revision data found.'}</div>
              </div>
            </section>
          </>
        ) : (
          <div style={{display: 'flex', alignItems: 'center', justifySelf: 'center', height: '100%', color: '#8b949e'}}>
            Select a run from the sidebar to view details
          </div>
        )}
      </main>

      {isNewRunModalOpen && (
        <div style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000}}>
          <div style={{background: 'var(--bg-secondary)', padding: '2rem', borderRadius: '12px', width: '400px', border: '1px solid var(--border-color)'}}>
            <h3>New Philological Audit</h3>
            <p style={{fontSize: '0.8rem', color: '#8b949e', margin: '1rem 0'}}>Enter the path to your article (.md or .txt):</p>
            <input 
              type="text" 
              placeholder="C:/path/to/my-article.md"
              value={newRunPath}
              onChange={(e) => setNewRunPath(e.target.value)}
              style={{width: '100%', padding: '0.75rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '6px', marginBottom: '1.5rem'}}
            />
            <div style={{display: 'flex', gap: '1rem', justifyContent: 'flex-end'}}>
              <button onClick={() => setIsNewRunModalOpen(false)} style={{background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer'}}>Cancel</button>
              <button onClick={handleStartRun} style={{padding: '0.5rem 1.5rem', background: '#58a6ff', border: 'none', color: 'white', borderRadius: '6px', fontWeight: 600, cursor: 'pointer'}}>Start Audit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
