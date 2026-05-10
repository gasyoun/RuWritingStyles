import { useCallback, useEffect, useState, useRef } from 'react';
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell, LineChart, Line
} from 'recharts';
import { 
  Search, BookOpen, Activity, Layers, MessageSquare,
  Settings, Download, Plus, Info, Zap
} from 'lucide-react';

function App() {
  const [runs, setRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [selectedRunIds, setSelectedRunIds] = useState([]);
  const [concordance, setConcordance] = useState({});
  const [systemStatuses, setSystemStatuses] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('google');
  const [isNewRunModalOpen, setIsNewRunModalOpen] = useState(false);
  const [newRunPath, setNewRunPath] = useState('C:\\Users\\user\\Documents\\GitHub\\RuWritingStyles\\article.md');
  const [viewMode, setViewMode] = useState('audit'); // 'audit', 'profile', 'syntax', 'compare'
  const [comparisonData, setComparisonData] = useState([]);
  const [resolutions, setResolutions] = useState({});
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const [trace, setTrace] = useState([]);
  const [injectionText, setInjectionText] = useState('');

  const wsRef = useRef(null);

  // WebSocket Live Updates
  useEffect(() => {
    if (!activeRunId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/${activeRunId}`);
    wsRef.current = ws;
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setTrace(prev => [
        { ...msg, timestamp: new Date().toLocaleTimeString() },
        ...prev.slice(0, 19) // Keep last 20 events
      ]);

      // Auto-refresh data if step completed
      if (msg.type === 'step_update' && msg.status === 'completed') {
        fetch(`http://localhost:8000/runs/${activeRunId}`)
          .then(res => res.json())
          .then(data => setRunData(data));
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      setTrace([]);
    };
  }, [activeRunId]);

  const sendInjection = (content) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'human_injection',
        content: content
      }));
    }
  };

  const handleInjectionSubmit = (e) => {
    if (e.key === 'Enter' && injectionText.trim()) {
      sendInjection(injectionText.trim());
      setInjectionText('');
    }
  };

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
    if (activeRunId && viewMode !== 'compare') {
      fetch(`http://localhost:8000/runs/${activeRunId}`)
        .then(res => res.json())
        .then(data => {
          setRunData(data);
          fetch(`http://localhost:8000/runs/${activeRunId}/concordance`)
            .then(res => res.json())
            .then(concData => setConcordance(concData));
        });
    }
  }, [activeRunId, viewMode]);

  // 3. Fetch Comparison Data
  useEffect(() => {
    if (viewMode === 'compare' && selectedRunIds.length > 1) {
      fetch(`http://localhost:8000/api/compare?run_ids=${selectedRunIds.join(',')}`)
        .then(res => res.json())
        .then(data => setComparisonData(data));
    }
  }, [viewMode, selectedRunIds]);

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

  const handleApplyResolutions = () => {
    if (!activeRunId) return;
    const overrides = Object.values(resolutions);
    if (overrides.length === 0) return;
    
    fetch(`http://localhost:8000/runs/${activeRunId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overrides })
    }).then(res => res.json()).then(data => {
      alert(data.status);
      setResolutions({});
      // Ideally poll for status, but for now just clear
    }).catch(err => alert("Error applying resolutions: " + err));
  };

  const handleFinalize = () => {
    if (!activeRunId) return;
    setIsFinalizing(true);
    fetch(`http://localhost:8000/runs/${activeRunId}/finalize`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        alert(data.status === 'finalized' ? 'Final manuscript generated!' : data.status);
        setIsFinalizing(false);
      })
      .catch(err => {
        alert("Error finalizing: " + err);
        setIsFinalizing(false);
      });
  };

  const toggleRunSelection = (runId) => {
    setSelectedRunIds(prev => 
      prev.includes(runId) 
        ? prev.filter(id => id !== runId) 
        : [...prev, runId]
    );
  };

  const currentStatus = systemStatuses.find(p => p.provider === selectedProvider) || { ready: false };

  // Prepare Compass Data
  const compassData = runData?.profile ? Object.entries(runData.profile).map(([name, value]) => ({
    subject: name,
    A: value * 100,
    fullMark: 100
  })) : [];

  // Prepare Bloom Data
  const bloomData = runData?.bloom_stats ? Object.entries(runData.bloom_stats).map(([name, value]) => ({
    name,
    count: value
  })) : [];

  const BLOOM_COLORS = {
    'Remembering': '#8b949e', 'Understanding': '#58a6ff', 'Applying': '#3fb950',
    'Analyzing': '#d29922', 'Evaluating': '#f85149', 'Creating': '#bc8cff'
  };

  const getTensionColor = (score) => {
    if (!score) return 'transparent';
    const alpha = score * 0.3;
    if (score > 0.8) return `rgba(248, 81, 73, ${alpha})`;
    if (score > 0.4) return `rgba(210, 153, 34, ${alpha})`;
    return `rgba(88, 166, 255, ${alpha})`;
  };

  return (
    <div className="studio-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Layers size={24} />
          <span>RuWritingStyles</span>
        </div>
        
        <button className="new-audit-btn" onClick={() => setIsNewRunModalOpen(true)}>
          <Plus size={18} /> New Philological Audit
        </button>

        <div className="provider-selector">
          <label>Active Intelligence</label>
          <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
            <option value="google">Google Gemini 1.5</option>
            <option value="anthropic">Claude 3.5 Sonnet</option>
            <option value="openrouter">OpenRouter (Balanced)</option>
            <option value="ollama">Local: Ollama (Llama-3)</option>
          </select>
        </div>

        <nav className="run-list-container">
          <div className="section-label">
            Audit History
            {selectedRunIds.length > 1 && (
              <button className={`compare-mini-btn ${viewMode === 'compare' ? 'active' : ''}`} onClick={() => setViewMode('compare')}>
                Compare ({selectedRunIds.length})
              </button>
            )}
          </div>
          <ul className="run-list">
            {runs.map(runId => (
              <li key={runId} className={`run-item ${activeRunId === runId ? 'active' : ''} ${selectedRunIds.includes(runId) ? 'selected' : ''}`} onClick={() => setActiveRunId(runId)}>
                <input type="checkbox" checked={selectedRunIds.includes(runId)} onChange={(e) => { e.stopPropagation(); toggleRunSelection(runId); }} />
                <span className="run-id-text">{runId}</span>
              </li>
            ))}
          </ul>
        </nav>
        
        <div className="sidebar-footer">
          <div className={`status-pill ${currentStatus.ready ? 'ready' : 'offline'}`}>
            <div className="status-dot"></div>
            <span>{selectedProvider.toUpperCase()}: {currentStatus.ready ? 'READY' : 'OFFLINE'}</span>
          </div>
          <Settings size={18} className="settings-icon" />
        </div>
      </aside>

      <main className="workbench">
        <header className="workbench-header">
          <div className="header-left">
            <h2 className="run-title">
              {viewMode === 'compare' ? `Comparison: ${selectedRunIds.length} runs` : `Workbench: ${activeRunId || 'No Run Selected'}`}
            </h2>
            {currentStatus.ready && <span className="badge">v2.2 Philological Scale</span>}
          </div>
          
          <div className="view-switcher">
            <button className={viewMode === 'audit' ? 'active' : ''} onClick={() => setViewMode('audit')}>
              <BookOpen size={16} /> Audit
            </button>
            <button className={viewMode === 'profile' ? 'active' : ''} onClick={() => setViewMode('profile')}>
              <Activity size={16} /> Profile
            </button>
            <button className={viewMode === 'syntax' ? 'active' : ''} onClick={() => setViewMode('syntax')}>
              <Layers size={16} /> Syntax
            </button>
          </div>

          <div className="header-actions">
             <button className="export-btn" onClick={handleFinalize} disabled={isFinalizing}>
               <Download size={16} /> {isFinalizing ? 'Finalizing...' : 'Finalize'}
             </button>
          </div>
        </header>

        {viewMode === 'compare' ? (
          <div className="workbench-content compare-view">
             <section className="stats-row">
               <div className="stat-card glass full-width">
                 <div className="stat-header"><Activity size={16} /><span>Stylistic Evolution (Compass Shift)</span></div>
                 <div className="chart-container large">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={comparisonData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                        <XAxis dataKey="run_id" tick={{fontSize: 10, fill: '#8b949e'}} />
                        <YAxis tick={{fontSize: 10, fill: '#8b949e'}} />
                        <Tooltip contentStyle={{backgroundColor: '#161b22', border: '1px solid #30363d'}} />
                        <Legend />
                        {/* Dynamically create lines for each school */}
                        {comparisonData.length > 0 && Object.keys(comparisonData[0].profile).map((school, i) => (
                          <Line key={school} type="monotone" dataKey={`profile.${school}`} stroke={['#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff'][i % 5]} />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                 </div>
               </div>
             </section>
             <div className="compare-grid">
               {comparisonData.map(run => (
                 <div key={run.run_id} className="run-summary-card glass">
                   <h3>{run.run_id}</h3>
                   <div className="small-stat">Bloom: {Object.values(run.bloom_stats).reduce((a,b)=>a+b, 0)} decisions</div>
                   <div className="small-stat">Duration: {run.duration ? run.duration.toFixed(1) : 'N/A'}s</div>
                 </div>
               ))}
             </div>
          </div>
        ) : runData ? (
          <div className="workbench-content">
            <section className="stats-row">
              <div className="stat-card glass">
                <div className="stat-header"><Activity size={16} /><span>Methodological Compass</span></div>
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height={150}>
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={compassData}>
                      <PolarGrid stroke="#30363d" />
                      <PolarAngleAxis dataKey="subject" tick={{fontSize: 10, fill: '#8b949e'}} />
                      <Radar name="Alignment" dataKey="A" stroke="#58a6ff" fill="#58a6ff" fillOpacity={0.6} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="stat-card glass">
                <div className="stat-header"><Zap size={16} /><span>Cognitive Depth (Bloom)</span></div>
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={bloomData} layout="vertical">
                      <XAxis type="number" hide />
                      <YAxis type="category" dataKey="name" tick={{fontSize: 10, fill: '#8b949e'}} width={80} />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {bloomData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={BLOOM_COLORS[entry.name] || '#58a6ff'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="stat-card glass">
                <div className="stat-header"><Layers size={16} /><span>Syntax & Bias</span></div>
                <div className="stat-value">{runData.syntax?.shifts?.length || 0} / {runData.bias_audit?.bias_score || 0}</div>
                <div className="stat-label">Syntax Shifts / Bias Score (0-10)</div>
              </div>

              <div className="stat-card glass">
                <div className="stat-header"><BookOpen size={16} /><span>Citation Grounding</span></div>
                <div className="stat-value">{runData.citation_stats?.verified?.length || 0} / {runData.citation_stats?.hallucinations?.length || 0}</div>
                <div className="stat-label">Verified / Hallucinations</div>
              </div>
            </section>

            {runData.bias_audit?.methodological_critique && (
              <section className="oversight-row" style={{marginBottom: '1.5rem'}}>
                <div className="stat-card glass full-width" style={{background: 'rgba(248, 81, 73, 0.05)', border: '1px solid rgba(248, 81, 73, 0.2)'}}>
                  <div className="stat-header" style={{color: '#f85149'}}><Info size={16} /><span>Methodological Audit Critique</span></div>
                  <div className="critique-text" style={{fontSize: '0.9rem', color: '#c9d1d9', marginTop: '0.5rem', lineHeight: '1.5'}}>
                    {runData.bias_audit.methodological_critique}
                  </div>
                </div>
              </section>
            )}

            <section className="main-grid">
              <div className="editor-section">
                <div className="dual-editor glass">
                  <div className="pane">
                    <div className="pane-header">Manuscript & Tension Map</div>
                    <div className="pane-scroll">
                      <div className="text-content">
                        {runData.segments?.segments?.map((seg, i) => (
                          <span key={i} className="text-segment" style={{ background: getTensionColor(runData.tension?.[seg.span_id]), borderBottom: runData.tension?.[seg.span_id] > 0.5 ? '1px dashed #f85149' : 'none' }}>{seg.text}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="pane">
                    <div className="pane-header">Philological Revision</div>
                    <div className="pane-scroll"><div className="text-content revised">{runData.revised_text}</div></div>
                  </div>
                </div>

                <div className="decisions-panel glass">
                   <div className="panel-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                     <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><MessageSquare size={16} />Council Deliberations</div>
                     {Object.keys(resolutions).length > 0 && (
                       <button className="apply-res-btn" onClick={handleApplyResolutions} style={{padding: '4px 8px', fontSize: '12px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>
                         Apply Overrides ({Object.keys(resolutions).length})
                       </button>
                     )}
                   </div>
                   <div className="decisions-list">
                     {runData.council?.decisions?.map((d, i) => {
                       const currentRes = resolutions[d.finding_id] || { status: d.status, human_comment: '' };
                       return (
                       <div key={i} className="decision-item">
                         <div className="decision-meta">
                           <span className="span-tag">{d.finding_id}</span>
                           <span className={`status-tag ${currentRes.status}`}>{currentRes.status}</span>
                           <span className="bloom-tag" style={{background: BLOOM_COLORS[d.bloom_level]}}>{d.bloom_level}</span>
                           <select 
                             value={currentRes.status} 
                             onChange={(e) => setResolutions(prev => ({...prev, [d.finding_id]: {...currentRes, finding_id: d.finding_id, status: e.target.value}}))}
                             style={{marginLeft: 'auto', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '4px'}}
                           >
                             <option value="accepted">Accept</option>
                             <option value="rejected">Reject</option>
                           </select>
                         </div>
                         <div className="decision-text">{d.reason}</div>
                         <input 
                           type="text" 
                           placeholder="Human override comment..." 
                           value={currentRes.human_comment}
                           onChange={(e) => setResolutions(prev => ({...prev, [d.finding_id]: {...currentRes, finding_id: d.finding_id, human_comment: e.target.value}}))}
                           style={{width: '100%', marginTop: '8px', padding: '4px 8px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', borderRadius: '4px', fontSize: '12px'}}
                         />
                         {d.influence && (
                           <div className="school-tags" style={{marginTop: '8px'}}>
                             {Object.entries(d.influence).map(([school, weight]) => (
                               <span key={school} className="school-tag">{school}: {Math.round(weight*100)}%</span>
                             ))}
                           </div>
                         )}
                       </div>
                     )})}
                   </div>
                </div>
              </div>

              <aside className="concordance-sidebar glass">
                <div className="panel-header" style={{display: 'flex', gap: '1rem', borderBottom: '1px solid #30363d'}}>
                  <button className={`tab-btn ${!showCitations ? 'active' : ''}`} onClick={() => setShowCitations(false)} style={{background: 'none', border: 'none', color: !showCitations ? '#58a6ff' : '#8b949e', cursor: 'pointer', fontSize: '0.9rem', paddingBottom: '0.5rem', borderBottom: !showCitations ? '2px solid #58a6ff' : 'none'}}>Concordance</button>
                  <button className={`tab-btn ${showCitations ? 'active' : ''}`} onClick={() => setShowCitations(true)} style={{background: 'none', border: 'none', color: showCitations ? '#58a6ff' : '#8b949e', cursor: 'pointer', fontSize: '0.9rem', paddingBottom: '0.5rem', borderBottom: showCitations ? '2px solid #58a6ff' : 'none'}}>Citations</button>
                </div>
                <div className="concordance-content" style={{paddingTop: '1rem'}}>
                  {!showCitations ? (
                    Object.keys(concordance).length > 0 ? (
                      Object.entries(concordance).map(([term, matches]) => (
                        <div key={term} className="concordance-group">
                          <div className="term-label">{term}</div>
                          {matches.map((m, i) => (
                            <div key={i} className="concordance-match">
                              <div className="match-source">{m.source}</div>
                              <div className="match-text">«{m.text}»</div>
                            </div>
                          ))}
                        </div>
                      ))
                    ) : (
                      <div className="empty-concordance"><Info size={24} /><p>No academic precedents found.</p></div>
                    )
                  ) : (
                    <div className="citations-list">
                      <div className="section-label">Verified Grounding</div>
                      {runData.citation_stats?.verified?.map((c, i) => (
                        <div key={i} className="citation-item verified" style={{borderLeft: '2px solid #3fb950', paddingLeft: '8px', marginBottom: '8px'}}>
                          <div className="cite-text" style={{fontWeight: 'bold'}}>{c.citation}</div>
                          <div className="cite-source" style={{fontSize: '0.8rem', color: '#8b949e'}}>{c.entry?.title || c.source_file}</div>
                        </div>
                      ))}
                      <div className="section-label" style={{marginTop: '1.5rem'}}>Hallucinations / Missing</div>
                      {runData.citation_stats?.hallucinations?.map((c, i) => (
                        <div key={i} className="citation-item failed" style={{borderLeft: '2px solid #f85149', paddingLeft: '8px', marginBottom: '8px'}}>
                          <div className="cite-text" style={{fontWeight: 'bold', color: '#f85149'}}>{c.citation}</div>
                          <div className="cite-reason" style={{fontSize: '0.8rem', color: '#8b949e'}}>{c.reason}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </aside>
            </section>
          </div>
        ) : (
          <div className="empty-state">
            <Search size={48} />
            <h2>Select an Audit to begin</h2>
            <p>Or start a new investigation using the sidebar.</p>
          </div>
        )}
      </main>

      {isNewRunModalOpen && (
        <div className="modal-overlay">
          <div className="modal glass">
            <div className="modal-header"><Plus size={20} /><h3>New Philological Audit</h3></div>
            <div className="modal-body">
              <p>Initialize a new automated stylistic audit. Specify the absolute path to your source manuscript (.md, .txt).</p>
              <div className="input-group">
                <label>Manuscript Path</label>
                <input type="text" value={newRunPath} onChange={(e) => setNewRunPath(e.target.value)} />
              </div>
              <div className="modal-actions">
                <button className="cancel-btn" onClick={() => setIsNewRunModalOpen(false)}>Cancel</button>
                <button className="start-btn" onClick={handleStartRun}>Execute Audit</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {trace.length > 0 && (
        <div className="thinking-trace-container glass">
          <div className="trace-header">
            <div className="trace-title">
              <Zap size={14} />
              <span>Thinking Trace</span>
            </div>
            <div className="live-pulse"></div>
          </div>
          <div className="trace-content">
            {trace.map((item, idx) => (
              <div key={idx} className="trace-item">
                <div className="trace-time">{item.timestamp}</div>
                <div className="trace-message">
                  {item.type === 'step_update' ? (
                    <span>
                      Step <span className="trace-type-step">{item.step_id}</span> is <b>{item.status}</b>
                    </span>
                  ) : item.type === 'tool_call' ? (
                    <span>
                      Calling <span className="trace-type-tool">{item.tool_name}</span> for {item.task}
                    </span>
                  ) : item.type === 'injection_received' ? (
                    <span style={{color: 'var(--accent-primary)', fontWeight: 'bold'}}>
                      Socratic Injection Queued: "{item.content}"
                    </span>
                  ) : (
                    <span>Run status: <b>{item.status}</b></span>
                  )}
                </div>
                {item.arguments && (
                  <div className="trace-details">
                    Query: {item.arguments.query}
                  </div>
                )}
                {item.result && item.result.results && item.result.results.length > 0 && (
                  <div className="trace-details" style={{color: 'var(--accent-success)'}}>
                    Found: {item.result.results[0].title || item.result.results[0].id}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="trace-input-container">
            <input 
              type="text" 
              className="trace-input" 
              placeholder="Inject scholarly argument..." 
              value={injectionText}
              onChange={(e) => setInjectionText(e.target.value)}
              onKeyDown={handleInjectionSubmit}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
