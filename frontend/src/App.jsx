import React, { useState } from 'react';
import HeroScene from './components/HeroScene';
import FileUploader from './components/FileUploader';
import QualityDashboard from './components/QualityDashboard';
import ChatPanel from './components/ChatPanel';
import VisualStudio from './components/VisualStudio';
import PrivacyVault from './components/PrivacyVault';
import ContributorHub from './components/ContributorHub';
import { api } from './api/client';
import {
  Database,
  Sparkles,
  RefreshCw,
  Eye,
  EyeOff,
  BarChart3,
  MessageSquare,
  ShieldCheck,
  Activity,
  GitPullRequest,
  Lock,
  Layers,
  HardDrive,
  FileText,
  FileSpreadsheet,
  Download,
  Loader2
} from 'lucide-react';

export default function App() {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [session, setSession] = useState(null); // { tableId, metadata, qualityReport, suggestedQuestions }
  const [chatMessages, setChatMessages] = useState([]);
  const [globalError, setGlobalError] = useState(null);
  const [activeTab, setActiveTab] = useState('visual_studio');
  const [showLandingContributor, setShowLandingContributor] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState(null);

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
      setCanUndo(false);
      setActiveTab('visual_studio');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed.';
      setGlobalError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle loading pre-bundled sample dataset
  const handleSelectSample = async (filename) => {
    setIsUploading(true);
    setGlobalError(null);
    try {
      const data = await api.loadSample(filename);
      setSession({
        tableId: data.table_id,
        metadata: data.metadata,
        qualityReport: data.quality_report,
        suggestedQuestions: data.suggested_questions,
      });
      setChatMessages([]);
      setCanUndo(false);
      setActiveTab('visual_studio');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load sample dataset.';
      setGlobalError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle asking a question or conversational cleaning request
  const handleSendMessage = async (question) => {
    if (!session?.tableId) return;
    setIsAnswering(true);
    setGlobalError(null);

    const historyPayload = chatMessages.map((m) => ({
      role: 'user',
      content: m.question,
    }));

    try {
      const result = await api.askQuestion(session.tableId, question, historyPayload);

      if (result.is_cleaning && result.quality_report) {
        setSession((prev) => ({
          ...prev,
          qualityReport: result.quality_report,
          metadata: result.metadata || prev.metadata,
        }));
        setCanUndo(Boolean(result.cleaning_details?.can_undo));
      }

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
        is_cleaning: result.is_cleaning,
        cleaning_details: result.cleaning_details,
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

  // Handle direct data cleaning action
  const handleClean = async (action, params = null) => {
    if (!session?.tableId) return;
    setIsCleaning(true);
    setGlobalError(null);
    try {
      const result = await api.cleanData(session.tableId, action, params);
      setSession((prev) => ({
        ...prev,
        qualityReport: result.quality_report,
        metadata: result.metadata || prev.metadata,
      }));
      setCanUndo(Boolean(result.cleaning_details?.can_undo));

      const cleanEntry = {
        question: `Clean data (${action.replace('_', ' ')})`,
        summary: result.summary,
        sql: `-- Applied data cleaning: ${action}`,
        is_cleaning: true,
        cleaning_details: result.cleaning_details,
      };
      setChatMessages((prev) => [...prev, cleanEntry]);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Data cleaning failed.';
      setGlobalError(msg);
    } finally {
      setIsCleaning(false);
    }
  };

  // Handle undo cleaning
  const handleUndo = async () => {
    if (!session?.tableId) return;
    setIsCleaning(true);
    setGlobalError(null);
    try {
      const result = await api.undoClean(session.tableId);
      setSession((prev) => ({
        ...prev,
        qualityReport: result.quality_report,
        metadata: result.metadata || prev.metadata,
      }));
      setCanUndo(Boolean(result.can_undo));

      const undoEntry = {
        question: 'Undo previous data cleaning',
        summary: `↩️ ${result.message}\nData health score restored to ${result.quality_report.health_score}/100.`,
        sql: '-- Reverted to previous snapshot',
      };
      setChatMessages((prev) => [...prev, undoEntry]);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Undo operation failed.';
      setGlobalError(msg);
    } finally {
      setIsCleaning(false);
    }
  };

  // Export report (PDF or Excel)
  const handleExport = (format = 'pdf') => {
    if (!session?.tableId) return;
    setDownloadingFormat(format);
    try {
      const url = api.getReportUrl(session.tableId, format);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `datachat_report_${session.metadata?.original_filename || 'dataset'}.${format}`);
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setTimeout(() => setDownloadingFormat(null), 1500);
    }
  };

  // Export cleaned dataset
  const handleExportCleaned = (format = 'xlsx') => {
    if (!session?.tableId) return;
    const url = api.getCleanedDataUrl(session.tableId, format);
    window.open(url, '_blank');
  };

  // Reset to landing page
  const handleReset = () => {
    setSession(null);
    setChatMessages([]);
    setCanUndo(false);
    setGlobalError(null);
    setActiveTab('visual_studio');
    setShowLandingContributor(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-x-hidden selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={handleReset}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  DataChat Lab
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Open Source
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-medium">
                Local-First In-Memory DuckDB Engine
              </div>
            </div>
          </div>

          {/* Right Header Badges & Actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Zero-Leak Privacy Pill Badge */}
            <div
              onClick={() => {
                if (session) setActiveTab('privacy');
              }}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 text-xs font-medium cursor-pointer hover:bg-emerald-950/70 transition"
              title="Your proprietary data is never transmitted to cloud LLMs."
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Zero Raw Data Egress</span>
            </div>

            {/* Contributor Guide Toggle (Landing Page) */}
            {!session && (
              <button
                onClick={() => setShowLandingContributor(!showLandingContributor)}
                className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                  showLandingContributor
                    ? 'bg-blue-600 text-white border-blue-500'
                    : 'bg-slate-900/60 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                }`}
              >
                <GitPullRequest className="w-3.5 h-3.5 text-blue-400" />
                <span className="hidden sm:inline">Contribute</span>
              </button>
            )}

            {/* Reduce motion toggle */}
            <button
              onClick={() => setReduceMotion(!reduceMotion)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-900/50 transition"
              title="Toggle 3D animation motion"
            >
              {reduceMotion ? <EyeOff className="w-3.5 h-3.5 text-amber-400" /> : <Eye className="w-3.5 h-3.5 text-cyan-400" />}
              <span className="hidden sm:inline">{reduceMotion ? 'Reduced Motion' : '3D Active'}</span>
            </button>

            {session && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-xs font-semibold text-white px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-md shadow-cyan-600/20 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>New Dataset</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 relative z-10 flex flex-col">
        {/* Landing Page State */}
        {!session ? (
          showLandingContributor ? (
            <div className="space-y-6 py-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setShowLandingContributor(false)}
                  className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
                >
                  &larr; Back to Dataset Ingestion
                </button>
              </div>
              <ContributorHub />
            </div>
          ) : (
            <div className="relative flex-1 flex flex-col justify-center items-center py-8 sm:py-16">
              {/* 3D Canvas Scene Behind Landing Upload */}
              <HeroScene reduceMotion={reduceMotion} />

              <div className="relative z-10 text-center max-w-3xl mx-auto mb-8 sm:mb-10">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/70 border border-cyan-800/80 text-cyan-400 text-xs font-semibold mb-6 backdrop-blur-md shadow-lg shadow-cyan-950/30">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Open Source Lab • In-Process DuckDB • Verifiable Zero-Data Egress</span>
                </div>

                <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
                  Private Data Intelligence <br className="hidden sm:inline" />
                  <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500 bg-clip-text text-transparent">
                    Without Cloud Data Ingestion
                  </span>
                </h1>

                <p className="mt-4 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
                  Your raw data stays in local RAM. The AI translates questions to vectorized DuckDB SQL using only column headers. Instant charts, graphs, and profiling with zero privacy compromise.
                </p>
              </div>

              {/* Upload Area & 1-Click Samples */}
              <div className="relative z-10 w-full mb-12">
                <FileUploader
                  onUploadComplete={handleUpload}
                  onSelectSample={handleSelectSample}
                  isLoading={isUploading}
                />
              </div>

              {globalError && (
                <div className="relative z-10 mt-6 max-w-md mx-auto p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-rose-300 text-sm text-center">
                  {globalError}
                </div>
              )}

              {/* Unique Value Propositions Grid */}
              <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl mt-4">
                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm shadow-md">
                  <div className="p-2.5 w-fit rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-3">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white">Your Data Stays With You</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    0 records sent to AI servers. DuckDB runs embedded in-memory (:memory:) on your local CPU.
                  </p>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm shadow-md">
                  <div className="p-2.5 w-fit rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-3">
                    <BarChart3 className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white">Instant Visual Analytics</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Auto-synthesizes distributions, breakdown charts, and trends. Interactive custom chart builder.
                  </p>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm shadow-md">
                  <div className="p-2.5 w-fit rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-3">
                    <GitPullRequest className="w-5 h-5" />
                  </div>
                  <h3 className="text-sm font-bold text-white">Open Source & Extensible</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    Modular research codebase. Easily plug in Ollama, ClickHouse, SQLite, or custom cleaning recipes.
                  </p>
                </div>
              </div>
            </div>
          )
        ) : (
          /* Active Analysis & Workspace with Tab Navigation */
          <div className="flex flex-col flex-1 space-y-6">
            {/* Active Table Quick Bar */}
            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-400">
                  <HardDrive className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-slate-400 font-mono">Active In-Process Dataset</div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    <span>{session.metadata?.original_filename || 'Uploaded Dataset'}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                      {session.metadata?.format?.toUpperCase() || 'TABLE'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dataset Quick Stats & Direct Report Downloader */}
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                <div className="hidden sm:block">
                  <span className="text-slate-500">Rows:</span>{' '}
                  <strong className="text-slate-200">{session.metadata?.row_count?.toLocaleString()}</strong>
                </div>
                <div className="hidden sm:block">
                  <span className="text-slate-500">Columns:</span>{' '}
                  <strong className="text-slate-200">{session.metadata?.column_count}</strong>
                </div>
                <div className="hidden sm:block">
                  <span className="text-slate-500">Health:</span>{' '}
                  <strong className="text-emerald-400">{session.qualityReport?.health_score}/100</strong>
                </div>

                {/* Direct PDF & Excel Downloader */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleExport('pdf')}
                    disabled={downloadingFormat === 'pdf'}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white text-xs font-semibold shadow-md shadow-rose-600/20 transition active:scale-95 disabled:opacity-60"
                    title="Download complete executive PDF analytics report"
                  >
                    {downloadingFormat === 'pdf' ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileText className="w-3.5 h-3.5" />
                    )}
                    <span>{downloadingFormat === 'pdf' ? 'Generating PDF...' : 'Download PDF Report'}</span>
                  </button>

                  <button
                    onClick={() => handleExport('xlsx')}
                    disabled={downloadingFormat === 'xlsx'}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition disabled:opacity-60"
                    title="Download Excel workbook"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Excel</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-2xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-md">
              <button
                onClick={() => setActiveTab('visual_studio')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'visual_studio'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                <span>Visual Studio (Charts & Graphs)</span>
              </button>

              <button
                onClick={() => setActiveTab('chat')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'chat'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Conversational Copilot</span>
              </button>

              <button
                onClick={() => setActiveTab('privacy')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'privacy'
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Data Privacy & Storage Vault</span>
              </button>

              <button
                onClick={() => setActiveTab('quality')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'quality'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span>Data Quality & Cleaner Lab</span>
              </button>

              <button
                onClick={() => setActiveTab('contribute')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition ${
                  activeTab === 'contribute'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <GitPullRequest className="w-4 h-4 text-blue-400" />
                <span>Open Source Contributor Hub</span>
              </button>
            </div>

            {/* Tab Panels */}
            {activeTab === 'visual_studio' && (
              <VisualStudio tableId={session.tableId} metadata={session.metadata} onExport={handleExport} />
            )}

            {activeTab === 'chat' && (
              <ChatPanel
                tableId={session.tableId}
                suggestedQuestions={session.suggestedQuestions}
                messages={chatMessages}
                onSendMessage={handleSendMessage}
                onExport={handleExport}
                onExportCleaned={handleExportCleaned}
                onUndo={handleUndo}
                canUndo={canUndo}
                isLoading={isAnswering || isCleaning}
              />
            )}

            {activeTab === 'privacy' && (
              <PrivacyVault tableId={session.tableId} metadata={session.metadata} />
            )}

            {activeTab === 'quality' && (
              <QualityDashboard
                report={session.qualityReport}
                metadata={session.metadata}
                onExport={handleExport}
                onExportCleaned={handleExportCleaned}
                onClean={handleClean}
                onUndo={handleUndo}
                canUndo={canUndo}
                isCleaning={isCleaning}
              />
            )}

            {activeTab === 'contribute' && <ContributorHub />}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-5 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Zero-Data-Egress In-Memory DuckDB Engine</span>
          </div>
          <div className="text-slate-400">
            Open Source Lab Project • Contributions Welcome via Pull Requests
          </div>
          <div className="font-mono text-slate-500">
            Primary: Groq (Llama-3.3-70b) • Fallback: Gemini
          </div>
        </div>
      </footer>
    </div>
  );
}
