import React, { useState, useMemo } from 'react';
import { Search, User, MapPin } from 'lucide-react';
import {
  DB_TEACHER_ID,
  DB_TEACHER_NAME,
  DB_TEACHER_DEPT,
  DB_TEACHER_DESIGNATION
} from './mappingConstants';

export default function TeacherGrid({ teachers, onSelectTeacher }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTeachers = useMemo(() => {
    if (!searchTerm) return teachers;
    const lowerSearch = searchTerm.toLowerCase();
    
    return teachers.filter((teacher) => {
      const name = teacher[DB_TEACHER_NAME]?.toLowerCase() || '';
      const id = teacher[DB_TEACHER_ID]?.toLowerCase() || '';
      const dept = teacher[DB_TEACHER_DEPT]?.toLowerCase() || '';
      
      return name.includes(lowerSearch) || id.includes(lowerSearch) || dept.includes(lowerSearch);
    });
  }, [teachers, searchTerm]);

  return (
    <div className="w-full max-w-6xl mx-auto p-4 sm:p-6 lg:p-8 animate-fade-in">
      <div className="mb-8 space-y-4 sm:space-y-0 sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Teacher Directory</h1>
          <p className="text-sm text-gray-500 mt-1">Select a teacher to view their routine and details.</p>
        </div>
        <div className="relative max-w-md w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-shadow shadow-sm"
            placeholder="Search by name, initials, or dept..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {filteredTeachers.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredTeachers.map((teacher) => (
            <button
              key={teacher[DB_TEACHER_ID]}
              onClick={() => onSelectTeacher(teacher[DB_TEACHER_ID])}
              className="group relative flex flex-col bg-white rounded-xl border border-gray-200 p-6 text-left hover:border-blue-500 hover:shadow-md transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <div className="flex items-center justify-between w-full mb-4">
                <div className="flex-shrink-0 h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center border border-blue-200 group-hover:bg-blue-600 transition-colors duration-300">
                  <span className="text-lg font-semibold text-blue-700 group-hover:text-white">
                    {teacher[DB_TEACHER_ID]}
                  </span>
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 truncate">
                  {teacher[DB_TEACHER_NAME]}
                </h3>
                <div className="mt-1 flex items-center text-sm text-gray-500">
                  <User className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                  <span className="truncate">{teacher[DB_TEACHER_DESIGNATION]}</span>
                </div>
                <div className="mt-1 flex items-center text-sm text-gray-500">
                  <MapPin className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                  <span className="truncate">{teacher[DB_TEACHER_DEPT]} Dept.</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-gray-50 rounded-xl border border-gray-200 border-dashed">
          <Search className="mx-auto h-12 w-12 text-gray-300 mb-3" />
          <h3 className="text-lg font-medium text-gray-900">No teachers found</h3>
          <p className="mt-1 text-sm text-gray-500">
            We couldn't find anything matching "{searchTerm}". Try adjusting your search.
          </p>
        </div>
      )}
    </div>
  );
}
