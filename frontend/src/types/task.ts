// Task types

// Primary Task interface
export interface Task {
  id: string;
  content: string;
  duration: number; // in minutes
  is_completed: boolean;
  created_at: string;
  updated_at: string;
  status?: string; // "unscheduled", "scheduled", "completed"

  task_type: "one-off" | "recurring"; // Provided by backend, can be used as a hint

  // Optional fields that define task nature
  dependencies?: string[];
  due_by?: string; // ISO date string (for non-recurring tasks primarily)

  // Recurrence: list of day integers (e.g., [0, 2, 4] for Mon, Wed, Fri)
  // null or empty list indicates non-recurring.
  recurrence?: number[];

  // For recurring task instances
  recurring_event_id?: string; // ID of the parent recurring event
  instance_date?: string; // The specific date this recurring instance is for

  time_window_start?: string | null; // "HH:MM" (local time for input, UTC for storage if backend handles that)
  time_window_end?: string | null; // "HH:MM"

  is_active?: boolean; // Typically for recurring tasks

  // Fields for scheduled times
  start?: string; // ISO date string, populated by scheduler
  end?: string; // ISO date string, populated by scheduler
}

// Form data type for creating/updating tasks
export interface TaskFormData {
  content: string;
  duration: number; // in minutes
  is_completed?: boolean;
  status?: string; // For task status: "unscheduled", "scheduled", "completed"

  // Fields for one-off nature
  due_by?: Date | null; // Use Date object in form, convert to ISO string for API
  include_time?: boolean; // UI helper for due_by
  dependencies?: string[];

  // Fields for recurring nature
  // This flag will drive the UI to show/hide recurrence fields
  is_recurring_ui_flag?: boolean; // Not sent to backend, just for form logic
  recurrence_days?: number[]; // Array of day numbers (0-6)
  time_window_start?: string | null; // "HH:MM" (local time)
  time_window_end?: string | null; // "HH:MM" (local time)

  // For editing scheduled times directly (if implemented)
  start?: string | Date;
  end?: string | Date;
}

// Response type for task creation
export interface TaskCreationResponse {
  id: string;
  content: string;
  message: string;
}

// Filter types for task listing
export interface TaskFilters {
  task_nature?: "one-off" | "recurring"; // Changed from 'type' to 'task_nature'
  is_completed?: boolean;
}
