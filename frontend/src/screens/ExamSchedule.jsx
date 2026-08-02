import React, { useState, useEffect, useRef } from 'react';
import { Calendar, FileText, Download, AlertCircle, ClipboardList, Image as ImageIcon, X } from 'lucide-react';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { getExamSchedule } from '../services/api.js';
import { getPdfImageDimensions, downloadCanvasAsImage } from '../utils/exportSheet.js';

// ── helpers ──────────────────────────────────────────────────────────────────

/** All unique semester numbers present in the full schedule */
function allSemesters(scheduleArray) {
  const nums = new Set();
  const arr = Array.isArray(scheduleArray) ? scheduleArray : [];
  arr.forEach((row) => {
    const courses = Array.isArray(row.courses) ? row.courses : [];
    courses.forEach((c) => {
      if (c && typeof c === 'object' && c.semester) nums.add(c.semester);
    });
  });
  return [...nums].sort((a, b) => Number(a) - Number(b));
}

/** Filter a course list to only entries matching the selected semester */
function filterCourses(courses, sem) {
  const arr = Array.isArray(courses) ? courses : [];
  if (!sem) return arr;
  return arr.filter((c) => c && typeof c === 'object' && String(c.semester) === String(sem));
}

// ── component ─────────────────────────────────────────────────────────────────

export default function ExamSchedule() {
  const [data, setData] = useState({ image_url: null, schedule: [] })
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedSem, setSelectedSem] = useState('');   // '' = All
  const [downloading, setDownloading] = useState(false);
  const [showImage, setShowImage] = useState(false);
  const tableRef = useRef(null);

  // ── fetch on mount ─────────────────────────────────────────────────────────
  useEffect(() => {
    getExamSchedule()
      .then((d) => { if (d) setData(d); })
      .catch((err) => setError(err.message || 'Failed to load exam schedule.'))
      .finally(() => setLoading(false));
  }, []);

  // ── derived data ───────────────────────────────────────────────────────────
  // Support both new wrapped format { image_url, schedule } and old flat array format [...]
  const scheduleArray = Array.isArray(data?.schedule)
    ? data.schedule
    : Array.isArray(data)
      ? data
      : [];

  const semesters = data ? allSemesters(scheduleArray) : [];

  /** Rows visible after semester filter */
  const visibleRows = scheduleArray.map((row) => ({
    ...row,
    courses: filterCourses(row.courses, selectedSem)
  })).filter((row) => !selectedSem || row.courses.length > 0);

  const today = new Date().toISOString().slice(0, 10);
  const semSlug = 'exam-schedule';
  const filenameBase = `${semSlug}-${today}`;

  // ── capture helpers ────────────────────────────────────────────────────────
  const captureCanvas = async () => {
    if (!tableRef.current) return null;
    await document.fonts.ready;
    return html2canvas(tableRef.current, {
      scale: 2,
      backgroundColor: '#ffffff',
      useCORS: true,
      logging: false,
    });
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const canvas = await captureCanvas();
      if (!canvas) return;
      const imgData = canvas.toDataURL('image/png');
      const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const { x, y, w, h } = getPdfImageDimensions(doc, imgData, 10);
      doc.addImage(imgData, 'PNG', x, y, w, h, undefined, 'NONE');
      doc.save(`${filenameBase}.pdf`);
    } catch (err) {
      console.error('PDF generation failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadImage = async () => {
    setDownloading(true);
    try {
      const canvas = await captureCanvas();
      if (!canvas) return;
      downloadCanvasAsImage(canvas, `${filenameBase}.png`);
    } catch (err) {
      console.error('Image generation failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  // ── render states ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 space-y-4">
        <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-500 font-medium text-sm">Loading exam schedule…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-32 space-y-4 text-center">
        <AlertCircle className="w-14 h-14 text-slate-300" />
        <p className="text-slate-600 font-semibold text-lg">No exam schedule uploaded yet.</p>
        <p className="text-slate-400 text-sm max-w-xs">
          Ask your admin to upload the exam schedule from the Admin Panel.
        </p>
      </div>
    );
  }

  // ── main render ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 relative">
      {/* ── Image Modal ────────────────────────────────────────────────── */}
      {showImage && data.image_url && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-violet-600" />
                Original Uploaded Image
              </h3>
              <button
                onClick={() => setShowImage(false)}
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-auto flex-1 bg-slate-200/50 flex justify-center">
              <img
                src={data.image_url}
                alt="Exam Schedule"
                className="max-w-full h-auto rounded-lg shadow-sm border border-slate-200 object-contain"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Semester Filter ──────────────────────────────────────────────── */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div className="flex flex-col sm:flex-row gap-4 items-start">

          {/* Left half: semester dropdown */}
          <div className="flex-1 w-full">
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Filter by Semester
            </label>
            <select
              value={selectedSem}
              onChange={(e) => setSelectedSem(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl text-slate-800 font-medium cursor-pointer hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-violet-400 transition-colors"
            >
              <option value="">All Semesters</option>
              {semesters.map((s) => (
                <option key={s} value={s}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>

          {/* Right half: source file */}
          {data.image_url && (
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                Source File
              </label>
              <button
                onClick={async () => {
                  const res = await fetch(data.image_url);
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'exam_schedule_image.jpeg';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="w-full bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl flex justify-between items-center hover:border-slate-300 hover:bg-slate-100 transition-colors"
              >
                <span className="text-slate-700 font-medium text-sm truncate">exam_schedule_image.jpeg</span>
                <Download className="w-4 h-4 text-slate-400 flex-shrink-0 ml-2" />
              </button>
            </div>
          )}

        </div>
      </div>

      {/* ── Download Toolbar ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">
            Exam Schedule Loaded
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadPdf}
            disabled={downloading}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-semibold text-sm px-4 py-2 rounded-xl transition-all shadow-sm active:scale-95 whitespace-nowrap"
          >
            <FileText className="w-4 h-4" />
            {downloading ? 'Compiling…' : 'Download PDF'}
          </button>
          <button
            onClick={handleDownloadImage}
            disabled={downloading}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-semibold text-sm px-4 py-2 rounded-xl transition-all shadow-sm active:scale-95 whitespace-nowrap"
          >
            <Download className="w-4 h-4" />
            {downloading ? 'Compiling…' : 'Download Image'}
          </button>
        </div>
      </div>

      {/* ── Routine-like Grid View ──────────────────────────────────────── */}
      <div
        ref={tableRef}
        className="space-y-6"
      >
        {visibleRows.length === 0 ? (
          <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl">
            <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-slate-900 font-semibold mb-1">No Exam Slots</h3>
            <p className="text-slate-500 text-sm">No exam slots match the selected semester.</p>
          </div>
        ) : (
          Object.entries(
            visibleRows.reduce((acc, row) => {
              const key = `${row.date} - ${row.day}`;
              if (!acc[key]) acc[key] = [];
              acc[key].push(row);
              return acc;
            }, {})
          ).map(([dateDay, slots], idx) => (
            <div
              key={idx}
              className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col md:flex-row"
            >
              {/* Day Strip */}
              <div className="md:w-48 bg-slate-900 text-white px-6 py-4 flex md:flex-col justify-between md:justify-center items-center md:items-start gap-1 flex-shrink-0">
                <span className="font-bold text-[15px] tracking-wide leading-tight">{dateDay.split(' - ')[0]}</span>
                <span className="font-medium text-indigo-300 text-sm">{dateDay.split(' - ')[1]}</span>
                <span className="text-xs text-slate-400 font-medium mt-1">
                  {slots.length} slot{slots.length > 1 ? 's' : ''}
                </span>
              </div>

              {/* Slots Grid */}
              <div className="p-4 flex-1 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4 bg-slate-50/50">
                {slots.map((row, sIdx) => (
                  <div
                    key={sIdx}
                    className="bg-white border border-slate-200/80 p-4 rounded-xl shadow-sm hover:border-violet-300 transition-colors flex flex-col"
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-violet-700 mb-3 bg-violet-50 px-2 py-1 rounded-md w-fit border border-violet-100">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{row.slot}</span>
                    </div>

                    <div className="flex-1">
                      {row.courses.length === 0 ? (
                        <p className="text-slate-400 text-sm italic py-2">No courses scheduled</p>
                      ) : (
                        <div className="flex flex-col gap-2">
                          {row.courses.map((c, ci) => {
                            const isObj = typeof c === 'object' && c !== null;
                            const code = isObj
                              ? (typeof c.code === 'object' && c.code !== null ? c.code.code : c.code)
                              : String(c);
                            const sem = isObj ? c.semester : null;

                            return (
                              <div
                                key={ci}
                                className="flex items-start justify-between border-b border-slate-100 last:border-0 pb-2 last:pb-0 gap-2"
                              >
                                <span className="font-bold text-slate-800 text-sm">{code}</span>
                                {sem && (
                                  <span className="text-[10px] uppercase bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-bold tracking-wide flex-shrink-0">
                                    Sem {sem}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Semester count badge */}
      <p className="text-xs text-slate-400 text-right pr-2">
        Showing {visibleRows.length} of {scheduleArray.length} exam slots
        {selectedSem ? ` · Semester ${selectedSem}` : ''}
      </p>
    </div>
  );
}
