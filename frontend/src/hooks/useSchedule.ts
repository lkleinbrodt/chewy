import { useCallback, useEffect, useState } from "react";

import type { ScheduledTask } from "@/types/schedule";
import { handleApiErrorWithToast } from "@/utils/errorUtils";
import scheduleService from "@/services/scheduleService";

/**
 * Hook for managing schedules
 */
export function useSchedule(
  initialStartDate = new Date(),
  initialEndDate = new Date(new Date().setDate(new Date().getDate() + 7))
) {
  const [startDate, setStartDate] = useState<Date>(initialStartDate);
  const [endDate, setEndDate] = useState<Date>(initialEndDate);
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch the schedule for current date range
  const fetchSchedule = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const tasks = await scheduleService.getSchedule(startDate, endDate);
      setScheduledTasks(tasks);
    } catch (err) {
      const errorMessage = "Failed to load schedule. Please try again.";
      setError(errorMessage);
      console.error("Error fetching schedule:", err);
      handleApiErrorWithToast(err, "fetching schedule");
    } finally {
      setIsLoading(false);
    }
  }, [startDate, endDate]);

  // Generate a new schedule
  const generateSchedule = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const newTasks = await scheduleService.generateSchedule(
        startDate,
        endDate
      );
      setScheduledTasks(newTasks);
      return true;
    } catch (err) {
      const errorMessage = "Failed to generate schedule. Please try again.";
      setError(errorMessage);
      console.error("Error generating schedule:", err);
      handleApiErrorWithToast(err, "generating schedule");
      return false;
    } finally {
      setIsGenerating(false);
    }
  }, [startDate, endDate]);

  // Update a scheduled task
  const updateScheduledTask = useCallback(
    async (
      taskId: string,
      updateData: { start?: Date; end?: Date; status?: string }
    ) => {
      try {
        await scheduleService.updateScheduledTask(taskId, updateData);
        // Refresh the schedule after updating
        fetchSchedule();
        return true;
      } catch (err) {
        const errorMessage = "Failed to update task. Please try again.";
        setError(errorMessage);
        console.error("Error updating scheduled task:", err);
        handleApiErrorWithToast(err, "updating task");
        return false;
      }
    },
    [fetchSchedule]
  );

  const clearAllScheduledTasks = useCallback(async () => {
    try {
      await scheduleService.clearAllScheduledTasks();
      fetchSchedule();
    } catch (err) {
      console.error("Error clearing scheduled tasks:", err);
      handleApiErrorWithToast(err, "clearing scheduled tasks");
    }
  }, [fetchSchedule]);

  // Navigation functions
  const nextWeek = useCallback(() => {
    setStartDate(new Date(startDate.getTime() + 7 * 24 * 60 * 60 * 1000));
    setEndDate(new Date(endDate.getTime() + 7 * 24 * 60 * 60 * 1000));
  }, [startDate, endDate]);

  const prevWeek = useCallback(() => {
    setStartDate(new Date(startDate.getTime() - 7 * 24 * 60 * 60 * 1000));
    setEndDate(new Date(endDate.getTime() - 7 * 24 * 60 * 60 * 1000));
  }, [startDate, endDate]);

  const goToToday = useCallback(() => {
    const today = new Date();
    setStartDate(today);
    setEndDate(new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000));
  }, []);

  // Load schedule when date range changes
  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  return {
    startDate,
    endDate,
    scheduledTasks,
    isLoading,
    isGenerating,
    error,
    fetchSchedule,
    generateSchedule,
    updateScheduledTask,
    nextWeek,
    prevWeek,
    goToToday,
    clearAllScheduledTasks,
  };
}
