import React, { useState, useEffect } from 'react';
import { X, ZoomIn, ZoomOut, FileText, Image as ImageIcon } from 'lucide-react';
import RoutineDownloadLayout from './RoutineDownloadLayout.jsx';

export default function RoutinePreviewModal({
  isOpen,
  onClose,
  routine,
  selectedGroup,
  title,
  season,
  oddDates,
  evenDates,
  onDownloadPdf,
  onDownloadImage,
}) {
  const [scale, setScale] = useState(0.85);

  useEffect(() => {
    if (isOpen && typeof window !== 'undefined') {
      if (window.innerWidth < 640) {
        setScale(0.3); // Scale down to fit mobile screens
      } else if (window.innerWidth < 1024) {
        setScale(0.6); // Scale down for tablets
      } else {
        setScale(0.85);
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.1, 1.5));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.1, 0.2));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-900/60 backdrop-blur-md transition-all duration-300">
      {/* Modal Card */}
      <div className="bg-slate-100 rounded-2xl shadow-2xl w-full max-w-5xl h-[95vh] sm:h-[90vh] flex flex-col border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="bg-white border-b border-slate-200 px-4 sm:px-6 py-3 sm:py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
          <div className="flex justify-between w-full sm:w-auto items-center gap-2">
            <div>
              <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                Routine Download Preview
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                Section {selectedGroup} — Official PDF Print Format
              </p>
            </div>
            {/* Close button on mobile */}
            <button 
              onClick={onClose}
              className="p-2 sm:hidden hover:bg-slate-100 text-slate-500 hover:text-slate-800 rounded-lg transition-colors flex-shrink-0"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Controls */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
            {/* Zoom Controls */}
            <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200">
              <button 
                onClick={handleZoomOut}
                title="Zoom Out"
                className="p-1.5 hover:bg-white text-slate-600 rounded-md transition-colors"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-xs font-semibold px-2 text-slate-700 min-w-[3.5rem] text-center">
                {Math.round(scale * 100)}%
              </span>
              <button 
                onClick={handleZoomIn}
                title="Zoom In"
                className="p-1.5 hover:bg-white text-slate-600 rounded-md transition-colors"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Downloads */}
            <button
              onClick={onDownloadPdf}
              className="flex-1 sm:flex-none flex justify-center items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg transition-colors shadow-sm"
            >
              <FileText className="w-3.5 h-3.5" />
              PDF
            </button>
            <button
              onClick={onDownloadImage}
              className="flex-1 sm:flex-none flex justify-center items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg transition-colors shadow-sm"
            >
              <ImageIcon className="w-3.5 h-3.5" />
              Image
            </button>

            <div className="hidden sm:block h-6 w-px bg-slate-200 mx-1" />

            {/* Close on desktop */}
            <button 
              onClick={onClose}
              className="hidden sm:block p-2 hover:bg-slate-100 text-slate-500 hover:text-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Workspace */}
        <div className="flex-1 overflow-auto p-4 sm:p-8 bg-slate-200/50">
          <div 
            style={{ width: 1123 * scale }} 
            className="mx-auto"
          >
            <div
              className="transition-transform duration-100 ease-out origin-top-left shadow-xl rounded-lg bg-white"
              style={{
                transform: `scale(${scale})`,
                width: '1123px', // Explicit width to maintain layout
                marginBottom: '2rem',
              }}
            >
              <RoutineDownloadLayout
                routine={routine}
                selectedGroup={selectedGroup}
                title={title}
                season={season}
                oddDates={oddDates}
                evenDates={evenDates}
              />
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="bg-white border-t border-slate-200 px-4 sm:px-6 py-3 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <span className="text-center sm:text-left">Tip: The downloaded file maps all course codes to their official NUB subject titles.</span>
          <span className="font-semibold text-indigo-600">Department of CSE, NUB</span>
        </div>
      </div>
    </div>
  );
}
