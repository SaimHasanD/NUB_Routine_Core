import React, { useState, useRef, useEffect } from 'react';
import { Upload, Lock, CheckCircle, AlertCircle, FileSpreadsheet, RefreshCw, Calendar, Layers, Hash, ClipboardList, Image as ImageIcon } from 'lucide-react';
import { uploadExcel, fetchAdminStatus, uploadExamSchedule, getExamSchedule } from '../services/api.js';

const ADMIN_PASSWORD = "admin123_nu";

export default function UploadScreen() {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState('');

  // Routine status
  const [routineStatus, setRoutineStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Upload
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // Exam upload
  const [examFile, setExamFile] = useState(null);
  const [examDragActive, setExamDragActive] = useState(false);
  const [examUploading, setExamUploading] = useState(false);
  const [examSuccess, setExamSuccess] = useState(null);
  const [examError, setExamError] = useState(null);
  const examFileInputRef = useRef(null);

  const [examData, setExamData] = useState(null);

  const loadStatus = async () => {
    setStatusLoading(true);
    try {
      const data = await fetchAdminStatus();
      setRoutineStatus(data);
    } catch {
      setRoutineStatus(null);
    }

    try {
      const eData = await getExamSchedule();
      setExamData(eData);
    } catch {
      setExamData(null);
    }

    setStatusLoading(false);
  };

  useEffect(() => {
    if (isAuthenticated) loadStatus();
  }, [isAuthenticated]);

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === ADMIN_PASSWORD) {
      setIsAuthenticated(true);
      setAuthError('');
    } else {
      setAuthError('Invalid admin password. Access denied.');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleUpload = async (isReplace = false) => {
    if (!file) return;
    setUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const data = await uploadExcel(file, password, isReplace);
      setUploadSuccess({
        message: data.message,
        groupsCount: data.groups ? data.groups.length : 0,
        totalEntries: data.total_entries || 0,
      });
      setFile(null);
      // Refresh status after successful upload
      await loadStatus();
    } catch (error) {
      console.error("Upload failed", error);
      setUploadError(error.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleExamUpload = async () => {
    if (!examFile) return;
    setExamUploading(true);
    setExamSuccess(null);
    setExamError(null);
    try {
      const data = await uploadExamSchedule(examFile, password);
      setExamSuccess(`Exam schedule saved — ${data.entries} exam day(s) parsed.`);
      setExamFile(null);
    } catch (err) {
      console.error('Exam upload failed', err);
      setExamError(err.message || 'Exam upload failed.');
    } finally {
      setExamUploading(false);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown';
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  // ── Login Screen ────────────────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full border border-slate-100">
          <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 mb-6 mx-auto">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-center text-slate-900 mb-2">Admin Authentication</h2>
          <p className="text-slate-500 text-center text-sm mb-6">
            Enter password to manage class schedules.
          </p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
              />
            </div>

            {authError && (
              <div className="flex items-center gap-2 text-rose-600 text-sm bg-rose-50 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl transition-all shadow-sm"
            >
              Verify &amp; Enter
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Determine routine state ─────────────────────────────────────
  const hasRoutine = routineStatus && routineStatus.loaded;
  const isReady = routineStatus !== null && !statusLoading;

  // ── Admin Panel ─────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto space-y-6">

      {/* ── Current Routine Status Card ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
            Active Routine
          </h2>
          <button
            onClick={loadStatus}
            disabled={statusLoading}
            className="text-slate-400 hover:text-indigo-600 transition-colors p-1.5 rounded-lg hover:bg-slate-50"
            title="Refresh status"
          >
            <RefreshCw className={`w-4 h-4 ${statusLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="p-6">
          {statusLoading && !routineStatus ? (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-3" />
              <p className="text-sm text-slate-500">Checking system status...</p>
            </div>
          ) : !routineStatus ? (
            <div className="text-center py-6">
              <div className="w-14 h-14 bg-rose-50 rounded-full flex items-center justify-center text-rose-500 mx-auto mb-4">
                <AlertCircle className="w-7 h-7" />
              </div>
              <h3 className="text-slate-900 font-semibold mb-1">Failed to Load Status</h3>
              <p className="text-slate-500 text-sm mb-4">Could not connect to the backend.</p>
              <button onClick={loadStatus} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors">
                Retry Connection
              </button>
            </div>
          ) : hasRoutine ? (
            /* ── Routine IS loaded ── */
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Active
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    File Name
                  </div>
                  <p className="text-slate-900 font-semibold text-sm truncate" title={routineStatus.filename}>
                    {routineStatus.filename || 'Unknown'}
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">
                    <Calendar className="w-3.5 h-3.5" />
                    Loaded At
                  </div>
                  <p className="text-slate-900 font-semibold text-sm">
                    {formatDate(routineStatus.uploaded_at)}
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">
                    <Layers className="w-3.5 h-3.5" />
                    Sections
                  </div>
                  <p className="text-slate-900 font-semibold text-sm">
                    {routineStatus.groups_count} groups
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">
                    <Hash className="w-3.5 h-3.5" />
                    Total Entries
                  </div>
                  <p className="text-slate-900 font-semibold text-sm">
                    {routineStatus.total_entries} classes
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* ── No routine loaded ── */
            <div className="text-center py-6">
              <div className="w-14 h-14 bg-amber-50 rounded-full flex items-center justify-center text-amber-500 mx-auto mb-4">
                <AlertCircle className="w-7 h-7" />
              </div>
              <h3 className="text-slate-900 font-semibold mb-1">No Routine Loaded</h3>
              <p className="text-slate-500 text-sm">
                Upload an Excel file below to get started.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Upload Card ── */}
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
        <h2 className="text-lg font-bold text-slate-900 mb-1">
          {hasRoutine ? 'Replace Routine' : 'Upload Routine'}
        </h2>
        <p className="text-slate-500 text-sm mb-6">
          {hasRoutine
            ? 'Upload a new Excel file to replace the currently active routine.'
            : 'Upload the NUB master schedule Excel file to activate the system.'}
        </p>

        {/* Drag & Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${dragActive
            ? 'border-indigo-600 bg-indigo-50/50'
            : 'border-slate-300 hover:border-slate-400 bg-slate-50'
            }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".xlsx,.xls"
            onChange={handleFileChange}
          />
          <Upload className="w-10 h-10 text-slate-400 mx-auto mb-4" />
          {file ? (
            <p className="text-indigo-600 font-medium text-sm">{file.name}</p>
          ) : (
            <div>
              <p className="text-slate-700 font-medium">Click to upload or drag &amp; drop</p>
              <p className="text-xs text-slate-400 mt-1">Excel (.xlsx) files only</p>
            </div>
          )}
        </div>

        {/* Upload / Replace button */}
        <button
          onClick={() => handleUpload(hasRoutine)}
          disabled={!file || uploading}
          className={`w-full mt-6 py-3 font-medium rounded-xl transition-all shadow-sm flex justify-center items-center gap-2 ${file && !uploading
            ? hasRoutine
              ? 'bg-amber-500 hover:bg-amber-600 text-white'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
            : 'bg-slate-100 text-slate-400 cursor-not-allowed'
            }`}
        >
          {uploading ? (
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          ) : hasRoutine ? (
            <>
              <RefreshCw className="w-4 h-4" />
              Replace Current Routine
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload &amp; Activate Routine
            </>
          )}
        </button>

        {/* Warning for replacement */}
        {hasRoutine && file && (
          <div className="mt-4 flex items-start gap-2 text-amber-700 text-xs bg-amber-50 p-3 rounded-lg border border-amber-200">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>This will replace the current routine <strong>"{routineStatus?.filename}"</strong> with <strong>"{file.name}"</strong>. This action cannot be undone.</span>
          </div>
        )}

        {/* Success */}
        {uploadSuccess && (
          <div className="mt-6 border border-emerald-200 bg-emerald-50 rounded-xl p-4 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-emerald-900 text-sm">
                {hasRoutine ? 'Routine Replaced!' : 'Upload Successful!'}
              </h4>
              <p className="text-emerald-700 text-xs mt-0.5">
                {uploadSuccess.message}
              </p>
            </div>
          </div>
        )}

        {/* Error */}
        {uploadError && (
          <div className="mt-6 border border-rose-200 bg-rose-50 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-rose-900 text-sm">Upload Failed!</h4>
              <p className="text-rose-700 text-xs mt-0.5">
                {uploadError}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Exam Schedule Upload Card ── */}
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
        <h2 className="text-lg font-bold text-slate-900 mb-1 flex items-center gap-2">
          <ClipboardList className="w-5 h-5 text-violet-600" />
          Exam Schedule
        </h2>
        <p className="text-slate-500 text-sm mb-6">
          Upload a photo, screenshot, or PDF of the exam schedule.
          Gemini Vision will extract and structure the data automatically.
        </p>

        {examData?.image_url && (
          <div className="mb-6 p-4 bg-slate-50 border border-slate-100 rounded-xl">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Currently Active
            </h3>
            <div className="aspect-video relative rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-white flex items-center justify-center">
              <img
                src={examData.image_url}
                alt="Active Exam Schedule"
                className="max-w-full max-h-full object-contain"
              />
            </div>
            <p className="text-xs text-slate-400 mt-2 text-center">
              Showing {examData.schedule?.length || 0} exam slot(s)
            </p>
          </div>
        )}

        {/* Drag & Drop zone */}
        <div
          onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setExamDragActive(true); }}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setExamDragActive(true); }}
          onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setExamDragActive(false); }}
          onDrop={(e) => {
            e.preventDefault(); e.stopPropagation(); setExamDragActive(false);
            if (e.dataTransfer.files?.[0]) setExamFile(e.dataTransfer.files[0]);
          }}
          onClick={() => examFileInputRef.current.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${examDragActive
            ? 'border-violet-600 bg-violet-50/50'
            : 'border-slate-300 hover:border-slate-400 bg-slate-50'
            }`}
        >
          <input
            ref={examFileInputRef}
            type="file"
            className="hidden"
            accept="image/*,.pdf"
            onChange={(e) => { if (e.target.files?.[0]) setExamFile(e.target.files[0]); }}
          />
          <ImageIcon className="w-10 h-10 text-slate-400 mx-auto mb-4" />
          {examFile ? (
            <p className="text-violet-600 font-medium text-sm">{examFile.name}</p>
          ) : (
            <div>
              <p className="text-slate-700 font-medium">Click to upload or drag &amp; drop</p>
              <p className="text-xs text-slate-400 mt-1">PNG, JPG, PDF — first page used for PDF</p>
            </div>
          )}
        </div>

        {/* Upload button */}
        {/* <button
          onClick={handleExamUpload}
          disabled={!examFile || examUploading}
          className={`w-full mt-6 py-3 font-medium rounded-xl transition-all shadow-sm flex justify-center items-center gap-2 ${examFile && !examUploading
              ? 'bg-violet-600 hover:bg-violet-700 text-white'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed'
            }`}
        >
          {examUploading ? (
            <div className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload &amp; Process Exam Schedule
            </>
          )}
        </button> */}

        {/* Success */}
        {examSuccess && (
          <div className="mt-6 border border-emerald-200 bg-emerald-50 rounded-xl p-4 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-emerald-900 text-sm">Exam Schedule Uploaded!</h4>
              <p className="text-emerald-700 text-xs mt-0.5">{examSuccess}</p>
            </div>
          </div>
        )}

        {/* Error */}
        {examError && (
          <div className="mt-6 border border-rose-200 bg-rose-50 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-rose-900 text-sm">Upload Failed!</h4>
              <p className="text-rose-700 text-xs mt-0.5">{examError}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
