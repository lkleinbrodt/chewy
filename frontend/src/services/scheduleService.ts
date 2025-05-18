import type { Task } from "@/types/task";
import axiosInstance from "@/utils/axiosInstance";

/**
 * Schedule service for API interactions
 */
const scheduleService = {
  /**
   * Generate a new schedule
   * Calls the API to update tasks with start and end times
   */
  generateSchedule: async (): Promise<Task[]> => {
    try {
      const response = await axiosInstance.post("/schedule", {
        start_date: new Date().toISOString(),
        end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
      });

      // Convert string dates to Date objects
      return response.data.tasks.map((task: Task) => ({
        ...task,
        start: task.start ? new Date(task.start) : undefined,
        end: task.end ? new Date(task.end) : undefined,
      })) as Task[];
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
