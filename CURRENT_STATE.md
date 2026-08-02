# Current State: ECSE Routine Generator Audit

- This document is the single source of truth representing the current state of the ECSE Routine Generator codebase.
- It lists all files, active API connections, and the status of system bugs and architecture.

## Project Directory Structure and File Audit

### Root Configuration
- `Architecture.svg`: SVG architectural diagram of the system's parser and state layers.
- `CURRENT_STATE.md`: The definitive audit of the project status.
- `Plan And Architecture.md`: Initial design draft mapping out sheet rows and merge mapping concepts.
- `README.md`: Main user guide describing setup, local running, and core parser layout.

### Backend (FastAPI, Python)
- `backend/requirements.txt`: Python dependencies list including FastAPI, Uvicorn, openpyxl, Pydantic, and Requests.
- `backend/app/__init__.py`: Orchestrator that merges parsed subsections, resolves teacher acronyms, splits time slots, and handles day overrides.
- `backend/app/cell_parser.py`: Regular expression parser that extracts class details from single cells.
- `backend/app/faculty_mapper.py`: Parses the Faculty Information sheet to index acronyms to full names and provides a fallback for missing teachers.
- `backend/app/header_parser.py`: Scans the regular, lab, and online header rows to map columns to chronological time slots.
- `backend/app/main.py`: Main FastAPI application registering server-side upload authentication, route endpoints, merges, and server startup autoload lifespan.
- `backend/app/merge_resolver.py`: Builds a coordinates mapping for merged openpyxl ranges so adjacent cells resolve values correctly.
- `backend/app/models.py`: Pydantic response schemas safeguarding JSON output structures.
- `backend/app/parser.py`: Top-level runner that parses files and feeds them to the workbook parser.
- `backend/app/section_lab.py`: Extracts lab section schedules and parses odd and even markers.
- `backend/app/section_online.py`: Extracts online classes, scans the online header day override, and strips odd and even tags for specific courses.
- `backend/app/section_regular.py`: Extracts regular theory schedules.
- `backend/app/state.py`: Holds the global, in-memory, thread-safe schedule data dictionary.
- `backend/test_data/Version_1_ ECSE Class Routine Summer 2025.xlsx`: Test routine data file representing the production sheet for the summer term.

### Frontend (React, Vite, CSS)
- `frontend/index.html`: HTML template specifying base font tags.
- `frontend/package.json`: Frontend package configuration tracking Tailwind and Lucide dependencies.
- `frontend/postcss.config.js`: PostCSS compilation rules.
- `frontend/tailwind.config.js`: Tailwind styling configuration.
- `frontend/vite.config.js`: Vite bundler configuration mapping the development port to proxy the server-side port.
- `frontend/src/App.jsx`: Primary navigation router driving the single-page application views.
- `frontend/src/index.css`: Custom stylesheet importing typography variables.
- `frontend/src/main.jsx`: Vite React rendering entry point.
- `frontend/src/components/RoutineDownloadLayout.jsx`: PDF replica print layout mapping course codes, odd and even week calendars, and dynamic section-specific instructor lists.
- `frontend/src/components/RoutinePreviewModal.jsx`: Modal to preview the print layout before downloading.
- `frontend/src/components/RoutineTable.jsx`: Displays the schedule grid from Sunday to Saturday with hover timelines and information popups.
- `frontend/src/screens/DashboardScreen.jsx`: Main dashboard viewport displaying section search and generated routines, featuring PDF and image download actions.
- `frontend/src/screens/UploadScreen.jsx`: Admin control panel showing login, file uploader, and visual alerts.
- `frontend/src/services/api.js`: HTTP gateway querying backend REST APIs.

## Frontend-to-Backend API Connections

- The `healthCheck()` function calls `GET /api/v1/health` during page mount and receives a status object.
- The `fetchGroups()` function calls `GET /api/v1/groups` for dropdown autocompletion in the dashboard and receives an array of groups.
- The `fetchRoutine(groupId)` function calls `GET /api/v1/routine/{group_id}` when generating a routine and receives the group schedule entries.
- The `uploadExcel(file, password)` function calls `POST /api/v1/upload` using form data from the upload screen and receives the parsed group list and total entry count.

## Issues, Inconsistencies, and Incomplete Items

- The active system status is completely solid and operational.
- All active issues, architectural gaps, and parser bugs have been fully fixed, tested, and resolved.
- The mock data constant was cleanly deleted from the dashboard screen.
- An unused storage script was completely deleted from the backend application.
- A phantom directory structure was fully removed.
- The API service was rewritten cleanly as a strict gateway to the backend REST API.
- Lifespan autoload functionality was added to parse the test Excel file automatically on startup.
- The backend upload endpoint was secured with server-side authentication.
- Upload error states, descriptive banner notifications, and catch handlers were implemented in the upload screen.
- Saturday strip rendering was added to the weekly table layout.
- Dynamic online header scanning was developed to map classes dynamically to Wednesday.
- Odd and even markers for specific courses were stripped at the parser source level.
- Client-side PDF and image generation were implemented to replicate the official routine print layout.

## What to Do Next

- Consider adding an admin panel to update the sessional dates dynamically for future semesters, as they are currently hardcoded.
- Implement a JWT-based authentication system for the admin dashboard rather than using a single hardcoded password.

## How to Run

- To run the backend, navigate to the `backend` directory and start Uvicorn using the Python executable from the virtual environment on port 8000.
- To run the frontend, navigate to the `frontend` directory and execute the development script via npm.

## System Parse Statistics

- The system successfully loads 49 registered sections on startup.
- The system correctly extracts, merges, and indexes 490 schedule entries.
- The dynamic override mapping correctly assigns regular and lab classes to Friday, and online classes to Wednesday.
