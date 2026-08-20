import React, { useState, useEffect } from 'react';
import UploadScreen from './screens/UploadScreen.jsx';
import DashboardScreen from './screens/DashboardScreen.jsx';
import TeacherHubEntry from './TeacherHub/TeacherHubEntry.jsx';
import { fetchTeachers, fetchTeachersSchedule } from './services/api.js';

function getInitialRoute() {
  const p = window.location.pathname;
  if (p === '/admin') return '/admin';
  return '/';
}

export default function App() {
  const [currentRoute, setCurrentRoute] = useState(getInitialRoute);
  const [activeView, setActiveView] = useState('student');
  const [teachersData, setTeachersData] = useState([]);
  const [scheduleData, setScheduleData] = useState([]);
  const [isLoadingTeacherData, setIsLoadingTeacherData] = useState(false);

  useEffect(() => {
    if (activeView === 'teacher' && teachersData.length === 0) {
      setIsLoadingTeacherData(true);
      Promise.all([fetchTeachers(), fetchTeachersSchedule()])
        .then(([teachers, schedule]) => {
          setTeachersData(teachers);
          setScheduleData(schedule);
        })
        .catch(err => console.error("Failed to load teacher data:", err))
        .finally(() => setIsLoadingTeacherData(false));
    }
  }, [activeView, teachersData.length]);

  useEffect(() => {
    const handleLocationChange = () => setCurrentRoute(getInitialRoute());
    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentRoute(path);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans antialiased">
      {/* Navigation Bar */}
      <nav className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center shadow-sm sticky top-0 z-50">
        <div
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => {
            navigate('/');
            setActiveView('student');
          }}
        >
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
            N
          </div>
          <span className="font-bold text-slate-900 tracking-tight">NUB Routine Hub</span>
        </div>
        <div className="flex gap-3 items-center">
          <button
            onClick={() => {
              setActiveView('teacher');
              navigate('/');
            }}
            className={`text-sm font-semibold px-3 py-2 transition-colors ${
              activeView === 'teacher' ? 'text-indigo-600' : 'text-gray-600 hover:text-indigo-600'
            }`}
          >
            Teacher Hub
          </button>

          <button
            onClick={() => window.open('https://rajdip27.github.io/NUB-Cover-Page/', '_blank')}
            className="text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg transition-colors"
          >
            NUB Cover Page
          </button>

          <button
            onClick={() => {
              navigate(currentRoute === '/admin' ? '/' : '/admin');
              setActiveView('student');
            }}
            className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg transition-colors"
          >
            {currentRoute === '/admin' ? 'Public Portal' : 'Admin Panel'}
          </button>
        </div>
      </nav>

      {/* Screen Router */}
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {currentRoute === '/admin' ? (
          <UploadScreen />
        ) : (
          activeView === 'student' ? (
            <DashboardScreen />
          ) : (
            isLoadingTeacherData ? (
              <div className="flex justify-center py-20">
                <div className="animate-pulse flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 bg-indigo-500 rounded-full"></div>
                  <div className="w-4 h-4 bg-indigo-500 rounded-full delay-75"></div>
                  <div className="w-4 h-4 bg-indigo-500 rounded-full delay-150"></div>
                </div>
              </div>
            ) : (
              <TeacherHubEntry 
                teachersData={teachersData} 
                scheduleData={scheduleData} 
              />
            )
          )
        )}
      </main>
    </div>
  );
}
