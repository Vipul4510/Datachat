import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  TrendingUp,
  GraduationCap,
  Receipt,
  Zap
} from 'lucide-react';

const SUPPORTED_FORMATS = ['.csv', '.tsv', '.xlsx', '.xls', '.json', '.parquet'];

const SAMPLE_DATASETS = [
  {
    filename: 'sales_data.csv',
    title: 'E-Commerce Sales',
    subtitle: 'Revenue, profit, categories, & region',
    format: 'CSV',
    icon: TrendingUp,
    badgeColor: 'border-cyan-500/40 text-cyan-400 bg-cyan-950/40'
  },
  {
    filename: 'student_marks.xlsx',
    title: 'Academic Performance',
    subtitle: 'Exam scores, grades, & pass status',
    format: 'Excel',
    icon: GraduationCap,
    badgeColor: 'border-blue-500/40 text-blue-400 bg-blue-950/40'
  },
  {
    filename: 'expenses.json',
    title: 'Corporate Spend',
    subtitle: 'Department tech invoices & status',
    format: 'JSON',
    icon: Receipt,
    badgeColor: 'border-purple-500/40 text-purple-400 bg-purple-950/40'
  },
  {
    filename: 'sales_data.parquet',
    title: 'Vectorized Parquet',
    subtitle: 'High-speed columnar binary storage',
    format: 'Parquet',
    icon: Zap,
    badgeColor: 'border-emerald-500/40 text-emerald-400 bg-emerald-950/40'
  }
];

export default function FileUploader({ onUploadComplete, onSelectSample, isLoading }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [sheetName, setSheetName] = useState('');
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSelect = (file) => {
    setError(null);
    if (!file) return;

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!SUPPORTED_FORMATS.includes(ext)) {
      setError(`Format '${ext}' not supported. Supported: CSV, TSV, Excel, JSON, Parquet.`);
      return;
    }

    if (file.size > 200 * 1024 * 1024) {
      setError('File exceeds 200 MB maximum size limit.');
      return;
    }

    if (file.size === 0) {
      setError('File is empty (0 bytes).');
      return;
    }

    setSelectedFile(file);
    onUploadComplete(file, sheetName || null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSelect(e.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      {/* Drag & Drop Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-3xl p-8 sm:p-12 transition-all cursor-pointer backdrop-blur-md text-center shadow-xl ${
          dragActive
            ? 'border-cyan-400 bg-cyan-950/30 scale-[1.01]'
            : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900/80'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.xlsx,.xls,.json,.parquet"
          className="hidden"
          onChange={handleChange}
          disabled={isLoading}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="p-4 rounded-2xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-500/10">
            {isLoading ? (
              <Loader2 className="w-9 h-9 animate-spin text-cyan-400" />
            ) : (
              <UploadCloud className="w-9 h-9" />
            )}
          </div>

          <div>
            <h3 className="text-xl font-bold text-white tracking-tight">
              {isLoading ? 'Loading & Vectorizing Dataset...' : 'Drop your dataset here or browse'}
            </h3>
            <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
              Auto-ingests CSV, TSV, Excel, JSON, and Parquet directly into local in-process DuckDB RAM.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            {['CSV', 'TSV', 'Excel (.xlsx)', 'JSON', 'Parquet'].map((tag) => (
              <span
                key={tag}
                className="text-xs font-mono px-3 py-1 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/60"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800/80 text-rose-300 flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 1-Click Lab Sample Datasets */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Try a Pre-Bundled Open Source Lab Dataset (1-Click)
            </h4>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">Instant DuckDB Demo</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SAMPLE_DATASETS.map((sample) => {
            const Icon = sample.icon;
            return (
              <button
                key={sample.filename}
                disabled={isLoading}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectSample && onSelectSample(sample.filename);
                }}
                className="group p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-900/90 text-left transition shadow-md backdrop-blur-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-2 rounded-xl bg-slate-800 text-slate-300 group-hover:text-cyan-400 transition">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${sample.badgeColor}`}>
                      {sample.format}
                    </span>
                  </div>
                  <div className="text-xs font-bold text-white group-hover:text-cyan-300 transition">
                    {sample.title}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                    {sample.subtitle}
                  </div>
                </div>

                <div className="text-[10px] text-cyan-400 font-semibold mt-3 flex items-center gap-1 group-hover:translate-x-0.5 transition">
                  <span>Load Dataset</span> &rarr;
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
