import type { Objectives } from "@/types/objectives";
import axiosInstance from "@/utils/axiosInstance";

const OBJECTIVES_STORAGE_KEY = "scheduler_objectives";

const defaultObjectives: Objectives = {
  FREE_AFTERNOON: { enabled: true, weight: 10 },
  FREE_MORNING: { enabled: false, weight: 10 },
  EVEN_WORKLOAD: { enabled: true, weight: 10 },
};

const settingsService = {
  getCalendarDir: async () => {
    try {
      const response = await axiosInstance.get("/settings/calendar-dir");
      return response.data;
    } catch (error) {
      console.error("Error getting calendar directory:", error);
      throw error;
    }
  },

  setCalendarDir: async (calendarDir: string) => {
    try {
      const response = await axiosInstance.post("/settings/calendar-dir", {
        calendar_dir: calendarDir,
      });
      return response.data;
    } catch (error) {
      console.error("Error setting calendar directory:", error);
      throw error;
    }
  },

  // Objective related functions
  getObjectives: (): Objectives => {
    const storedObjectives = localStorage.getItem(OBJECTIVES_STORAGE_KEY);
    if (storedObjectives) {
      return JSON.parse(storedObjectives);
    }
    return defaultObjectives;
  },

  setObjectives: (objectives: Objectives): void => {
    localStorage.setItem(OBJECTIVES_STORAGE_KEY, JSON.stringify(objectives));
  },

  resetObjectives: (): void => {
    localStorage.setItem(
      OBJECTIVES_STORAGE_KEY,
      JSON.stringify(defaultObjectives)
    );
  },
};

export default settingsService;
