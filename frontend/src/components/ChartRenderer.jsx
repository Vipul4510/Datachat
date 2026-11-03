import React from 'react';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'];

export default function ChartRenderer({ chart }) {
  if (!chart || chart.type === 'none' || chart.type === 'table') return null;
  if (!['bar', 'line', 'pie', 'metric'].includes(chart.type)) return null;

  if (chart.type === 'metric') {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 my-3 inline-block">
        <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">
          {chart.title}
        </div>
        <div className="text-3xl font-bold text-cyan-400 mt-1">
          {typeof chart.value === 'number' ? chart.value.toLocaleString() : String(chart.value)}
          {chart.unit && <span className="text-sm font-normal text-slate-400 ml-1">{chart.unit}</span>}
        </div>
      </div>
    );
  }

  const { type, data, xAxis, yAxis, series, nameKey, dataKey, title } = chart;
  if (!data || data.length === 0) return null;

  return (
    <div className="w-full bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 my-3 backdrop-blur-sm">
      <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center justify-between">
        <span>{title || 'Visual Analysis'}</span>
        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-cyan-400 font-mono">
          {type.toUpperCase()}
        </span>
      </div>

      <div className="h-64 sm:h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {type === 'bar' && (
            <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey={xAxis}
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  color: '#f8fafc',
                }}
              />
              {series && series.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />}
              {(series || [yAxis]).map((sKey, idx) => (
                <Bar
                  key={sKey}
                  dataKey={sKey}
                  fill={COLORS[idx % COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          )}

          {type === 'line' && (
            <LineChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey={xAxis}
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  color: '#f8fafc',
                }}
              />
              {series && series.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />}
              {(series || [yAxis]).map((sKey, idx) => (
                <Line
                  key={sKey}
                  type="monotone"
                  dataKey={sKey}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: COLORS[idx % COLORS.length] }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          )}

          {type === 'pie' && (
            <PieChart>
              <Pie
                data={data}
                dataKey={dataKey}
                nameKey={nameKey}
                cx="50%"
                cy="50%"
                outerRadius={85}
                innerRadius={35}
                paddingAngle={4}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={false}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
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
