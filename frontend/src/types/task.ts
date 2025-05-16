// Task types

// Common task interface
export interface BaseTask {
  id: string;
  content: string;
  duration: number; // in minutes
  is_completed: boolean;
  task_type: "one-off" | "recurring";
  created_at: string;
  updated_at: string;
  time_window_start: string | null; // Format: "HH:MM"
  time_window_end: string | null; // Format: "HH:MM"
}

// One-off task specific fields
export interface OneOffTask extends BaseTask {
  task_type: "one-off";
  due_by: string;
  dependencies: string[];
}

// Recurrence pattern specification
export interface RecurrencePattern {
  type: "daily" | "weekly";
  days?: string[]; // For weekly recurrence, contains days of week
}

// Recurring task specific fields
export interface RecurringTask extends BaseTask {
  task_type: "recurring";
  recurrence: RecurrencePattern;
  is_active: boolean;
  recurring_event_id?: string;
  instance_date?: string;
}

// Union type for all task types
export type Task = OneOffTask | RecurringTask;

// Form data types for creating/updating tasks
export interface TaskFormData {
  content: string;
  duration: number; // in minutes
  task_type: "one-off" | "recurring";
  is_completed?: boolean;
  time_window_start?: string | null;
  time_window_end?: string | null;
}

export interface OneOffTaskFormData extends TaskFormData {
  task_type: "one-off";
  due_by: Date;
  include_time?: boolean;
  dependencies?: string[];
}

export interface RecurringTaskFormData extends TaskFormData {
  task_type: "recurring";
  recurrence: RecurrencePattern;
  is_active?: boolean;
}

// Response type for task creation
export interface TaskCreationResponse {
  id: string;
  content: string;
  message: string;
}

// Filter types for task listing
export interface TaskFilters {
  type?: "one-off" | "recurring";
  is_completed?: boolean;
}
