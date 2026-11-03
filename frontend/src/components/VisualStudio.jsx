import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import ChartRenderer from './ChartRenderer';
import {
  BarChart3,
  TrendingUp,
  PieChart as PieIcon,
  Sparkles,
  Layers,
  Database,
  Sliders,
  PlusCircle,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileText
} from 'lucide-react';

export default function VisualStudio({ tableId, metadata, onExport }) {
  const [visData, setVisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Custom Chart Builder state
  const [customX, setCustomX] = useState('');
  const [customY, setCustomY] = useState('');
  const [customAgg, setCustomAgg] = useState('sum');
  const [customType, setCustomType] = useState('bar');
  const [buildingChart, setBuildingChart] = useState(false);
  const [customChartResult, setCustomChartResult] = useState(null);
  const [customError, setCustomError] = useState(null);

  const fetchVisualizations = async () => {
    if (!tableId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getVisualizations(tableId);
      setVisData(data);

      // Pre-select defaults for custom builder
      if (data.columns_summary) {
        if (data.columns_summary.categorical.length > 0) {
          setCustomX(data.columns_summary.categorical[0]);
        } else if (metadata?.schema?.length > 0) {
          setCustomX(metadata.schema[0].column_name);
        }

        if (data.columns_summary.numeric.length > 0) {
          setCustomY(data.columns_summary.numeric[0]);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate visual charts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVisualizations();
  }, [tableId]);

  const handleBuildCustomChart = async (e) => {
    e?.preventDefault();
    if (!customX) return;
    setBuildingChart(true);
    setCustomError(null);
    try {
      const res = await api.createCustomChart(tableId, {
        x_col: customX,
        y_col: customAgg === 'count' ? null : customY || null,
        agg: customAgg,
        chart_type: customType,
        limit: 20
      });
      setCustomChartResult(res);
    } catch (err) {
      setCustomError(err.response?.data?.detail || err.message || 'Failed to render custom chart.');
    } finally {
      setBuildingChart(false);
    }
  };

  const schemaCols = metadata?.schema || [];
  const numericCols = visData?.columns_summary?.numeric || [];
  const catCols = visData?.columns_summary?.categorical || [];

  return (
    <div className="space-y-6">
      {/* Studio Header Banner */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-slate-900/90 via-cyan-950/30 to-slate-900/90 border border-slate-800 shadow-2xl backdrop-blur-md relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-400 text-xs font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Instant DuckDB Vectorized Visual Studio</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Visual Analytics & Chart Studio
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              High-throughput graphical analysis directly from local RAM. Zero external cloud ingestion.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onExport && (
              <button
                onClick={() => onExport('pdf')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-rose-600/30 to-pink-600/30 hover:from-rose-600/40 hover:to-pink-600/40 text-rose-300 text-xs font-semibold border border-rose-500/40 transition shadow-sm active:scale-95"
                title="Download complete visual & statistical PDF report"
              >
                <FileText className="w-3.5 h-3.5 text-rose-400" />
                <span>Download PDF Report</span>
              </button>
            )}
            <button
              onClick={fetchVisualizations}
              disabled={loading}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Quick Metrics Bar */}
        {visData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-slate-800/80">
            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
              <div className="text-[11px] text-slate-400 font-medium">Dataset Records</div>
              <div className="text-xl font-bold text-white mt-0.5">
                {visData.columns_summary?.total_rows?.toLocaleString() || metadata?.row_count?.toLocaleString()}
              </div>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
              <div className="text-[11px] text-slate-400 font-medium">Numeric Metrics</div>
              <div className="text-xl font-bold text-cyan-400 mt-0.5">
                {numericCols.length} columns
              </div>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
              <div className="text-[11px] text-slate-400 font-medium">Categorical Dimensions</div>
              <div className="text-xl font-bold text-blue-400 mt-0.5">
                {catCols.length} columns
              </div>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
              <div className="text-[11px] text-slate-400 font-medium">Local Storage</div>
              <div className="text-xl font-bold text-emerald-400 mt-0.5">
                DuckDB :memory:
              </div>
            </div>
          </div>
        )}
      </div>

      {/* KPI Cards Row */}
      {visData?.kpi_cards && visData.kpi_cards.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <span>Key Numerical Indicators</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {visData.kpi_cards.map((kpi, idx) => (
              <div
                key={idx}
                className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 shadow-md backdrop-blur-sm hover:border-cyan-500/30 transition"
              >
                <div className="text-xs font-medium text-slate-300 truncate" title={kpi.column}>
                  {kpi.column}
                </div>
                <div className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-sky-300 mt-1">
                  {kpi.sum?.toLocaleString()}
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 mt-3 pt-2.5 border-t border-slate-800/60">
                  <span>Avg: <strong className="text-slate-200">{kpi.avg}</strong></span>
                  <span>Min: <strong className="text-slate-200">{kpi.min}</strong></span>
                  <span>Max: <strong className="text-slate-200">{kpi.max}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Custom Chart Builder */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-slate-200">Interactive Custom Chart Builder</h3>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">Realtime DuckDB SQL Synthesis</span>
        </div>

        <form onSubmit={handleBuildCustomChart} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* X Axis Dimension */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">X-Axis (Dimension)</label>
            <select
              value={customX}
              onChange={(e) => setCustomX(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {schemaCols.map((c) => (
                <option key={c.column_name} value={c.column_name}>
                  {c.column_name} ({c.column_type})
                </option>
              ))}
            </select>
          </div>

          {/* Aggregation */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Aggregation</label>
            <select
              value={customAgg}
              onChange={(e) => setCustomAgg(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="sum">SUM (Total)</option>
              <option value="avg">AVG (Mean)</option>
              <option value="count">COUNT (Rows)</option>
              <option value="max">MAX (Peak)</option>
              <option value="min">MIN (Floor)</option>
            </select>
          </div>

          {/* Y Axis Metric (Disabled if count) */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Y-Axis (Metric)</label>
            <select
              value={customY}
              disabled={customAgg === 'count'}
              onChange={(e) => setCustomY(e.target.value)}
              className={`w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 ${
                customAgg === 'count' ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {numericCols.length > 0 ? (
                numericCols.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))
              ) : (
                <option value="">No numeric columns</option>
              )}
            </select>
          </div>

          {/* Chart Type */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Visual Format</label>
            <select
              value={customType}
              onChange={(e) => setCustomType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="bar">Bar Chart</option>
              <option value="line">Line Chart</option>
              <option value="area">Area Chart</option>
              <option value="pie">Donut / Pie Chart</option>
            </select>
          </div>

          {/* Submit */}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={buildingChart || !customX}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 transition disabled:opacity-50"
            >
              {buildingChart ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <PlusCircle className="w-3.5 h-3.5" />
              )}
              <span>Plot Custom Chart</span>
            </button>
          </div>
        </form>

        {customError && (
          <div className="mt-3 p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{customError}</span>
          </div>
        )}

        {/* Active Custom Chart Display */}
        {customChartResult && (
          <div className="mt-4 pt-4 border-t border-slate-800">
            <ChartRenderer chart={customChartResult} allowTypeToggle={true} />
          </div>
        )}
      </div>

      {/* Auto-Generated Charts Gallery */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Automated Visual Gallery</span>
        </h3>

        {loading ? (
          <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl border border-slate-800">
            <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mb-3" />
            <span className="text-sm">Synthesizing multi-dimensional charts in DuckDB...</span>
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-sm">
            {error}
          </div>
        ) : visData?.charts?.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {visData.charts.map((ch, idx) => (
              <ChartRenderer key={ch.id || idx} chart={ch} allowTypeToggle={true} />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
            No automatic charts generated. Use the Custom Chart Builder above to plot any dimension!
          </div>
        )}
      </div>
    </div>
  );
}
