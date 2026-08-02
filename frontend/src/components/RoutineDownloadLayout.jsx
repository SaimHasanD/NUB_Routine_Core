import React from 'react';
import { A4_LANDSCAPE_WIDTH_PX, EXPORT_SHEET_PADDING } from '../utils/exportSheet.js';
import { COURSE_NAMES } from '../utils/courseNames.js';


// Accent colors — change PRIMARY to match your brand if needed.
// Everything else (table headers, course codes, section labels) derives from it.
const PRIMARY = "#2c5f8a";
const BORDER = "#e3e6ea";
const STRIPE = "#f6f8fa";

const ODD_BG = "#fffaf0";
const ODD_TEXT = "#b45309";
const ODD_LABEL_BG = "#fdf3e0";

const EVEN_BG = "#f5f9ff";
const EVEN_TEXT = "#1d4ed8";
const EVEN_LABEL_BG = "#e8f0fe";

const ONLINE_TEXT = "#7c3aed";

export default function RoutineDownloadLayout({
  routine,
  selectedGroup,
  title,
  season,
  oddDates,
  evenDates,
  forExport = false,
}) {
  if (!routine || routine.length === 0) return null;

  const rootId = forExport ? 'routine-print-sheet' : undefined;
  const mainTableId = forExport ? 'routine-main-table' : undefined;
  const oddTableId = forExport ? 'routine-odd-table' : undefined;
  const instTableId = forExport ? 'routine-inst-table' : undefined;
  const evenTableId = forExport ? 'routine-even-table' : undefined;

  // Demo fallback so the Email column is never blank while real instructor
  // emails aren't wired into the data source yet.
  const generateDemoEmail = (name, acronym) => {
    if (name) {
      const parts = name
        .toLowerCase()
        .replace(/[^a-z\s]/g, '')
        .trim()
        .split(/\s+/)
        .filter(Boolean);
      if (parts.length >= 2) return `${parts[0]}.${parts[parts.length - 1]}@gmail.com`;
      if (parts.length === 1) return `${parts[0]}@gmail.com`;
    }
    return `${(acronym || 'instructor').toLowerCase()}@gmail.com`;
  };

  const instructors = [];
  const seenAcro = new Set();

  routine.forEach(entry => {
    const teacher = entry.teacher;
    if (teacher && teacher.name && teacher.name !== "TBA" && !seenAcro.has(entry.teacher_acro)) {
      seenAcro.add(entry.teacher_acro);
      const name = teacher.name === entry.teacher_acro ? "" : teacher.name;
      instructors.push({
        acronym: entry.teacher_acro,
        name,
        designation: teacher.designation || "",
        department: teacher.department || "",
        mobile: teacher.mobile || "",
        email: teacher.email || generateDemoEmail(name, entry.teacher_acro),
      });
    }
  });

  if (instructors.length === 0) {
    instructors.push({
      acronym: "TBA",
      name: "To Be Announced",
      designation: "",
      department: "",
      mobile: "",
      email: "",
    });
  }

  // Sort routine so Online classes appear at the end
  const sortedRoutine = [...routine].sort((a, b) => {
    const aIsOnline = a.room.toLowerCase() === 'online';
    const bIsOnline = b.room.toLowerCase() === 'online';
    if (aIsOnline && !bIsOnline) return 1;
    if (!aIsOnline && bIsOnline) return -1;
    return 0;
  });

  const getDayNotes = (entry) => {
    if (entry.room.toLowerCase() === "online") return `${entry.day} (Online)`;
    if (entry.odd_even === "odd") return "Odd Weeks Only";
    if (entry.odd_even === "even") return "Even Weeks Only";
    return entry.week_note || "";
  };

  // Note text drives its own color — keeps it meaningful even in grayscale print,
  // and keeps it visually linked to the matching date grid below.
  const getNoteColor = (note) => {
    if (!note) return "#334155";
    if (note.includes("Online")) return ONLINE_TEXT;
    const lower = note.toLowerCase();
    if (lower.includes("odd")) return ODD_TEXT;
    if (lower.includes("even")) return EVEN_TEXT;
    return "#334155";
  };

  const formatMobile = (mobile) => {
    if (mobile == null || mobile === '') return '';
    const text = String(mobile).trim();
    return text.endsWith('.0') ? text.slice(0, -2) : text;
  };

  // ----- Style objects -----

  const pageStyle = {
    width: `${A4_LANDSCAPE_WIDTH_PX}px`,
    padding: EXPORT_SHEET_PADDING,
    backgroundColor: '#ffffff',
    fontFamily: '"Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    color: '#1a1a1a',
    boxSizing: 'border-box',
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    borderBottom: `2px solid ${PRIMARY}`,
    paddingBottom: '8px',
    marginBottom: '14px',
  };

  const titleStyle = { fontSize: '15px', fontWeight: 700, margin: 0, letterSpacing: '0.3px', lineHeight: 1.35, flex: 1 };
  const termStyle = { fontSize: '12px', color: '#666', whiteSpace: 'nowrap', flexShrink: 0, paddingTop: '1px' };

  const mainTableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    tableLayout: 'fixed',
    fontSize: '11.5px',
    marginBottom: '16px',
  };

  const mainThStyle = {
    backgroundColor: PRIMARY,
    color: '#ffffff',
    fontWeight: 600,
    fontSize: '10.5px',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    padding: '7px 8px',
    textAlign: 'left',
  };

  const mainTdBase = {
    padding: '7px 8px',
    textAlign: 'left',
    lineHeight: 1.4,
    borderBottom: `1px solid ${BORDER}`,
  };

  const timeCellStyle = { ...mainTdBase, fontWeight: 700, color: '#1a3a52', whiteSpace: 'nowrap' };
  const courseCellStyle = {
    ...mainTdBase,
    fontFamily: '"Courier New", monospace',
    fontWeight: 700,
    color: PRIMARY,
    whiteSpace: 'nowrap',
  };

  // ----- Bottom section: date grids -----

  const labelBaseStyle = {
    fontSize: '10px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    padding: '5px 10px',
    marginBottom: '6px',
  };

  const datesTableStyle = { width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' };

  const dateCellStyle = (bg, color) => ({
    border: `1px solid ${BORDER}`,
    padding: '6px 4px',
    textAlign: 'center',
    fontSize: '10.5px',
    fontWeight: 600,
    backgroundColor: bg,
    color,
  });

  const renderDateGrid = (dates, bg, color) => {
    const cells = Array.from({ length: 8 }, (_, i) => (dates && dates[i]) || '');
    const row1 = cells.slice(0, 4);
    const row2 = cells.slice(4, 8);
    return (
      <table style={datesTableStyle}>
        <tbody>
          <tr>
            {row1.map((d, i) => <td key={i} style={dateCellStyle(bg, color)}>{d}</td>)}
          </tr>
          <tr>
            {row2.map((d, i) => <td key={i} style={dateCellStyle(bg, color)}>{d}</td>)}
          </tr>
        </tbody>
      </table>
    );
  };

  // ----- Instructor table -----

  const subTableStyle = { width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', fontSize: '10.5px' };

  const subThStyle = {
    backgroundColor: '#eef2f6',
    color: PRIMARY,
    fontWeight: 700,
    fontSize: '10px',
    textTransform: 'uppercase',
    padding: '6px 8px',
    textAlign: 'left',
  };

  const subTdBase = {
    padding: '6px 8px',
    textAlign: 'left',
    lineHeight: 1.35,
    borderBottom: `1px solid ${BORDER}`,
  };

  const instructorLabelStyle = {
    ...labelBaseStyle,
    backgroundColor: PRIMARY,
    color: '#ffffff',
  };

  let displayTitle = title || `NUB · ECSE · Section ${selectedGroup} — Class Routine`;
  if (title) {
    displayTitle = title.replace(/Northern University Bangladesh Permanent Campus Central\s*/gi, "");
    if (!displayTitle.toLowerCase().includes('section')) {
      if (displayTitle.includes("ECSE,")) {
        displayTitle = displayTitle.replace("ECSE,", `ECSE, Section ${selectedGroup},`);
      } else if (displayTitle.includes("ECSE")) {
        displayTitle = displayTitle.replace("ECSE", `ECSE, Section ${selectedGroup}`);
      } else {
        displayTitle = `${displayTitle} (Section ${selectedGroup})`;
      }
    }
  }

  return (
    <div id={rootId} style={pageStyle}>

      {/* HEADER */}
      <div style={headerStyle}>
        <h1 style={titleStyle}>
          {displayTitle}
        </h1>
        {season && <span style={termStyle}>{season}</span>}
      </div>

      {/* MAIN ROUTINE TABLE */}
      <table id={mainTableId} style={mainTableStyle}>
        <colgroup>
          <col style={{ width: '3%' }} />
          <col style={{ width: '12%' }} />
          <col style={{ width: '7%' }} />
          <col style={{ width: '6%' }} />
          <col style={{ width: '9%' }} />
          <col style={{ width: '50%' }} />
          <col style={{ width: '13%' }} />
        </colgroup>
        <thead>
          <tr>
            <th style={mainThStyle}>S.L</th>
            <th style={mainThStyle}>Time</th>
            <th style={mainThStyle}>Room</th>
            <th style={mainThStyle}>Instr.</th>
            <th style={mainThStyle}>Course</th>
            <th style={mainThStyle}>Subject</th>
            <th style={mainThStyle}>Notes</th>
          </tr>
        </thead>
        <tbody>
          {sortedRoutine.map((entry, index) => {
            const subjectName = COURSE_NAMES[entry.course] || entry.course;
            const note = getDayNotes(entry);
            const rowBg = index % 2 === 1 ? STRIPE : '#ffffff';
            const tdStyle = { ...mainTdBase, backgroundColor: rowBg };
            return (
              <tr key={index}>
                <td style={tdStyle}>{index + 1}</td>
                <td style={{ ...timeCellStyle, backgroundColor: rowBg }}>
                  {entry.start_time} - {entry.end_time}
                </td>
                <td style={tdStyle}>{entry.room}</td>
                <td style={tdStyle}>{entry.teacher_acro || 'TBA'}</td>
                <td style={{ ...courseCellStyle, backgroundColor: rowBg }}>{entry.course}</td>
                <td style={tdStyle}>{subjectName}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, fontSize: '10.5px', color: getNoteColor(note), whiteSpace: 'nowrap' }}>
                  {note}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* ODD / EVEN WEEK DATE GRIDS */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '14px', tableLayout: 'fixed' }}>
        <tbody>
          <tr>
            <td style={{ width: '50%', verticalAlign: 'top', paddingRight: '12px' }}>
              <div id={oddTableId} style={{ ...labelBaseStyle, backgroundColor: ODD_LABEL_BG, color: ODD_TEXT }}>
                Odd Week Dates
              </div>
              {renderDateGrid(oddDates, ODD_BG, ODD_TEXT)}
            </td>
            <td style={{ width: '50%', verticalAlign: 'top', paddingLeft: '12px' }}>
              <div id={evenTableId} style={{ ...labelBaseStyle, backgroundColor: EVEN_LABEL_BG, color: EVEN_TEXT }}>
                Even Week Dates
              </div>
              {renderDateGrid(evenDates, EVEN_BG, EVEN_TEXT)}
            </td>
          </tr>
        </tbody>
      </table>

      {/* INSTRUCTOR LIST */}
      <div style={instructorLabelStyle}>Instructor List</div>
      <table id={instTableId} style={subTableStyle}>
        <colgroup>
          <col style={{ width: '5%' }} />
          <col style={{ width: '8%' }} />
          <col style={{ width: '19%' }} />
          <col style={{ width: '14%' }} />
          <col style={{ width: '11%' }} />
          <col style={{ width: '15%' }} />
          <col style={{ width: '28%' }} />
        </colgroup>
        <thead>
          <tr>
            <th style={subThStyle}>S.L</th>
            <th style={subThStyle}>Acro</th>
            <th style={subThStyle}>Name</th>
            <th style={subThStyle}>Designation</th>
            <th style={subThStyle}>Dept</th>
            <th style={subThStyle}>Mobile</th>
            <th style={subThStyle}>Email</th>
          </tr>
        </thead>
        <tbody>
          {instructors.map((inst, idx) => {
            const rowBg = idx % 2 === 1 ? STRIPE : '#ffffff';
            const tdStyle = { ...subTdBase, backgroundColor: rowBg };
            return (
              <tr key={idx}>
                <td style={tdStyle}>{idx + 1}</td>
                <td style={{ ...tdStyle, fontWeight: 700, color: PRIMARY }}>{inst.acronym}</td>
                <td style={tdStyle}>{inst.name}</td>
                <td style={tdStyle}>{inst.designation}</td>
                <td style={tdStyle}>{inst.department}</td>
                <td style={tdStyle}>{formatMobile(inst.mobile)}</td>
                <td style={{ ...tdStyle, color: PRIMARY }}>{inst.email}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* FOOTER */}
      <div style={{ marginTop: '8px', fontSize: '9px', color: '#888', textAlign: 'right' }}>
        Department of CSE, NUB
      </div>
    </div>
  );
}
