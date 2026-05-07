"""Project-wide interactive dashboard generation."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any


def generate_project_dashboard(repo_root: Path, output_path: Path | None = None) -> Path:
    """Generate a comprehensive HTML dashboard for the entire project."""
    
    runs_dir = repo_root / "runs"
    run_folders = [d for d in runs_dir.iterdir() if d.is_dir() and (d / "segments.json").exists()]
    
    dashboard_data = []
    
    for run_dir in run_folders:
        run_info = {
            "id": run_dir.name,
            "timestamp": datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "style": "unknown",
            "status": "unknown",
            "findings": 0,
            "sentiment": None,
            "peer_review": None
        }
        
        # Load segments for style/source
        seg_path = run_dir / "segments.json"
        if seg_path.exists():
            segs = json.loads(seg_path.read_text(encoding="utf-8"))
            run_info["source"] = Path(segs.get("input_path", "unknown")).name
            
        # Load verification for status
        ver_path = run_dir / "verification.json"
        if ver_path.exists():
            ver = json.loads(ver_path.read_text(encoding="utf-8"))
            run_info["status"] = ver.get("status", "unknown")
            
        # Sentiment
        sent_path = run_dir / "sentiment.json"
        if sent_path.exists():
            run_info["sentiment"] = json.loads(sent_path.read_text(encoding="utf-8"))
            
        dashboard_data.append(run_info)
        
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>RuWritingStyles - Project Dashboard</title>
        <style>
            body {{ font-family: 'Segoe UI', system-ui; background: #f0f2f5; margin: 0; padding: 2rem; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
            .card {{ background: #fff; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .stat-val {{ font-size: 2rem; font-weight: bold; color: #007bff; }}
            table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #f8f9fa; font-weight: 600; color: #666; }}
            tr:hover {{ background: #fcfcfc; }}
            .badge {{ padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.85rem; }}
            .status-completed {{ background: #d4edda; color: #155724; }}
            .sentiment-box {{ display: flex; gap: 4px; }}
            .sent-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Corpus Dashboard</h1>
                <div class="muted">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
            </div>
            
            <div class="stats-grid">
                <div class="card">
                    <div class="muted">Total Runs</div>
                    <div class="stat-val">{len(dashboard_data)}</div>
                </div>
                <div class="card">
                    <div class="muted">Successful Revisions</div>
                    <div class="stat-val">{sum(1 for r in dashboard_data if r['status'] == 'completed')}</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Processing Queue</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Source</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th>Sentiment Shift (Dist)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {" ".join(f'''
                        <tr>
                            <td><code>{r['id']}</code></td>
                            <td>{r.get('source', '-')}</td>
                            <td>{r['timestamp']}</td>
                            <td><span class="badge status-{r['status']}">{r['status']}</span></td>
                            <td>{r['sentiment']['deltas']['distance'] if r['sentiment'] else '-'}</td>
                        </tr>
                        ''' for r in sorted(dashboard_data, key=lambda x: x['timestamp'], reverse=True))}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    if output_path is None:
        output_path = repo_root / "DASHBOARD.html"
        
    output_path.write_text(html, encoding="utf-8")
    return output_path
