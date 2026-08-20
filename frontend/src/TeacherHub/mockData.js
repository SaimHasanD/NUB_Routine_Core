// Mock data for testing the TeacherHub module without a real backend

export const mockTeachers = [
  {
    name: "Dr. Syed Akhter Hossain",
    designation: "Professor",
    department: "CSE",
    mobile: "01711122334",
    email: "sahossain@nub.ac.bd",
    teacher_acro: "SAH"
  },
  {
    name: "A.H.M Fazle Elahi",
    designation: "Assistant Professor",
    department: "CSE",
    mobile: "01999999999",
    email: "elahi@nub.ac.bd",
    teacher_acro: "FE"
  },
  {
    name: "Jane Doe",
    designation: "Lecturer",
    department: "EEE",
    mobile: "01888888888",
    email: "jane@nub.ac.bd",
    teacher_acro: "JD"
  }
];

export const mockSchedule = [
  {
    course_code: "CSE-1101",
    course: "Computer Fundamentals",
    group: "1",
    teacher_acro: "FE",
    room: "201",
    time_slot: "09:00 AM - 10:30 AM",
    start_time: "09:00 AM",
    end_time: "10:30 AM",
    day: "Sunday",
    type: "Theory",
    section_type: "regular",
    week_note: ""
  },
  {
    course_code: "CSE-1102",
    course: "Computer Fundamentals Lab",
    group: "2",
    teacher_acro: "FE",
    room: "Lab 1",
    time_slot: "11:00 AM - 01:00 PM",
    start_time: "11:00 AM",
    end_time: "01:00 PM",
    day: "Sunday",
    type: "Lab",
    section_type: "lab_even",
    week_note: ""
  },
  {
    course_code: "CSE-4101",
    course: "Artificial Intelligence",
    group: "1",
    teacher_acro: "SAH",
    room: "305",
    time_slot: "02:00 PM - 03:30 PM",
    start_time: "02:00 PM",
    end_time: "03:30 PM",
    day: "Monday",
    type: "Theory",
    section_type: "regular",
    week_note: ""
  }
];
