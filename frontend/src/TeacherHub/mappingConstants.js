/**
 * MAPPING CONSTANTS
 * 
 * Adjust these constants to match the exact keys output by your Excel parser 
 * for the "ECSE Summer 18-06-2026 (5).xlsx" file and your Database models.
 */

// --- Database Teacher Model Keys ---
export const DB_TEACHER_ID = 'teacher_acro'; // The unique identifier for the teacher in DB
export const DB_TEACHER_NAME = 'name';
export const DB_TEACHER_DEPT = 'department';
export const DB_TEACHER_DESIGNATION = 'designation';
export const DB_TEACHER_PHONE = 'mobile';
export const DB_TEACHER_EMAIL = 'email';

// --- Excel Parsed JSON Keys (Schedule Entry) ---
export const EXCEL_CLASS_TEACHER_ID = 'teacher_acro'; // The key in the parsed schedule matching DB_TEACHER_ID
export const EXCEL_CLASS_COURSE_CODE = 'course_code';
export const EXCEL_CLASS_COURSE_NAME = 'course';
export const EXCEL_CLASS_GROUP = 'group';
export const EXCEL_CLASS_ROOM = 'room';
export const EXCEL_CLASS_DAY = 'day';
export const EXCEL_CLASS_START_TIME = 'start_time';
export const EXCEL_CLASS_END_TIME = 'end_time';
export const EXCEL_CLASS_TYPE = 'type'; // e.g., theory, lab
