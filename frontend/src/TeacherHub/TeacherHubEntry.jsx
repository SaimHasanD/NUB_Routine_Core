import React, { useState, useEffect, useCallback } from 'react';
import TeacherGrid from './TeacherGrid';
import TeacherProfile from './TeacherProfile';
import TeacherTimetable from './TeacherTimetable';
import { DB_TEACHER_ID } from './mappingConstants';

/**
 * TeacherHubEntry - Main Module Wrapper
 * 
 * Implements robust internal state management that allows for deep linking.
 * It listens to URL parameter changes (?teacher=ID) to sync the state without 
 * strictly depending on a router like Next.js or React Router, making it drop-in ready.
 */
export default function TeacherHubEntry({ 
  teachersData = [], 
  scheduleData = [] 
}) {
  const [selectedTeacherId, setSelectedTeacherId] = useState(null);

  // Sync state with URL parameter on mount and popstate
  useEffect(() => {
    const handleUrlChange = () => {
      const params = new URLSearchParams(window.location.search);
      const teacherParam = params.get('teacher');
      setSelectedTeacherId(teacherParam || null);
    };

    // Initial check
    handleUrlChange();

    // Listen to browser navigation
    window.addEventListener('popstate', handleUrlChange);
    return () => window.removeEventListener('popstate', handleUrlChange);
  }, []);

  // Handle teacher selection and update URL
  const handleSelectTeacher = useCallback((teacherId) => {
    const url = new URL(window.location);
    if (teacherId) {
      url.searchParams.set('teacher', teacherId);
    } else {
      url.searchParams.delete('teacher');
    }
    window.history.pushState({}, '', url);
    setSelectedTeacherId(teacherId);
  }, []);

  const handleBack = useCallback(() => {
    handleSelectTeacher(null);
  }, [handleSelectTeacher]);

  const selectedTeacher = React.useMemo(() => {
    if (!selectedTeacherId) return null;
    return teachersData.find(t => t[DB_TEACHER_ID] === selectedTeacherId) || null;
  }, [teachersData, selectedTeacherId]);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {!selectedTeacherId ? (
        <TeacherGrid 
          teachers={teachersData} 
          onSelectTeacher={handleSelectTeacher} 
        />
      ) : (
        <div className="flex flex-col">
          {selectedTeacher ? (
            <>
              <TeacherProfile 
                teacher={selectedTeacher} 
                onBack={handleBack} 
              />
              <TeacherTimetable 
                teacherId={selectedTeacherId} 
                scheduleData={scheduleData} 
              />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 h-[60vh]">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Teacher Not Found</h2>
              <p className="text-gray-500 mb-6">The requested teacher ID does not exist in our database.</p>
              <button 
                onClick={handleBack}
                className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Return to Directory
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
