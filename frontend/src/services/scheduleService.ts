import type { ScheduledTask } from "@/types/schedule";
import axiosInstance from "@/utils/axiosInstance";

/**
 * Schedule service for API interactions
 */
const scheduleService = {
  /**
   * Generate a new schedule for the given date range
   */
  generateSchedule: async (
    startDate: Date,
    endDate: Date
  ): Promise<ScheduledTask[]> => {
    try {
      const response = await axiosInstance.post("/schedule/generate", {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      });

      // Convert UTC dates from backend to local timezone
      return response.data.scheduled_tasks.map((task: ScheduledTask) => ({
        ...task,
        start: new Date(task.start), // JS Date constructor automatically converts to local timezone
        end: new Date(task.end), // JS Date constructor automatically converts to local timezone
      }));
    } catch (error) {
      console.error("Error generating schedule:", error);
      throw error;
    }
  },

  /**
   * Get schedule for a date range
   */
  getSchedule: async (
    startDate: Date,
    endDate: Date
  ): Promise<ScheduledTask[]> => {
    try {
      const response = await axiosInstance.get("/schedule", {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        },
      });

      // Convert UTC dates from backend to local timezone
      return response.data.map((task: ScheduledTask) => ({
        ...task,
        start: new Date(task.start), // JS Date constructor automatically converts to local timezone
        end: new Date(task.end), // JS Date constructor automatically converts to local timezone
      }));
    } catch (error) {
      console.error("Error fetching schedule:", error);
      throw error;
    }
  },

  /**
   * Update a scheduled task
   */
  updateScheduledTask: async (
    scheduledTaskId: string,
    updateData: {
      start?: Date;
      end?: Date;
      status?: string;
    }
  ): Promise<{ message: string }> => {
    try {
      // Convert dates to ISO strings if present
      const formattedData = {
        ...updateData,
        start: updateData.start?.toISOString(), // This preserves timezone info
        end: updateData.end?.toISOString(), // This preserves timezone info
      };

      const response = await axiosInstance.put(
        `/schedule/tasks/${scheduledTaskId}`,
        formattedData
      );
      return response.data;
    } catch (error) {
      console.error("Error updating scheduled task:", error);
      throw error;
    }
  },

  clearAllScheduledTasks: async (): Promise<{ message: string }> => {
    try {
      const response = await axiosInstance.delete("/schedule/clear");
      return response.data;
    } catch (error) {
      console.error("Error clearing scheduled tasks:", error);
      throw error;
    }
  },
};

export default scheduleService;
