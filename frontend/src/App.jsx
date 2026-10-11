import React, { useState } from 'react';
import HeroScene from './components/HeroScene';
import FileUploader from './components/FileUploader';
import QualityDashboard from './components/QualityDashboard';
import ChatPanel from './components/ChatPanel';
import { api } from './api/client';
import { Database, Sparkles, RefreshCw, Eye, EyeOff } from 'lucide-react';

export default function App() {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [session, setSession] = useState(null); // { tableId, metadata, qualityReport, suggestedQuestions }
  const [chatMessages, setChatMessages] = useState([]);
  const [globalError, setGlobalError] = useState(null);

  // Handle file upload
  const handleUpload = async (file, sheetName) => {
    setIsUploading(true);
    setGlobalError(null);
    try {
      const data = await api.uploadFile(file, sheetName);
      setSession({
        tableId: data.table_id,
        metadata: data.metadata,
        qualityReport: data.quality_report,
        suggestedQuestions: data.suggested_questions,
      });
      setChatMessages([]);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed.';
      setGlobalError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle asking a question
  const handleSendMessage = async (question) => {
    if (!session?.tableId) return;
    setIsAnswering(true);
    setGlobalError(null);

    // Build chat history for conversational context
    const historyPayload = chatMessages.map((m) => ({
      role: 'user',
      content: m.question,
    }));

    try {
      const result = await api.askQuestion(session.tableId, question, historyPayload);
      const newEntry = {
        question,
        summary: result.summary,
        sql: result.sql,
        columns: result.columns,
        rows: result.rows,
        row_count: result.row_count,
        chart: result.chart,
        retries: result.retries,
        error: result.error,
      };
      setChatMessages((prev) => [...prev, newEntry]);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Error executing query.';
      setChatMessages((prev) => [
        ...prev,
        {
          question,
          summary: 'An error occurred while communicating with the assistant.',
          error: msg,
          sql: '',
        },
      ]);
    } finally {
      setIsAnswering(false);
    }
  };

  // Export report
  const handleExport = (format) => {
    if (!session?.tableId) return;
    const url = api.getReportUrl(session.tableId, format);
    window.open(url, '_blank');
  };

  // Reset to upload another file
  const handleReset = () => {
    setSession(null);
    setChatMessages([]);
    setGlobalError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-x-hidden">
      {/* Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={handleReset}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                DataChat
              </span>
              <span className="text-[10px] font-mono ml-2 px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                DuckDB Powered
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Reduce motion toggle */}
            <button
              onClick={() => setReduceMotion(!reduceMotion)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/50 transition"
              title="Toggle 3D animation motion"
            >
              {reduceMotion ? <EyeOff className="w-3.5 h-3.5 text-amber-400" /> : <Eye className="w-3.5 h-3.5 text-cyan-400" />}
              <span>{reduceMotion ? 'Reduced Motion' : '3D Motion Active'}</span>
            </button>

            {session && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>New Dataset</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 relative z-10 flex flex-col">
        {/* Landing Page State (no dataset uploaded yet) */}
        {!session ? (
          <div className="relative flex-1 flex flex-col justify-center items-center py-12 sm:py-20">
            {/* 3D Canvas Scene Behind Landing Upload */}
            <HeroScene reduceMotion={reduceMotion} />

            <div className="relative z-10 text-center max-w-3xl mx-auto mb-10">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/80 text-cyan-400 text-xs font-medium mb-6 backdrop-blur-md">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Zero Server Config • In-Process DuckDB • LLM Powered</span>
              </div>
              <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
                Conversational Data Analytics <br className="hidden sm:inline" />
                <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500 bg-clip-text text-transparent">
                  Directly on Your Files
                </span>
              </h1>
              <p className="mt-4 text-base sm:text-lg text-slate-400 max-w-2xl mx-auto">
                Upload your CSV, Excel, JSON or Parquet file. Get instantaneous data-quality profiling,
                then ask questions in plain English.
              </p>
            </div>

            {/* Upload Area */}
            <div className="relative z-10 w-full">
              <FileUploader onUploadComplete={handleUpload} isLoading={isUploading} />
            </div>

            {globalError && (
              <div className="relative z-10 mt-6 max-w-md mx-auto p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-sm text-center">
                {globalError}
              </div>
            )}
          </div>
        ) : (
          /* Active Analysis & Chat Workspace */
          <div className="flex flex-col flex-1">
            {/* Data Quality Report & Dashboard */}
            <QualityDashboard
              report={session.qualityReport}
              metadata={session.metadata}
              onExport={handleExport}
            />

            {/* Chat Panel */}
            <ChatPanel
              tableId={session.tableId}
              suggestedQuestions={session.suggestedQuestions}
              messages={chatMessages}
              onSendMessage={handleSendMessage}
              isLoading={isAnswering}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-4 text-center text-xs text-slate-500">
        DataChat • In-Process DuckDB Analytics • Primary: Groq (llama-3.3-70b-versatile) • Fallback: Gemini
      </footer>
    </div>
  );
}
