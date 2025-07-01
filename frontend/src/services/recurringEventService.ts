import type {
  RecurringEvent,
  RecurringEventCreationResponse,
  RecurringEventFilters,
  RecurringEventFormData,
} from "@/types/recurringEvent";

import axiosInstance from "@/utils/axiosInstance";
import { formatRecurringEventForApi } from "@/utils/recurringEventUtils";

/**
 * RecurringEvent service for API interactions
 */
const recurringEventService = {
  /**
   * Get all recurring events with optional filtering
   */
  getRecurringEvents: async (
    filters: RecurringEventFilters = {}
  ): Promise<RecurringEvent[]> => {
    try {
      const response = await axiosInstance.get("/recurring-events", {
        params: filters,
      });
      return response.data;
    } catch (error) {
      console.error("Error fetching recurring events:", error);
      throw error;
    }
  },

  /**
   * Get a single recurring event by ID
   */
  getRecurringEvent: async (
    recurringEventId: string
  ): Promise<RecurringEvent> => {
    const response = await axiosInstance.get(
      `/recurring-events/${recurringEventId}`
    );
    return response.data;
  },

  /**
   * Create a new recurring event
   */
  createRecurringEvent: async (
    recurringEventData: RecurringEventFormData
  ): Promise<RecurringEventCreationResponse> => {
    const formattedData = formatRecurringEventForApi(recurringEventData);
    const response = await axiosInstance.post(
      "/recurring-events",
      formattedData
    );
    return response.data;
  },

  /**
   * Update an existing recurring event
   */
  updateRecurringEvent: async (
    recurringEventId: string,
    recurringEventData: RecurringEventFormData
  ): Promise<{ message: string }> => {
    const formattedData = formatRecurringEventForApi(recurringEventData);
    const response = await axiosInstance.put(
      `/recurring-events/${recurringEventId}`,
      formattedData
    );
    return response.data;
  },

  /**
   * Delete a recurring event
   */
  deleteRecurringEvent: async (
    recurringEventId: string
  ): Promise<{ message: string }> => {
    const response = await axiosInstance.delete(
      `/recurring-events/${recurringEventId}`
    );
    return response.data;
  },

  /**
   * Reset tasks for a recurring event (delete and recreate all tasks)
   */
  resetRecurringEventTasks: async (
    recurringEventId: string,
    startDate: string,
    endDate: string
  ): Promise<{ message: string }> => {
    const response = await axiosInstance.post(
      `/recurring-events/${recurringEventId}/reset-tasks`,
      {
        start_date: startDate,
        end_date: endDate,
      }
    );
    return response.data;
  },
};

export default recurringEventService;
