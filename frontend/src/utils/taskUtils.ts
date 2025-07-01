import type { Task, TaskFormData } from "@/types/task";

/**
 * Convert form data to API format
 */
export const formatTaskForApi = (formData: TaskFormData) => {
  const isRecurring =
    formData.is_recurring_ui_flag ||
    (formData.recurrence_days && formData.recurrence_days.length > 0);

  // it should never be recurring, this is deprecated
  if (isRecurring) {
    throw new Error("Recurring tasks are deprecated");
  }

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
