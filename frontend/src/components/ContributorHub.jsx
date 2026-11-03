import React, { useState } from 'react';
import {
  GitPullRequest,
  Terminal,
  Code2,
  Cpu,
  Layers,
  Database,
  CheckCircle2,
  Copy,
  Check,
  BookOpen,
  Sparkles,
  Share2
} from 'lucide-react';

export default function ContributorHub() {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('llm');

  const copyCloneCmd = () => {
    navigator.clipboard.writeText('git clone https://github.com/Vipul4510/Datachat.git');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Open Source Lab Hero */}
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-blue-950/40 via-slate-900/90 to-indigo-950/40 border border-blue-800/60 shadow-2xl backdrop-blur-md relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-700/80 text-blue-400 text-xs font-semibold mb-3">
              <GitPullRequest className="w-4 h-4" />
              <span>Open Source Research Lab Project</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Community Contributor Hub
            </h2>
            <p className="text-sm text-slate-300 mt-2 leading-relaxed">
              DataChat is built as an open, modular research lab. Anyone can contribute new AI providers,
              analytical database connectors, statistical anomaly detectors, and custom chart designs.
            </p>
          </div>

          <div className="flex flex-col gap-2 min-w-[220px]">
            <button
              onClick={copyCloneCmd}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 shadow-md transition"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-cyan-400" />}
              <span>{copied ? 'Copied Clone Command!' : 'Copy git clone URL'}</span>
            </button>
            <div className="text-center text-[11px] text-slate-400 font-mono">
              MIT License • Contributions Welcome
            </div>
          </div>
        </div>
      </div>

      {/* Architecture System Map */}
      <div className="p-6 rounded-3xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur-md">
        <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Modular System Architecture</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-1">
              1. Frontend UI
            </div>
            <div className="text-sm font-bold text-slate-200">React 19 + Vite</div>
            <p className="text-xs text-slate-400 mt-2">
              Recharts visualizer, 3D Hero canvas, dark glassmorphism design system.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1">
              2. API Gateway
            </div>
            <div className="text-sm font-bold text-slate-200">FastAPI (Python 3.11)</div>
            <p className="text-xs text-slate-400 mt-2">
              Asynchronous endpoints, CORS, file streaming, session quality profiling.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">
              3. Vectorized OLAP
            </div>
            <div className="text-sm font-bold text-slate-200">DuckDB C++ Engine</div>
            <p className="text-xs text-slate-400 mt-2">
              In-memory columnar execution, zero-copy query engine, CSV/Parquet reader.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80">
            <div className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-1">
              4. LLM Intelligence
            </div>
            <div className="text-sm font-bold text-slate-200">Schema-Only Reasoning</div>
            <p className="text-xs text-slate-400 mt-2">
              Groq (Llama-3.3) + Gemini fallback + 3-step automated SQL self-correction loop.
            </p>
          </div>
        </div>
      </div>

      {/* Interactive Contributor Extension Guides */}
      <div className="p-6 rounded-3xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5 pb-3 border-b border-slate-800/60">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Code2 className="w-4 h-4 text-cyan-400" />
              <span>Extensibility Guide: How to Add Features</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Pick a domain below to see the exact code and location to implement your enhancement.
            </p>
          </div>

          <div className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('llm')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'llm' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Add LLM Provider
            </button>
            <button
              onClick={() => setActiveTab('db')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'db' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Add DB Connector
            </button>
            <button
              onClick={() => setActiveTab('clean')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'clean' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Add Cleaning Recipe
            </button>
            <button
              onClick={() => setActiveTab('chart')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'chart' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Add Chart Type
            </button>
          </div>
        </div>

        {/* Tab 1: LLM */}
        {activeTab === 'llm' && (
          <div className="space-y-3">
            <div className="text-xs text-slate-300">
              Target File: <code className="text-cyan-400 font-mono">backend/services/llm.py</code>
            </div>
            <p className="text-xs text-slate-400">
              Add your custom local or cloud LLM function (e.g. Ollama, Claude 3.5, DeepSeek) and include it in <code className="text-cyan-400 font-mono">run_nl_query_with_self_correction</code>:
            </p>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre>{`def _call_ollama(messages: List[Dict[str, str]], model: str = "llama3.2") -> str:
    url = "http://localhost:11434/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, json=payload)
        return resp.json()["message"]["content"]`}</pre>
            </div>
          </div>
        )}

        {/* Tab 2: DB Connector */}
        {activeTab === 'db' && (
          <div className="space-y-3">
            <div className="text-xs text-slate-300">
              Target File: <code className="text-cyan-400 font-mono">backend/services/loader.py</code>
            </div>
            <p className="text-xs text-slate-400">
              DuckDB has native extensions for PostgreSQL, SQLite, and ClickHouse. You can attach remote databases directly:
            </p>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre>{`def attach_sqlite_db(db_path: str):
    conn = get_connection()
    conn.execute(f"ATTACH '{db_path}' AS sqlite_db (TYPE SQLITE)")
    return list_attached_tables(conn)`}</pre>
            </div>
          </div>
        )}

        {/* Tab 3: Cleaning Recipe */}
        {activeTab === 'clean' && (
          <div className="space-y-3">
            <div className="text-xs text-slate-300">
              Target File: <code className="text-cyan-400 font-mono">backend/services/cleaner.py</code>
            </div>
            <p className="text-xs text-slate-400">
              Add custom transformations to <code className="text-cyan-400 font-mono">apply_cleaning_actions</code>:
            </p>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre>{`elif action == "standardize_dates":
    # Custom cleaning action
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
    changes.append(f"Standardized {len(date_cols)} date columns to ISO-8601")`}</pre>
            </div>
          </div>
        )}

        {/* Tab 4: Chart */}
        {activeTab === 'chart' && (
          <div className="space-y-3">
            <div className="text-xs text-slate-300">
              Target File: <code className="text-cyan-400 font-mono">frontend/src/components/ChartRenderer.jsx</code>
            </div>
            <p className="text-xs text-slate-400">
              Import additional Recharts or Three.js visualizers (e.g. RadarChart, Treemap, ScatterPlot):
            </p>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre>{`import { RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts';
// Render Radar component inside ResponsiveContainer when type === 'radar'`}</pre>
            </div>
          </div>
        )}
      </div>

      {/* Community Checklist */}
      <div className="p-6 rounded-3xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Ready to Submit a Pull Request?</span>
          </h4>
          <p className="text-xs text-slate-400 mt-1">
            Check the contribution guide in <code className="text-cyan-400 font-mono">CONTRIBUTING.md</code> at the project root for testing commands and PR guidelines.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-mono border border-slate-700">
            pytest tests/
          </span>
          <span className="text-xs px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-mono border border-slate-700">
            npm run build
          </span>
        </div>
      </div>
    </div>
  );
}
