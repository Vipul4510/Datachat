import React, { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { BarChart3, LineChart as LineIcon, PieChart as PieIcon, Activity } from 'lucide-react';

const COLORS = [
  '#06b6d4', // cyan-500
  '#3b82f6', // blue-500
  '#8b5cf6', // purple-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ec4899', // pink-500
  '#6366f1', // indigo-500
  '#14b8a6', // teal-500
];

export default function ChartRenderer({ chart, allowTypeToggle = true }) {
  if (!chart || chart.type === 'none' || chart.type === 'table') return null;
  const initialType = (chart.type === 'donut' ? 'pie' : chart.type);
  const [activeType, setActiveType] = useState(initialType);

  if (chart.type === 'metric') {
    return (
      <div className="bg-gradient-to-br from-slate-900/90 to-slate-950/80 border border-slate-800 rounded-2xl p-5 my-3 inline-block shadow-lg shadow-cyan-950/20 backdrop-blur-md">
        <div className="text-xs uppercase tracking-wider text-slate-400 font-medium flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>{chart.title}</span>
        </div>
        <div className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mt-2">
          {typeof chart.value === 'number' ? chart.value.toLocaleString() : String(chart.value)}
          {chart.unit && <span className="text-sm font-normal text-slate-400 ml-1.5">{chart.unit}</span>}
        </div>
      </div>
    );
  }

  const { data, xAxis, yAxis, series, nameKey, dataKey, title } = chart;
  if (!data || data.length === 0) return null;

  const currentXAxis = xAxis || 'name' || 'category';
  const currentYAxis = yAxis || (series && series[0]) || dataKey || 'value';
  const currentSeries = series && series.length > 0 ? series : [currentYAxis];

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800/90 rounded-2xl p-4 sm:p-5 my-3 backdrop-blur-md shadow-xl shadow-black/40">
      {/* Chart Header & Type Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-800/60">
        <div>
          <h4 className="text-sm font-semibold text-slate-200 tracking-tight flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            {title || 'Visual Analysis'}
          </h4>
          {chart.subtitle && (
            <p className="text-xs text-slate-400 mt-0.5">{chart.subtitle}</p>
          )}
        </div>

        {allowTypeToggle && (
          <div className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveType('bar')}
              className={`p-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1 ${
                activeType === 'bar' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Bar Chart"
            >
              <BarChart3 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setActiveType('line')}
              className={`p-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1 ${
                activeType === 'line' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Line Chart"
            >
              <LineIcon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setActiveType('area')}
              className={`p-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1 ${
                activeType === 'area' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Area Chart"
            >
              <Activity className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setActiveType('pie')}
              className={`p-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1 ${
                activeType === 'pie' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Donut / Pie Chart"
            >
              <PieIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Chart Canvas */}
      <div className="h-64 sm:h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {activeType === 'bar' ? (
            <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <defs>
                {COLORS.map((c, i) => (
                  <linearGradient key={`grad-${i}`} id={`barGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={c} stopOpacity={0.9} />
                    <stop offset="100%" stopColor={c} stopOpacity={0.3} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey={currentXAxis}
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                  color: '#f8fafc',
                }}
              />
              {currentSeries.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />}
              {currentSeries.map((sKey, idx) => (
                <Bar
                  key={sKey}
                  dataKey={sKey}
                  fill={`url(#barGrad-${idx % COLORS.length})`}
                  stroke={COLORS[idx % COLORS.length]}
                  radius={[6, 6, 0, 0]}
                />
              ))}
            </BarChart>
          ) : activeType === 'line' ? (
            <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey={currentXAxis}
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  color: '#f8fafc',
                }}
              />
              {currentSeries.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />}
              {currentSeries.map((sKey, idx) => (
                <Line
                  key={sKey}
                  type="monotone"
                  dataKey={sKey}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#090d16', stroke: COLORS[idx % COLORS.length], strokeWidth: 2 }}
                  activeDot={{ r: 7, fill: COLORS[idx % COLORS.length] }}
                />
              ))}
            </LineChart>
          ) : activeType === 'area' ? (
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <defs>
                {COLORS.map((c, i) => (
                  <linearGradient key={`areaGrad-${i}`} id={`areaGrad-${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={c} stopOpacity={0.6} />
                    <stop offset="100%" stopColor={c} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey={currentXAxis}
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  color: '#f8fafc',
                }}
              />
              {currentSeries.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />}
              {currentSeries.map((sKey, idx) => (
                <Area
                  key={sKey}
                  type="monotone"
                  dataKey={sKey}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2.5}
                  fill={`url(#areaGrad-${idx % COLORS.length})`}
                />
              ))}
            </AreaChart>
          ) : (
            <PieChart>
              <Pie
                data={data}
                dataKey={dataKey || currentYAxis}
                nameKey={nameKey || currentXAxis}
                cx="50%"
                cy="50%"
                outerRadius={88}
                innerRadius={45}
                paddingAngle={4}
                stroke="#090d16"
                strokeWidth={2}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={false}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  color: '#f8fafc',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
