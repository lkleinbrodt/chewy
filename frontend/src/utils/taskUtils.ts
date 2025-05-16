import type {
  OneOffTask,
  OneOffTaskFormData,
  RecurringTask,
  RecurringTaskFormData,
  Task,
} from "@/types/task";

/**
 * Convert form data to API format
 */
export const formatTaskForApi = (
  formData: OneOffTaskFormData | RecurringTaskFormData
) => {
  if (formData.task_type === "one-off") {
    // Create a copy of the due_by date for manipulation
    const dueDate = new Date(formData.due_by);

    // If the user did not include a specific time, set it to 12:01 AM (already set in the form)
    // The date is in local time, so convert to UTC for the backend

    return {
      content: formData.content,
      duration: Number(formData.duration),
      dependencies: formData.dependencies || [],
      due_by: dueDate.toISOString(), // This automatically converts to UTC
      task_type: "one-off" as const,
      is_completed: formData.is_completed || false,
      time_window_start: formData.time_window_start || null,
      time_window_end: formData.time_window_end || null,
    };
  } else {
    // Recurring task
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
      content: formData.content,
      duration: Number(formData.duration),
      task_type: "recurring" as const,
      recurrence: formData.recurrence,
      time_window_start,
      time_window_end,
      is_active: formData.is_active || true,
    };
  }
};

/**
 * Format API data for form
 */
export const formatTaskForForm = (
  apiData: Task
): OneOffTaskFormData | RecurringTaskFormData => {
  const commonFields = {
    id: apiData.id,
    content: apiData.content,
    duration: apiData.duration,
    task_type: apiData.task_type,
    time_window_start: apiData.time_window_start,
    time_window_end: apiData.time_window_end,
  };

  if (apiData.task_type === "one-off") {
    const oneOffTask = apiData as OneOffTask;
    const dueByDate = new Date(oneOffTask.due_by);
    // Check if time is set to anything other than around midnight (allowing for small variations)
    const hasSpecificTime =
      dueByDate.getHours() !== 0 || dueByDate.getMinutes() > 5;

    return {
      ...commonFields,
      task_type: "one-off" as const,
      dependencies: oneOffTask.dependencies || [],
      due_by: dueByDate,
      include_time: hasSpecificTime,
      is_completed: oneOffTask.is_completed || false,
    };
  } else {
    // Recurring task
    const recurringTask = apiData as RecurringTask;

    // Convert UTC time strings back to local time
    let localTimeWindowStart = "";
    let localTimeWindowEnd = "";

    if (recurringTask.time_window_start) {
      // Parse UTC time string and convert to local time
      const [hours, minutes] = recurringTask.time_window_start
        .split(":")
        .map(Number);
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

    if (recurringTask.time_window_end) {
      // Parse UTC time string and convert to local time
      const [hours, minutes] = recurringTask.time_window_end
        .split(":")
        .map(Number);
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
      task_type: "recurring" as const,
      recurrence: recurringTask.recurrence,
      time_window_start: localTimeWindowStart,
      time_window_end: localTimeWindowEnd,
      is_active: recurringTask.is_active || true,
    };
  }
};

/**
 * Check if a task is blocked by incomplete dependencies
 */
export const isTaskBlocked = (task: Task, allTasks: Task[]): boolean => {
  if (
    task.task_type !== "one-off" ||
    !task.dependencies ||
    task.dependencies.length === 0
  ) {
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

  if (task.task_type === "one-off") {
    if (isTaskBlocked(task, allTasks)) {
      return { label: "Blocked", color: "bg-amber-400" };
    }

    const dueDate = new Date(task.due_by);
    const today = new Date();

    if (dueDate < today) {
      return { label: "Overdue", color: "bg-red-400" };
    }
  }

  if (task.task_type === "recurring") {
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
 * Format due date or recurrence pattern to human-readable string
 */
export const formatTaskSchedule = (task: Task): string => {
  if (task.task_type === "one-off") {
    return new Date(task.due_by).toLocaleDateString();
  } else {
    const { recurrence } = task;

    if (recurrence.type === "daily") {
      return "Daily";
    } else if (recurrence.type === "weekly") {
      return "Weekly";
    } else if (recurrence.type === "custom" && recurrence.days) {
      const dayMap: Record<string, string> = {
        mon: "Monday",
        tue: "Tuesday",
        wed: "Wednesday",
        thu: "Thursday",
        fri: "Friday",
        sat: "Saturday",
        sun: "Sunday",
      };

      return recurrence.days.map((day) => dayMap[day] || day).join(", ");
    }

    return "Custom schedule";
  }
};

/**
 * Check for circular dependencies
 * Returns true if adding the dependency would create a circular reference
 */
export const wouldCreateCircularDependency = (
  taskId: string,
  dependencyId: string,
  allTasks: Task[]
): boolean => {
  // If we're trying to make a task depend on itself, that's circular
  if (taskId === dependencyId) return true;

  // Find the dependency task
  const dependencyTask = allTasks.find((t) => t.id === dependencyId);

  // If dependency doesn't exist or isn't a one-off task, no circular dependency
  if (!dependencyTask || dependencyTask.task_type !== "one-off") return false;

  // If the dependency has no dependencies of its own, no circular dependency
  if (
    !dependencyTask.dependencies ||
    dependencyTask.dependencies.length === 0
  ) {
    return false;
  }

  // Check if any of the dependency's dependencies would create a circular reference
  return checkForCircularPath(
    taskId,
    dependencyTask.dependencies,
    allTasks,
    new Set()
  );
};

/**
 * Helper function to check for circular paths in dependencies
 */
const checkForCircularPath = (
  originalTaskId: string,
  dependencies: string[],
  allTasks: Task[],
  visited: Set<string>
): boolean => {
  for (const depId of dependencies) {
    // If we've seen this task before in this path, we have a cycle
    if (visited.has(depId)) continue;

    // If the dependency is the original task, we have a cycle
    if (depId === originalTaskId) return true;

    // Find this dependency
    const depTask = allTasks.find((t) => t.id === depId);
    if (!depTask || depTask.task_type !== "one-off") continue;

    // If this dependency has its own dependencies, check those too
    if (depTask.dependencies && depTask.dependencies.length > 0) {
      const newVisited = new Set(visited);
      newVisited.add(depId);
      if (
        checkForCircularPath(
          originalTaskId,
          depTask.dependencies,
          allTasks,
          newVisited
        )
      ) {
        return true;
      }
    }
  }

  return false;
};
