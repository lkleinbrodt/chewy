import type { Task } from "@/types/task";
import axiosInstance from "@/utils/axiosInstance";
import settingsService from "./settingsService";

export interface UnscheduledTaskInfo {
  task: Task;
  reason: string;
}

/**
 * Schedule service for API interactions
 */
const scheduleService = {
  /**
   * Generate a new schedule
   * Calls the API to update tasks with start and end times
   */
  generateSchedule: async (): Promise<{
    scheduled_tasks: Task[];
    unscheduled_tasks: UnscheduledTaskInfo[];
    status_message: string;
    message: string;
  }> => {
    try {
      const objectives = settingsService.getObjectives();

      // Use start of today to avoid timezone issues and past dates
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const response = await axiosInstance.post("/schedule/generate", {
        start_date: today.toISOString(),
        end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
        objectives, // Include objectives from settings
      });

      // Convert string dates to Date objects for scheduled tasks
      const scheduled_tasks = response.data.scheduled_tasks.map(
        (task: Task) => ({
          ...task,
          start: task.start ? new Date(task.start) : undefined,
          end: task.end ? new Date(task.end) : undefined,
        })
      );

      // Convert string dates for unscheduled tasks' nested task objects
      const unscheduled_tasks = (response.data.unscheduled_tasks || []).map(
        (info: { task: Task; reason: string }) => ({
          ...info,
          task: {
            ...info.task,
            start: info.task.start ? new Date(info.task.start) : undefined,
            end: info.task.end ? new Date(info.task.end) : undefined,
          },
        })
      );

      return {
        ...response.data,
        scheduled_tasks,
        unscheduled_tasks,
      };
    } catch (error) {
      console.error("Error generating schedule:", error);
      throw error;
    }
  },

  /**
   * Clear schedule data from all tasks
   */
  clearScheduleDataFromTasks: async (): Promise<{ message: string }> => {
    try {
      const response = await axiosInstance.delete("/schedule/clear");
      return response.data;
    } catch (error) {
      console.error("Error clearing schedule data from tasks:", error);
      throw error;
    }
  },
};

export default scheduleService;
