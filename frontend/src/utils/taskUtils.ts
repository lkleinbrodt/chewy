import type { Task, TaskFormData } from "@/types/task";

/**
 * Convert form data to API format
 */
export const formatTaskForApi = (formData: TaskFormData) => {
  const isRecurring =
    formData.is_recurring_ui_flag ||
    (formData.recurrence_days && formData.recurrence_days.length > 0);

  // Common fields
  const commonFields = {
    content: formData.content,
    duration: Number(formData.duration),
    ...(formData.status && { status: formData.status }),
    ...(formData.start && {
      start:
        formData.start instanceof Date
          ? formData.start.toISOString()
          : formData.start,
    }),
    ...(formData.end && {
      end:
        formData.end instanceof Date
          ? formData.end.toISOString()
          : formData.end,
    }),
  };

  if (isRecurring) {
    // Handle recurring task fields
    let time_window_start: string | null = null;
    let time_window_end: string | null = null;

    // Convert local time strings to UTC time strings
    if (formData.time_window_start) {
      const [hours, minutes] = formData.time_window_start
        .split(":")
        .map(Number);
      const startDate = new Date();
      startDate.setHours(hours, minutes, 0, 0);

      // Format as HH:MM but in UTC
      const utcHours = startDate.getUTCHours();
      const utcMinutes = startDate.getUTCMinutes();
      time_window_start = `${utcHours.toString().padStart(2, "0")}:${utcMinutes
        .toString()
        .padStart(2, "0")}`;
    }

    if (formData.time_window_end) {
      const [hours, minutes] = formData.time_window_end.split(":").map(Number);
      const endDate = new Date();
      endDate.setHours(hours, minutes, 0, 0);

      // Format as HH:MM but in UTC
      const utcHours = endDate.getUTCHours();
      const utcMinutes = endDate.getUTCMinutes();
      time_window_end = `${utcHours.toString().padStart(2, "0")}:${utcMinutes
        .toString()
        .padStart(2, "0")}`;
    }

    return {
      ...commonFields,
      recurrence: formData.recurrence_days || [],
      time_window_start,
      time_window_end,
      due_by: null,
      dependencies: [],
    };
  } else {
    // Handle one-off task fields
    const dueDate = formData.due_by instanceof Date ? formData.due_by : null;

    return {
      ...commonFields,
      dependencies: formData.dependencies || [],
      due_by: dueDate?.toISOString() || null,
      recurrence: [],
      time_window_start: null,
      time_window_end: null,
    };
  }
};

/**
 * Format API data for form
 */
export const formatTaskForForm = (apiData: Task): TaskFormData => {
  // Common fields
  const commonFields = {
    content: apiData.content,
    duration: apiData.duration,
    is_completed: apiData.is_completed,
    time_window_start: apiData.time_window_start,
    time_window_end: apiData.time_window_end,
    start: apiData.start,
    end: apiData.end,
  };

  const isRecurring = apiData.recurrence && apiData.recurrence.length > 0;

  if (isRecurring) {
    // Convert UTC time strings back to local time
    let localTimeWindowStart = "";
    let localTimeWindowEnd = "";

    if (apiData.time_window_start) {
      // Parse UTC time string and convert to local time
      const [hours, minutes] = apiData.time_window_start.split(":").map(Number);
      const date = new Date();
      // Set hours and minutes in UTC
      date.setUTCHours(hours, minutes, 0, 0);
      // Get local hours and minutes
      const localHours = date.getHours();
      const localMinutes = date.getMinutes();
      // Format as HH:MM
      localTimeWindowStart = `${localHours
        .toString()
        .padStart(2, "0")}:${localMinutes.toString().padStart(2, "0")}`;
    }

    if (apiData.time_window_end) {
      // Parse UTC time string and convert to local time
      const [hours, minutes] = apiData.time_window_end.split(":").map(Number);
      const date = new Date();
      // Set hours and minutes in UTC
      date.setUTCHours(hours, minutes, 0, 0);
      // Get local hours and minutes
      const localHours = date.getHours();
      const localMinutes = date.getMinutes();
      // Format as HH:MM
      localTimeWindowEnd = `${localHours
        .toString()
        .padStart(2, "0")}:${localMinutes.toString().padStart(2, "0")}`;
    }

    return {
      ...commonFields,
      is_recurring_ui_flag: true,
      recurrence_days: apiData.recurrence || [],
      time_window_start: localTimeWindowStart || null,
      time_window_end: localTimeWindowEnd || null,
    };
  } else {
    // One-off task
    const dueByDate = apiData.due_by ? new Date(apiData.due_by) : null;
    // Check if time is set to anything other than around midnight (allowing for small variations)
    const hasSpecificTime = dueByDate
      ? dueByDate.getHours() !== 0 || dueByDate.getMinutes() > 5
      : false;

    return {
      ...commonFields,
      is_recurring_ui_flag: false,
      dependencies: apiData.dependencies || [],
      due_by: dueByDate,
      include_time: hasSpecificTime,
    };
  }
};

/**
 * Check if a task is blocked by incomplete dependencies
 */
export const isTaskBlocked = (task: Task, allTasks: Task[]): boolean => {
  if (!task.dependencies || task.dependencies.length === 0) {
    return false;
  }

  return task.dependencies.some((depId) => {
    const dependencyTask = allTasks.find((t) => t.id === depId);
    return dependencyTask && !dependencyTask.is_completed;
  });
};

/**
 * Get task status label
 */
export const getTaskStatus = (
  task: Task,
  allTasks: Task[]
): {
  label: string;
  color: string;
} => {
  if (task.is_completed) {
    return { label: "Completed", color: "bg-green-400" };
  }

  if (isTaskBlocked(task, allTasks)) {
    return { label: "Blocked", color: "bg-amber-400" };
  }

  if (task.due_by) {
    const dueDate = new Date(task.due_by);
    const today = new Date();

    if (dueDate < today) {
      return { label: "Overdue", color: "bg-red-400" };
    }
  }

  if (task.recurrence && task.recurrence.length > 0) {
    return { label: "Recurring", color: "bg-primary-light" };
  }

  return { label: "Active", color: "bg-secondary" };
};

/**
 * Format duration in minutes to human-readable string
 */
export const formatDuration = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (hours === 0) {
    return `${mins}m`;
  } else if (mins === 0) {
    return `${hours}h`;
  } else {
    return `${hours}h ${mins}m`;
  }
};

/**
 * Format task schedule information
 */
export const formatTaskSchedule = (task: Task): string => {
  const daysOfWeek = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  if (task.recurrence && task.recurrence.length > 0) {
    if (task.recurrence.length === 7) return "Daily";
    return task.recurrence.map((dayIndex) => daysOfWeek[dayIndex]).join(", ");
  }

  return task.due_by ? new Date(task.due_by).toLocaleDateString() : "N/A";
};

/**
 * Check if adding a dependency would create a circular dependency
 */
export const wouldCreateCircularDependency = (
  taskId: string,
  dependencyId: string,
  allTasks: Task[]
): boolean => {
  const visited = new Set<string>();
  return checkForCircularPath(dependencyId, [taskId], allTasks, visited);
};

/**
 * Helper function to check for circular dependencies
 */
const checkForCircularPath = (
  currentTaskId: string,
  targetTaskIds: string[],
  allTasks: Task[],
  visited: Set<string>
): boolean => {
  if (targetTaskIds.includes(currentTaskId)) {
    return true;
  }

  if (visited.has(currentTaskId)) {
    return false;
  }

  visited.add(currentTaskId);

  const currentTask = allTasks.find((task) => task.id === currentTaskId);
  if (
    !currentTask ||
    !currentTask.dependencies ||
    currentTask.dependencies.length === 0
  ) {
    return false;
  }

  return currentTask.dependencies.some((depId) =>
    checkForCircularPath(depId, targetTaskIds, allTasks, visited)
  );
};
