import { useCallback, useState } from "react";

import scheduleService from "@/services/scheduleService";

/**
 * Hook for managing schedule generation state
 * Simplified to only handle the schedule generation process
 */
export function useSchedule() {
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const generateSchedule = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const updatedTasks = await scheduleService.generateSchedule();
      return { success: true, updatedTasks };
    } catch (err) {
      const errorMessage = "Failed to generate schedule. Please try again.";
      setError(errorMessage);
      console.error("Error generating schedule:", err);
      return { success: false, updatedTasks: null };
    } finally {
      setIsGenerating(false);
    }
  }, []);

  return {
    isGenerating,
    error,
    generateSchedule,
  };
}
