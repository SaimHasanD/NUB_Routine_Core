import React, { useState, useEffect, useRef } from 'react';
import { Search, ChevronDown, Calendar, BookOpen, FileText, Download, Image as ImageIcon } from 'lucide-react';
import RoutineTable from '../components/RoutineTable.jsx';
import RoutinePreviewModal from '../components/RoutinePreviewModal.jsx';
import RoutineDownloadLayout from '../components/RoutineDownloadLayout.jsx';
import { healthCheck, fetchGroups, fetchRoutine, getSourceFileUrl } from '../services/api.js';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { getCaptureScale, getPdfImageDimensions, waitForExportReady, downloadCanvasAsImage } from '../utils/exportSheet.js';
import ExamSchedule from './ExamSchedule.jsx';




export default function DashboardScreen() {
  const [viewMode, setViewMode] = useState('class'); // 'class' | 'exam'
  const [groups, setGroups] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [routine, setRoutine] = useState([]);
  const [title, setTitle] = useState('');
  const [season, setSeason] = useState('');
  const [oddDates, setOddDates] = useState([]);
  const [evenDates, setEvenDates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [serverWaking, setServerWaking] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [sourceFilename, setSourceFilename] = useState(null);
  const [sourceAvailable, setSourceAvailable] = useState(false);
  const dropdownRef = useRef(null);
  const printSheetRef = useRef(null);

  const getExportRoot = () =>
    printSheetRef.current?.querySelector('#routine-print-sheet') ?? null;

  const withExportCapture = async (captureFn) => {
    const host = printSheetRef.current;
    const element = getExportRoot();
    if (!host || !element) return null;

    host.style.position = 'fixed';
    host.style.left = '0';
    host.style.top = '0';
    host.style.zIndex = '99999';
    host.style.opacity = '1';
    host.style.visibility = 'visible';

    await new Promise((resolve) => requestAnimationFrame(resolve));

    try {
      await document.fonts.ready;
      return await captureFn(element);
    } finally {
      // Hardcode restoration to avoid race condition where 'saved' state gets corrupted
      host.style.position = '';
      host.style.left = '-10000px';
      host.style.top = '';
      host.style.zIndex = '';
      host.style.opacity = '';
      host.style.visibility = '';
    }
  };

  const captureExportCanvas = async (element) => {
    await waitForExportReady();
    return html2canvas(element, {
      scale: getCaptureScale(element.offsetWidth),
      backgroundColor: '#ffffff',
      useCORS: true,
      allowTaint: true,
      logging: false,
      onclone: (_doc, clonedRoot) => {
        clonedRoot.style.lineHeight = 'normal';
        clonedRoot.querySelectorAll('td, th').forEach((cell) => {
          cell.style.verticalAlign = 'middle';
        });
        clonedRoot.querySelectorAll('.routine-cell-inner').forEach((inner) => {
          inner.style.verticalAlign = 'middle';
        });
      },
    });
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const canvas = await withExportCapture(captureExportCanvas);
      if (!canvas) return;

      const imgData = canvas.toDataURL('image/png');
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const { x, y, w, h } = getPdfImageDimensions(doc, imgData);
      doc.addImage(imgData, 'PNG', x, y, w, h, undefined, 'NONE');
      doc.save(`NUB_ECSE_Routine_Section_${selectedGroup}.pdf`);
    } catch (err) {
      console.error("PDF generation failed:", err);
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadImage = async () => {
    setDownloading(true);
    try {
      const canvas = await withExportCapture(captureExportCanvas);
      if (!canvas) return;

      downloadCanvasAsImage(canvas, `NUB_ECSE_Routine_Section_${selectedGroup || 'Full'}.png`);
    } catch (err) {
      console.error("Image generation failed:", err);
    } finally {
      setDownloading(false);
    }
  };

  // Wake server + load groups on mount
  useEffect(() => {
    async function init() {
      setServerWaking(true);
      try {
        await healthCheck();
        const data = await fetchGroups();
        setGroups(data.groups || []);
        if (data.title) setTitle(data.title);
        if (data.season) setSeason(data.season);
        setSourceFilename(data.source_filename || null);
        setSourceAvailable(Boolean(data.source_available));
      } catch (err) {
        console.error("Init error", err);
        setGroups([]);
      } finally {
        setServerWaking(false);
      }
    }
    init();
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredGroups = groups.filter(g =>
    g.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleGenerateRoutine = async (group) => {
    const target = group || selectedGroup;
    if (!target) return;
    setLoading(true);
    setHasSearched(true);
    try {
      const data = await fetchRoutine(target);
      setRoutine(data.entries || []);
      if (data.odd_week_dates) setOddDates(data.odd_week_dates);
      if (data.even_week_dates) setEvenDates(data.even_week_dates);
      if (data.season) setSeason(data.season);
    } catch (err) {
      console.error("Fetch routine error", err);
      setRoutine([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 rounded-2xl p-6 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 opacity-10 transform translate-x-12 -translate-y-12">
          <Calendar className="w-64 h-64" />
        </div>
        <span className="text-xs bg-indigo-500/30 text-indigo-300 border border-indigo-500/20 px-3 py-1 rounded-full font-semibold tracking-wider uppercase">
          Department of ECSE
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight mt-3 text-slate-50">
          Northern University Bangladesh
        </h1>
        <p className="text-slate-300 text-sm mt-1 font-medium">
          {title || "Class Routine"}
        </p>

        {serverWaking && (
          <div className="mt-4 inline-flex items-center gap-2 bg-amber-500/20 border border-amber-400/30 text-amber-300 text-xs px-3 py-1.5 rounded-full">
            <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
            Waking server... (~30s on first load)
          </div>
        )}
      </div>

      {/* View Toggle */}
      <div className="flex flex-row gap-3">
        <button
          onClick={() => setViewMode('class')}
          className={`flex-1 px-5 py-3 rounded-xl font-semibold text-sm transition-all ${viewMode === 'class'
            ? 'bg-indigo-600 text-white shadow-sm'
            : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
            }`}
        >
          Class Routine
        </button>
        <button
          onClick={() => setViewMode('exam')}
          className={`flex-1 px-5 py-3 rounded-xl font-semibold text-sm transition-all ${viewMode === 'exam'
            ? 'bg-violet-600 text-white shadow-sm'
            : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
            }`}
        >
          Exam Routine
        </button>
      </div>

      {viewMode === 'exam' && <ExamSchedule />}

      {viewMode === 'class' && (
        <>
          {/* Group Selector */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <div className="flex flex-col sm:flex-row gap-4 items-start">

              {/* Left half: section dropdown */}
              <div className="flex-1 w-full relative" ref={dropdownRef}>
                <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                  Filter by Semester
                </label>
                <div
                  onClick={() => setIsOpen(!isOpen)}
                  className="w-full bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl flex justify-between items-center cursor-pointer hover:border-slate-300 transition-colors"
                >
                  <span className={selectedGroup ? "text-slate-900 font-medium" : "text-slate-400"}>
                    {loading ? 'Loading...' : selectedGroup ? `Section ${selectedGroup}` : "Choose a section — loads instantly"}
                  </span>
                  <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                </div>
                {isOpen && (
                  <div className="absolute w-full mt-2 bg-white border border-slate-200 rounded-xl shadow-xl z-30 max-h-60 overflow-hidden flex flex-col">
                    <div className="p-2 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
                      <Search className="w-4 h-4 text-slate-400 ml-2 flex-shrink-0" />
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Filter sections..."
                        className="w-full bg-transparent px-2 py-1.5 text-sm outline-none text-slate-800"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="overflow-y-auto max-h-48 divide-y divide-slate-50">
                      {filteredGroups.length > 0 ? (
                        filteredGroups.map((group) => (
                          <div
                            key={group}
                            onClick={() => {
                              setSelectedGroup(group);
                              setIsOpen(false);
                              setSearchTerm('');
                              handleGenerateRoutine(group);
                            }}
                            className="px-4 py-2.5 text-sm hover:bg-indigo-50 text-slate-700 font-medium cursor-pointer transition-colors"
                          >
                            Section {group}
                          </div>
                        ))
                      ) : (
                        <div className="p-4 text-xs text-center text-slate-400">No matching sections found</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Right half: source file */}
              {sourceFilename && sourceAvailable && (
                <div className="flex-1 w-full">
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                    Source File
                  </label>
                  <a
                    href={getSourceFileUrl()}
                    download={sourceFilename}
                    onClick={(e) => {
                      if (!window.confirm(`Download "${sourceFilename}"?`)) {
                        e.preventDefault();
                      }
                    }}
                    className="w-full bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl flex justify-between items-center hover:border-slate-300 hover:bg-slate-100 transition-colors"
                  >
                    <span className="text-slate-700 font-medium text-sm truncate">{sourceFilename}</span>
                    <Download className="w-4 h-4 text-slate-400 flex-shrink-0 ml-2" />
                  </a>
                </div>
              )}

            </div>
          </div>

          {/* Routine Output */}
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
              <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-500 font-medium text-sm">
                Parsing schedule for Section {selectedGroup}...
              </p>
            </div>
          ) : hasSearched && routine.length > 0 ? (
            <div className="space-y-6">
              {/* Actions Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">
                    Routine Loaded Successfully
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDownloadPdf}
                    disabled={downloading}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-semibold text-sm px-4 py-2 rounded-xl transition-all shadow-sm active:scale-95"
                  >
                    <FileText className="w-4 h-4" />
                    {downloading ? "Compiling..." : "Download PDF"}
                  </button>
                  <button
                    onClick={handleDownloadImage}
                    disabled={downloading}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-semibold text-sm px-4 py-2 rounded-xl transition-all shadow-sm active:scale-95"
                  >
                    <Download className="w-4 h-4" />
                    {downloading ? "Compiling..." : "Download Image"}
                  </button>

                  <div className="h-6 w-px bg-slate-200 mx-1" />

                  <button
                    onClick={() => setPreviewOpen(true)}
                    title="Print Preview Layout"
                    className="flex items-center justify-center bg-slate-100 hover:bg-slate-200 text-slate-700 p-2.5 rounded-xl border border-slate-200/60 transition-all active:scale-95"
                  >
                    <ImageIcon className="w-4.5 h-4.5" />
                  </button>
                </div>
              </div>

              <RoutineTable routine={routine} selectedGroup={selectedGroup} />

              {/* Hidden layout for direct DOM capturing */}
              <div
                ref={printSheetRef}
                className="absolute top-0 pointer-events-none"
                style={{ left: '-10000px' }}
              >
                <RoutineDownloadLayout
                  forExport
                  routine={routine}
                  selectedGroup={selectedGroup}
                  title={title}
                  season={season}
                  oddDates={oddDates}
                  evenDates={evenDates}
                />
              </div>

              {/* Sessional/Print Layout Preview Modal */}
              <RoutinePreviewModal
                isOpen={previewOpen}
                onClose={() => setPreviewOpen(false)}
                routine={routine}
                selectedGroup={selectedGroup}
                title={title}
                season={season}
                oddDates={oddDates}
                evenDates={evenDates}
                onDownloadPdf={handleDownloadPdf}
                onDownloadImage={handleDownloadImage}
              />
            </div>
          ) : hasSearched ? (
            <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl">
              <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 font-medium">
                No routine available for this section yet.
              </p>
            </div>
          ) : (
            <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-2xl bg-white/50">
              <p className="text-slate-400 text-sm font-medium">
                Select your section above to load your class schedule.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
