import React from 'react';
import { Mail, Phone, ArrowLeft, Building2 } from 'lucide-react';
import {
  DB_TEACHER_NAME,
  DB_TEACHER_DESIGNATION,
  DB_TEACHER_DEPT,
  DB_TEACHER_PHONE,
  DB_TEACHER_EMAIL,
  DB_TEACHER_ID
} from './mappingConstants';

export default function TeacherProfile({ teacher, onBack }) {
  if (!teacher) return null;

  const email = teacher[DB_TEACHER_EMAIL];
  const phone = teacher[DB_TEACHER_PHONE];

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
        <button
          onClick={onBack}
          className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 mb-6 transition-colors group"
        >
          <ArrowLeft className="mr-2 h-4 w-4 group-hover:-translate-x-1 transition-transform" />
          Back to Directory
        </button>

        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center">
              <div className="h-16 w-16 sm:h-20 sm:w-20 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center border-2 border-white shadow-sm flex-shrink-0">
                <span className="text-2xl sm:text-3xl font-bold text-blue-700">
                  {teacher[DB_TEACHER_ID]}
                </span>
              </div>
              <div className="ml-5">
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight truncate">
                  {teacher[DB_TEACHER_NAME]}
                </h2>
                <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap sm:mt-2 sm:space-x-6 gap-y-2">
                  <div className="flex items-center text-sm text-gray-500">
                    <Building2 className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                    {teacher[DB_TEACHER_DESIGNATION]}, {teacher[DB_TEACHER_DEPT]} Dept.
                  </div>
                  {phone ? (
                    <div className="flex items-center text-sm text-gray-500">
                      <Phone className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                      <a href={`tel:${phone}`} className="hover:text-blue-600 transition-colors">
                        {phone}
                      </a>
                    </div>
                  ) : null}
                  {email ? (
                    <div className="flex items-center text-sm text-gray-500">
                      <Mail className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                      <a href={`mailto:${email}`} className="hover:text-blue-600 transition-colors">
                        {email}
                      </a>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
