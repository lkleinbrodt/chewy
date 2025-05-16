import { addWeeks, startOfWeek, subWeeks } from "date-fns";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { ScheduledTask } from "@/types/schedule";
import { appConfig } from "@/constants/appConfig";
import { handleApiErrorWithToast } from "@/utils/errorUtils";
import scheduleService from "@/services/scheduleService";

/**
 * Hook for managing schedules
 */
export function useSchedule(initialDate = new Date()) {
  const [currentDate, setCurrentDate] = useState<Date>(initialDate);
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Calculate week range based on current date using useMemo to avoid recreating objects
  const { startDate, endDate } = useMemo(() => {
    const { weekStartsOn, weekLength } = appConfig.calendar;
    // Convert weekStartsOn to 0|1|2|3|4|5|6 type that date-fns expects
    const startDay = weekStartsOn as 0 | 1 | 2 | 3 | 4 | 5 | 6;

    const start = startOfWeek(currentDate, { weekStartsOn: startDay });
    const end = new Date(start);
    end.setDate(start.getDate() + weekLength - 1);
    // Set end time to end of day
    end.setHours(23, 59, 59, 999);

    return { startDate: start, endDate: end };
  }, [currentDate]);

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
      setLastSyncTime(new Date());
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
        setIsLoading(true);
        await scheduleService.updateScheduledTask(taskId, updateData);
        // Refresh the schedule after updating
        await fetchSchedule();
        return true;
      } catch (err) {
        const errorMessage = "Failed to update task. Please try again.";
        setError(errorMessage);
        console.error("Error updating scheduled task:", err);
        handleApiErrorWithToast(err, "updating task");
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [fetchSchedule]
  );

  const clearAllScheduledTasks = useCallback(async () => {
    try {
      setIsLoading(true);
      await scheduleService.clearAllScheduledTasks();
      await fetchSchedule();
    } catch (err) {
      console.error("Error clearing scheduled tasks:", err);
      handleApiErrorWithToast(err, "clearing scheduled tasks");
    } finally {
      setIsLoading(false);
    }
  }, [fetchSchedule]);

  // Navigation functions
  const nextWeek = useCallback(() => {
    setCurrentDate((prev) => addWeeks(prev, 1));
  }, []);

  const prevWeek = useCallback(() => {
    setCurrentDate((prev) => subWeeks(prev, 1));
  }, []);

  const goToToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  // Load schedule when date range changes
  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  return {
    currentDate,
    startDate,
    endDate,
    scheduledTasks,
    isLoading,
    isGenerating,
    lastSyncTime,
    error,
    fetchSchedule,
    generateSchedule,
    updateScheduledTask,
    nextWeek,
    prevWeek,
    goToToday,
    clearAllScheduledTasks,
    refreshSchedule: fetchSchedule,
  };
}
