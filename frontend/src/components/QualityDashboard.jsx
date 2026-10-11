import React, { useState } from 'react';
import { Database, AlertTriangle, Layers, Activity, Download, ChevronDown, ChevronUp, FileSpreadsheet, FileText } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function QualityDashboard({ report, metadata, onExport }) {
  const [showPreview, setShowPreview] = useState(false);
  const [showColumns, setShowColumns] = useState(false);

  if (!report) return null;

  const {
    health_score,
    health_status,
    row_count,
    column_count,
    missing_cells,
    missing_cells_percentage,
    duplicate_rows,
    duplicate_percentage,
    total_iqr_outliers,
    columns = [],
    preview_rows = [],
  } = report;

  // Health color mapping
  const getScoreBadge = (score) => {
    if (score >= 85) return 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30';
    if (score >= 70) return 'text-cyan-400 bg-cyan-950/40 border-cyan-500/30';
    if (score >= 50) return 'text-amber-400 bg-amber-950/40 border-amber-500/30';
    return 'text-rose-400 bg-rose-950/40 border-rose-500/30';
  };

  // Missing values data for chart
  const missingData = columns
    .filter((c) => c.null_count > 0)
    .map((c) => ({
      column: c.column_name,
      missingCount: c.null_count,
      missingPct: c.null_percentage,
    }));

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md mb-8">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              DuckDB In-Process
            </span>
            <span className="text-xs font-mono text-slate-400">
              {metadata?.original_filename}
            </span>
          </div>
          <h2 className="text-xl font-bold text-white mt-1">Data Quality & Health Overview</h2>
        </div>

        {/* Export buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onExport('xlsx')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            Excel Export
          </button>
          <button
            onClick={() => onExport('pdf')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <FileText className="w-3.5 h-3.5 text-rose-400" />
            PDF Report
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
        {/* Health Score */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Health Score</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{health_score}</span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
          <div className="mt-2">
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${getScoreBadge(health_score)}`}>
              {health_status}
            </span>
          </div>
        </div>

        {/* Rows & Columns */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Dataset Shape</span>
            <Database className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-white">{row_count.toLocaleString()}</div>
            <div className="text-xs text-slate-400">{column_count} columns</div>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 font-mono">
            {metadata?.format?.toUpperCase()} format
          </div>
        </div>

        {/* Missing Values */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Missing Values</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-white">{missing_cells.toLocaleString()}</div>
            <div className="text-xs text-amber-400 font-medium">{missing_cells_percentage}% total cells</div>
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            {missingData.length} columns affected
          </div>
        </div>

        {/* Duplicates & Outliers */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Data Anomalies</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-white">{duplicate_rows} duplicates</div>
            <div className="text-xs text-slate-400">{total_iqr_outliers} IQR outliers</div>
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            {duplicate_percentage}% duplicate rate
          </div>
        </div>
      </div>

      {/* Missing Values Chart (if any missing values exist) */}
      {missingData.length > 0 && (
        <div className="mt-6 p-4 bg-slate-950/40 border border-slate-800/80 rounded-xl">
          <h4 className="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-2">
            Missing Values by Column
          </h4>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={missingData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="column" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem' }}
                />
                <Bar dataKey="missingCount" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Missing Cells" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Expandable Preview Table */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center justify-between w-full text-xs font-semibold uppercase tracking-wider text-slate-300 hover:text-white"
        >
          <span>Data Preview (Top 5 rows)</span>
          {showPreview ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showPreview && preview_rows.length > 0 && (
          <div className="mt-3 overflow-x-auto rounded-xl border border-slate-800">
            <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400">
                <tr>
                  {Object.keys(preview_rows[0]).map((col) => (
                    <th key={col} className="px-3 py-2 font-medium">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-900/30 text-slate-300 font-mono">
                {preview_rows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40">
                    {Object.values(row).map((val, cIdx) => (
                      <td key={cIdx} className="px-3 py-2 whitespace-nowrap">
                        {val === null || val === undefined ? (
                          <span className="text-slate-600 italic">null</span>
                        ) : (
                          String(val)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Expandable Column Schema Details */}
      <div className="mt-4 border-t border-slate-800/60 pt-3">
        <button
          onClick={() => setShowColumns(!showColumns)}
          className="flex items-center justify-between w-full text-xs font-semibold uppercase tracking-wider text-slate-300 hover:text-white"
        >
          <span>Column Metadata & Schema ({columns.length} columns)</span>
          {showColumns ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showColumns && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {columns.map((c) => (
              <div key={c.column_name} className="p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/60">
                <div className="font-semibold text-white truncate">{c.column_name}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Type: <span className="text-cyan-400 font-mono">{c.data_type}</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Nulls: {c.null_count} ({c.null_percentage}%) | Distinct: {c.distinct_count}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
