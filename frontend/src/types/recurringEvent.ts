// RecurringEvent types for frontend

export interface RecurringEvent {
  id: string;
  content: string;
  duration: number; // in minutes
  created_at: string;
  updated_at: string;

  // Time window preferences
  time_window_start?: string | null; // "HH:MM" format
  time_window_end?: string | null; // "HH:MM" format

  // Recurrence pattern - array of weekday numbers (0-6, starting with Monday as 0)
  recurrence: number[];

  // Related tasks generated from this recurring event
  tasks?: string[]; // Array of task IDs
}

// Form data for creating/updating recurring events
export interface RecurringEventFormData {
  content: string;
  duration: number;
  recurrence_days: number[]; // Array of day numbers (0-6)
  time_window_start?: string | null;
  time_window_end?: string | null;
}

// Response type for recurring event creation
export interface RecurringEventCreationResponse {
  id: string;
  content: string;
  message: string;
}

// Filter types for recurring event listing
export interface RecurringEventFilters {
  // Optional property for any future filters that might be needed
  [key: string]: unknown;
}
