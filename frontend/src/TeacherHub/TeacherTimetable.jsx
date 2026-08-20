import React, { useMemo } from 'react';
import { CalendarX } from 'lucide-react';
import {
  EXCEL_CLASS_TEACHER_ID,
  EXCEL_CLASS_DAY,
  EXCEL_CLASS_START_TIME,
  EXCEL_CLASS_END_TIME,
  EXCEL_CLASS_COURSE_CODE,
  EXCEL_CLASS_COURSE_NAME,
  EXCEL_CLASS_ROOM,
  EXCEL_CLASS_GROUP,
  EXCEL_CLASS_TYPE
} from './mappingConstants';

const DAYS_OF_WEEK = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

export default function TeacherTimetable({ teacherId, scheduleData }) {
  // Filter and structure the schedule data for this specific teacher
  const teacherClasses = useMemo(() => {
    if (!scheduleData || !teacherId) return {};

    const filtered = scheduleData.filter(
      (entry) => entry[EXCEL_CLASS_TEACHER_ID] === teacherId
    );

    // Group by day for easier rendering
    const grouped = {};
    DAYS_OF_WEEK.forEach(day => { grouped[day] = []; });

    filtered.forEach(entry => {
      const day = entry[EXCEL_CLASS_DAY];
      if (grouped[day]) {
        grouped[day].push(entry);
      } else {
        // Fallback for unexpected day strings
        if (!grouped['Other']) grouped['Other'] = [];
        grouped['Other'].push(entry);
      }
    });

    // Sort classes within each day by start time
    Object.keys(grouped).forEach(day => {
      grouped[day].sort((a, b) => {
        const timeA = a[EXCEL_CLASS_START_TIME] || '';
        const timeB = b[EXCEL_CLASS_START_TIME] || '';
        return timeA.localeCompare(timeB);
      });
    });

    return grouped;
  }, [scheduleData, teacherId]);

  const totalClasses = useMemo(() => {
    return Object.values(teacherClasses).reduce((acc, curr) => acc + curr.length, 0);
  }, [teacherClasses]);

  if (totalClasses === 0) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 animate-fade-in">
        <div className="flex flex-col items-center justify-center p-12 bg-gray-50 border border-gray-200 border-dashed rounded-2xl">
          <div className="h-16 w-16 bg-white rounded-full flex items-center justify-center shadow-sm mb-4">
            <CalendarX className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">No Classes Assigned</h3>
          <p className="text-gray-500 mt-2 text-center max-w-md">
            This teacher currently has no classes scheduled in the active routine.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-900">Weekly Routine</h3>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
          {totalClasses} Classes Total
        </span>
      </div>

      <div className="space-y-6">
        {Object.entries(teacherClasses).map(([day, classes]) => {
          if (classes.length === 0) return null;

          return (
            <div key={day} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
                <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">{day}</h4>
              </div>
              <div className="divide-y divide-gray-100">
                {classes.map((cls, idx) => (
                  <div key={idx} className="p-6 sm:flex sm:items-center hover:bg-slate-50 transition-colors">
                    <div className="sm:w-1/4 sm:pr-4 mb-4 sm:mb-0">
                      <div className="text-lg font-semibold text-gray-900">
                        {cls[EXCEL_CLASS_START_TIME]} - {cls[EXCEL_CLASS_END_TIME]}
                      </div>
                      <div className="text-sm font-medium text-blue-600 mt-1">
                        Room: {cls[EXCEL_CLASS_ROOM]}
                      </div>
                    </div>
                    <div className="sm:w-3/4 flex flex-col sm:flex-row sm:items-center justify-between">
                      <div>
                        <div className="text-lg font-bold text-gray-900 flex items-center gap-2">
                          {cls[EXCEL_CLASS_COURSE_CODE]}
                          {cls[EXCEL_CLASS_TYPE] && (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                              {cls[EXCEL_CLASS_TYPE]}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {cls[EXCEL_CLASS_COURSE_NAME]}
                        </div>
                      </div>
                      <div className="mt-4 sm:mt-0 sm:text-right">
                        <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                          Group {cls[EXCEL_CLASS_GROUP]}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
