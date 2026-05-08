import { useCallback, useEffect, useState } from 'react';
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell
} from 'recharts';
import { 
  Search, BookOpen, Activity, Layers, MessageSquare, AlertTriangle, 
  CheckCircle, ChevronRight, Settings, Download, Plus, Info, Zap
} from 'lucide-react';

function App() {
  const [runs, setRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [concordance, setConcordance] = useState({});
  const [systemStatuses, setSystemStatuses] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('google');
  const [isNewRunModalOpen, setIsNewRunModalOpen] = useState(false);
  const [newRunPath, setNewRunPath] = useState('C:\\Users\\user\\Documents\\GitHub\\RuWritingStyles\\article.md');
  const [viewMode, setViewMode] = useState('audit'); // 'audit', 'profile', 'syntax'

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
        .then(data => {
          setRunData(data);
          // Fetch concordance for this run
          fetch(`http://localhost:8000/runs/${activeRunId}/concordance`)
            .then(res => res.json())
            .then(concData => setConcordance(concData));
        });
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
    'Remembering': '#8b949e',
    'Understanding': '#58a6ff',
    'Applying': '#3fb950',
    'Analyzing': '#d29922',
    'Evaluating': '#f85149',
    'Creating': '#bc8cff'
  };

  const getTensionColor = (score) => {
    if (!score) return 'transparent';
    const alpha = score * 0.3;
    if (score > 0.8) return `rgba(248, 81, 73, ${alpha})`; // High tension: Red
    if (score > 0.4) return `rgba(210, 153, 34, ${alpha})`; // Medium tension: Orange
    return `rgba(88, 166, 255, ${alpha})`; // Low tension: Blue
  };

  return (
    <div className="studio-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Layers size={24} />
          <span>RuWritingStyles</span>
        </div>
        
        <button 
          className="new-audit-btn"
          onClick={() => setIsNewRunModalOpen(true)}
        >
          <Plus size={18} />
          New Philological Audit
        </button>

        <div className="provider-selector">
          <label>Active Intelligence</label>
          <select 
            value={selectedProvider} 
            onChange={(e) => setSelectedProvider(e.target.value)}
          >
            <option value="google">Google Gemini 1.5</option>
            <option value="anthropic">Claude 3.5 Sonnet</option>
            <option value="openrouter">OpenRouter (Balanced)</option>
          </select>
        </div>

        <nav className="run-list-container">
          <div className="section-label">Audit History</div>
          <ul className="run-list">
            {runs.map(runId => (
              <li 
                key={runId} 
                className={`run-item ${activeRunId === runId ? 'active' : ''}`}
                onClick={() => setActiveRunId(runId)}
              >
                < chevronRight size={14} />
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
            <h2 className="run-title">Workbench: {activeRunId || 'No Run Selected'}</h2>
            {currentStatus.ready && <span className="badge">v2.0 Scholarly Harness</span>}
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
             <button className="export-btn">
               <Download size={16} /> Export
             </button>
          </div>
        </header>

        {runData ? (
          <div className="workbench-content">
            <section className="stats-row">
              <div className="stat-card glass">
                <div className="stat-header">
                  <Activity size={16} />
                  <span>Methodological Compass</span>
                </div>
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
                <div className="stat-header">
                  <Zap size={16} />
                  <span>Cognitive Depth (Bloom)</span>
                </div>
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
                <div className="stat-header">
                  <Layers size={16} />
                  <span>Syntax Complexity</span>
                </div>
                <div className="stat-value">{runData.syntax?.shifts?.length || 0}</div>
                <div className="stat-label">Significant shifts detected</div>
              </div>
            </section>

            <section className="main-grid">
              <div className="editor-section">
                <div className="dual-editor glass">
                  <div className="pane">
                    <div className="pane-header">Manuscript & Tension Map</div>
                    <div className="pane-scroll">
                      <div className="text-content">
                        {runData.segments?.segments?.map((seg, i) => (
                          <span 
                            key={i} 
                            className="text-segment"
                            style={{ 
                              background: getTensionColor(runData.tension?.[seg.span_id]),
                              borderBottom: runData.tension?.[seg.span_id] > 0.5 ? '1px dashed #f85149' : 'none'
                            }}
                            title={runData.tension?.[seg.span_id] ? `Tension Score: ${runData.tension[seg.span_id]}` : ''}
                          >
                            {seg.text}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="pane">
                    <div className="pane-header">Philological Revision</div>
                    <div className="pane-scroll">
                      <div className="text-content revised">
                        {runData.revised_text}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="decisions-panel glass">
                   <div className="panel-header">
                     <MessageSquare size={16} />
                     Council Deliberations
                   </div>
                   <div className="decisions-list">
                     {runData.council?.decisions?.map((d, i) => (
                       <div key={i} className="decision-item">
                         <div className="decision-meta">
                           <span className="span-tag">{d.finding_id}</span>
                           <span className={`status-tag ${d.status}`}>{d.status}</span>
                           <span className="bloom-tag" style={{background: BLOOM_COLORS[d.bloom_level]}}>{d.bloom_level}</span>
                         </div>
                         <div className="decision-text">{d.reason}</div>
                         {d.influence && (
                           <div className="school-tags">
                             {Object.entries(d.influence).map(([school, weight]) => (
                               <span key={school} className="school-tag">{school}: {Math.round(weight*100)}%</span>
                             ))}
                           </div>
                         )}
                       </div>
                     ))}
                   </div>
                </div>
              </div>

              <aside className="concordance-sidebar glass">
                <div className="panel-header">
                  <BookOpen size={16} />
                  Interactive Concordance
                </div>
                <div className="concordance-content">
                  {Object.keys(concordance).length > 0 ? (
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
                    <div className="empty-concordance">
                      <Info size={24} />
                      <p>No academic precedents found for this passage.</p>
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
            <p>Or start a new philological investigation using the sidebar.</p>
          </div>
        )}
      </main>

      {isNewRunModalOpen && (
        <div className="modal-overlay">
          <div className="modal glass">
            <div className="modal-header">
              <Plus size={20} />
              <h3>New Philological Audit</h3>
            </div>
            <div className="modal-body">
              <p>Initialize a new automated stylistic audit. Specify the absolute path to your source manuscript (.md, .txt).</p>
              <div className="input-group">
                <label>Manuscript Path</label>
                <input 
                  type="text" 
                  value={newRunPath}
                  onChange={(e) => setNewRunPath(e.target.value)}
                  placeholder="C:/Users/Research/draft.md"
                />
              </div>
              <div className="modal-actions">
                <button className="cancel-btn" onClick={() => setIsNewRunModalOpen(false)}>Cancel</button>
                <button className="start-btn" onClick={handleStartRun}>Execute Audit</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
