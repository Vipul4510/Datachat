import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Code,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertCircle,
  Loader2,
  Download,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  RotateCcw,
  TrendingUp,
  Table
} from 'lucide-react';
import ChartRenderer from './ChartRenderer';

export default function ChatPanel({
  tableId,
  suggestedQuestions = [],
  messages = [],
  onSendMessage,
  onExport,
  onExportCleaned,
  onUndo,
  canUndo = false,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [expandedSqlIdxs, setExpandedSqlIdxs] = useState({});
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const q = input.trim();
    setInput('');
    onSendMessage(q);
  };

  const handleChipClick = (question) => {
    if (isLoading) return;
    onSendMessage(question);
  };

  const toggleSql = (idx) => {
    setExpandedSqlIdxs((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  return (
    <div className="w-full flex flex-col bg-slate-900/50 border border-slate-800 rounded-2xl backdrop-blur-md overflow-hidden flex-1 min-h-[500px]">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-slate-950/40 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Conversational Data & Cleaning Assistant</h3>
        </div>
        <div className="flex items-center gap-2">
          {onExport && (
            <button
              onClick={() => onExport('pdf')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-rose-600/30 to-pink-600/30 hover:from-rose-600/40 hover:to-pink-600/40 text-rose-300 text-xs font-semibold border border-rose-500/40 transition shadow-sm active:scale-95"
              title="Download conversation & quality report as PDF"
            >
              <FileText className="w-3.5 h-3.5 text-rose-400" />
              <span>Download PDF Report</span>
            </button>
          )}
          <span className="text-xs text-slate-400 font-mono hidden sm:inline">In-Memory DuckDB Engine</span>
        </div>
      </div>

      {/* Suggested Questions & Quick Action Chips */}
      {messages.length === 0 && (
        <div className="p-6 bg-slate-950/30 border-b border-slate-800/60">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Suggested starter queries & cleaning actions:
          </p>
          <div className="flex flex-wrap gap-2">
            {/* Quick cleaning chips */}
            <button
              onClick={() => handleChipClick('Auto clean the dataset to maximize data health score')}
              disabled={isLoading}
              className="text-xs text-left px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-950/70 to-blue-950/70 hover:from-cyan-900/70 hover:to-blue-900/70 text-cyan-300 border border-cyan-700/60 transition shadow-sm font-medium flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              ⚡ Auto-clean dataset
            </button>
            <button
              onClick={() => handleChipClick('Remove all duplicate rows')}
              disabled={isLoading}
              className="text-xs text-left px-3.5 py-2 rounded-xl bg-slate-800/70 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition shadow-sm"
            >
              🧹 Remove duplicates
            </button>
            <button
              onClick={() => handleChipClick('Fill missing values with column medians')}
              disabled={isLoading}
              className="text-xs text-left px-3.5 py-2 rounded-xl bg-slate-800/70 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition shadow-sm"
            >
              🩹 Fill missing values
            </button>

            {suggestedQuestions && suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleChipClick(q)}
                disabled={isLoading}
                className="text-xs text-left px-3.5 py-2 rounded-xl bg-slate-800/70 hover:bg-cyan-950/40 hover:text-cyan-300 hover:border-cyan-700/60 text-slate-300 border border-slate-700/60 transition shadow-sm"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-6">
        {messages.length === 0 && (
          <div className="h-48 flex flex-col items-center justify-center text-center text-slate-500">
            <Bot className="w-10 h-10 mb-2 text-slate-600" />
            <p className="text-sm">Ask any question or tell me how to clean your dataset.</p>
            <p className="text-xs text-slate-600 mt-1">
              "Clean all duplicates", "Impute missing values in Region", or "Show average sales by category"
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-3">
            {/* User message */}
            <div className="flex items-start gap-3 justify-end">
              <div className="max-w-xl bg-cyan-600/20 border border-cyan-500/30 text-cyan-100 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm shadow-sm">
                {msg.question}
              </div>
              <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center flex-shrink-0 text-xs font-bold border border-cyan-500/30">
                <User className="w-4 h-4" />
              </div>
            </div>

            {/* Assistant message */}
            <div className="flex items-start gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-slate-800 text-cyan-400 flex items-center justify-center flex-shrink-0 text-xs font-bold border border-slate-700">
                <Bot className="w-4 h-4" />
              </div>

              <div className="max-w-3xl w-full bg-slate-950/70 border border-slate-800/90 text-slate-200 rounded-2xl rounded-tl-sm p-4 text-sm shadow-md space-y-3">
                {/* Conversational summary answer */}
                <div className="leading-relaxed text-slate-100 whitespace-pre-line">
                  {msg.summary}
                </div>

                {/* If this is a data cleaning result, display rich action card */}
                {msg.is_cleaning && msg.cleaning_details && (
                  <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/40 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-900/40 pb-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="font-semibold text-xs text-emerald-300">
                          Data Health Transformation
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs font-bold">
                        <span className="text-slate-400">{msg.cleaning_details.initial_health_score}</span>
                        <span className="text-slate-500">➔</span>
                        <span className="text-emerald-400 text-sm">{msg.cleaning_details.final_health_score}/100</span>
                        {msg.cleaning_details.score_improvement > 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/60">
                            +{msg.cleaning_details.score_improvement} pts
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Dataset Rows</span>
                        <span className="font-semibold text-white">
                          {msg.cleaning_details.rows_before} ➔ {msg.cleaning_details.rows_after}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Duplicates Left</span>
                        <span className="font-semibold text-white">
                          {msg.cleaning_details.duplicate_rows_remaining}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Missing Cells Left</span>
                        <span className="font-semibold text-white">
                          {msg.cleaning_details.missing_cells_remaining}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">Outliers Left</span>
                        <span className="font-semibold text-white">
                          {msg.cleaning_details.outliers_remaining}
                        </span>
                      </div>
                    </div>

                    {/* Download Cleaned Data File Buttons */}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        onClick={() => onExportCleaned && onExportCleaned('xlsx')}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                        Download Cleaned Excel (.xlsx)
                      </button>
                      <button
                        onClick={() => onExportCleaned && onExportCleaned('csv')}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
                      >
                        <FileText className="w-3.5 h-3.5 text-cyan-400" />
                        Download Cleaned CSV
                      </button>
                      {canUndo && (
                        <button
                          onClick={() => onUndo && onUndo()}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/40 text-rose-300 text-xs font-medium border border-rose-800/60 transition ml-auto"
                        >
                          <RotateCcw className="w-3 h-3 text-rose-400" />
                          Undo Clean
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* View SQL Expander */}
                {msg.sql && (
                  <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/50">
                    <button
                      onClick={() => toggleSql(idx)}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs font-mono text-cyan-400 hover:bg-slate-800/60 transition"
                    >
                      <span className="flex items-center gap-1.5">
                        <Code className="w-3.5 h-3.5" />
                        View SQL Query
                      </span>
                      {expandedSqlIdxs[idx] ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>
                    {expandedSqlIdxs[idx] && (
                      <div className="p-3 bg-slate-950 font-mono text-xs text-slate-300 border-t border-slate-800 overflow-x-auto">
                        <pre>{msg.sql}</pre>
                      </div>
                    )}
                  </div>
                )}

                {/* Chart visualization */}
                {msg.chart && msg.chart.type && !['none', 'table'].includes(msg.chart.type) && (
                  <ChartRenderer chart={msg.chart} />
                )}

                {/* Results Table */}
                {msg.columns && msg.columns.length > 0 && msg.rows && msg.rows.length > 0 && (
                  <div className="mt-3 bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                    <div className="px-3.5 py-2.5 bg-slate-950/70 border-b border-slate-800/80 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <Table className="w-3.5 h-3.5 text-cyan-400" />
                        <span className="font-semibold text-slate-200">Tabular Results</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                          {msg.row_count || msg.rows.length} {((msg.row_count || msg.rows.length) === 1) ? 'row' : 'rows'}
                        </span>
                      </div>
                      {msg.retries > 0 && (
                        <span className="text-amber-400 text-[10px] font-mono">
                          Auto-corrected ({msg.retries} {msg.retries === 1 ? 'retry' : 'retries'})
                        </span>
                      )}
                    </div>
                    <div className="overflow-x-auto max-h-72">
                      <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
                        <thead className="bg-slate-900/90 text-slate-300 sticky top-0 backdrop-blur-sm z-10">
                          <tr>
                            {msg.columns.map((col) => (
                              <th key={col} className="px-3.5 py-2 font-medium tracking-wide text-slate-300">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-slate-950/30 text-slate-300 font-mono">
                          {msg.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-slate-800/40 transition">
                              {row.map((val, cIdx) => (
                                <td key={cIdx} className="px-3.5 py-2 whitespace-nowrap">
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
                  </div>
                )}

                {/* Error message if query failed */}
                {msg.error && (
                  <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 flex items-center gap-2 text-xs">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{msg.error}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator while LLM is generating */}
        {isLoading && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-800 text-cyan-400 flex items-center justify-center flex-shrink-0 border border-slate-700">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-950/60 border border-slate-800 rounded-2xl px-4 py-3 flex items-center gap-2 text-xs text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              <span>Translating question to DuckDB SQL & analyzing...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 bg-slate-950/70 border-t border-slate-800/80">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this data (e.g. 'Show total revenue by region')..."
            disabled={isLoading}
            className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-sm flex items-center gap-2 transition shadow-md shadow-cyan-950/40"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">Ask</span>
          </button>
        </form>
      </div>
    </div>
  );
}
