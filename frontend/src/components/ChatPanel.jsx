import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Code, ChevronDown, ChevronUp, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import ChartRenderer from './ChartRenderer';

export default function ChatPanel({
  tableId,
  suggestedQuestions = [],
  messages = [],
  onSendMessage,
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
      <div className="px-6 py-4 border-b border-slate-800/80 bg-slate-950/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Conversational SQL Assistant</h3>
        </div>
        <span className="text-xs text-slate-400 font-mono">In-Memory DuckDB Engine</span>
      </div>

      {/* Suggested Questions Chips (at top of conversation) */}
      {suggestedQuestions && suggestedQuestions.length > 0 && messages.length === 0 && (
        <div className="p-6 bg-slate-950/30 border-b border-slate-800/60">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Suggested starter queries:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q, idx) => (
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
            <p className="text-sm">Ask any question in plain English about your dataset.</p>
            <p className="text-xs text-slate-600 mt-1">
              "What is the average profit by category?" or "Show top 5 sales"
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
                <p className="leading-relaxed text-slate-100">{msg.summary}</p>

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
                {msg.chart && msg.chart.type !== 'none' && (
                  <ChartRenderer chart={msg.chart} />
                )}

                {/* Results Table */}
                {msg.columns && msg.columns.length > 0 && msg.rows && (
                  <div className="mt-3">
                    <div className="text-[11px] text-slate-400 font-mono mb-1.5 flex items-center justify-between">
                      <span>Result Data ({msg.row_count} rows)</span>
                      {msg.retries > 0 && (
                        <span className="text-amber-400 text-[10px]">
                          Auto-corrected ({msg.retries} retries)
                        </span>
                      )}
                    </div>
                    <div className="overflow-x-auto rounded-xl border border-slate-800/90 max-h-64">
                      <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
                        <thead className="bg-slate-900 text-slate-300 sticky top-0">
                          <tr>
                            {msg.columns.map((col) => (
                              <th key={col} className="px-3 py-2 font-medium">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-slate-950/40 text-slate-300 font-mono">
                          {msg.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-slate-800/30">
                              {row.map((val, cIdx) => (
                                <td key={cIdx} className="px-3 py-1.5 whitespace-nowrap">
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
