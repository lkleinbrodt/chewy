import { addWeeks, startOfWeek, subWeeks } from "date-fns";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { CalendarEvent } from "@/types/calendar";
import type { ScheduledTask } from "@/types/schedule";
import { appConfig } from "@/constants/appConfig";
import calendarService from "@/services/calendarApi";
import { formatEventForApi } from "@/utils/calendarUtils";
import { handleApiErrorWithToast } from "@/utils/errorUtils";
import scheduleService from "@/services/scheduleService";

export function useCalendar(initialDate = new Date()) {
  const [currentDate, setCurrentDate] = useState<Date>(initialDate);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);

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

  // Fetch events for current week
  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      const data = await calendarService.getEvents(startDate, endDate);
      setEvents(data);
      setError(null);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch events";
      setError(errorMessage);
      handleApiErrorWithToast(err, "fetching events");
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  // Fetch scheduled tasks for current week
  const fetchSchedule = useCallback(async () => {
    try {
      setLoading(true);
      const tasks = await scheduleService.getSchedule(startDate, endDate);
      setScheduledTasks(tasks);
      setError(null);
    } catch (err) {
      // Don't override the error if it's from fetching events
      if (!error) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch schedule";
        setError(errorMessage);
        handleApiErrorWithToast(err, "fetching schedule");
      }
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, error]);

  // Generate a new schedule
  const generateSchedule = async () => {
    try {
      setIsGenerating(true);
      const newTasks = await scheduleService.generateSchedule(
        startDate,
        endDate
      );
      setScheduledTasks(newTasks);
      setError(null);
      return true;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to generate schedule";
      setError(errorMessage);
      handleApiErrorWithToast(err, "generating schedule");
      return false;
    } finally {
      setIsGenerating(false);
    }
  };

  // Update a scheduled task
  const updateScheduledTask = async (
    taskId: string,
    updateData: { start?: Date; end?: Date; status?: string }
  ) => {
    try {
      setLoading(true);
      await scheduleService.updateScheduledTask(taskId, updateData);
      await fetchSchedule(); // Refresh tasks after update
      return true;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to update task";
      setError(errorMessage);
      handleApiErrorWithToast(err, "updating task");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Navigate to next week
  const nextWeek = () => {
    setCurrentDate((prev) => addWeeks(prev, 1));
  };

  // Navigate to previous week
  const prevWeek = () => {
    setCurrentDate((prev) => subWeeks(prev, 1));
  };

  // Go to today
  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Synchronize calendar with JSON files
  const syncCalendar = async () => {
    try {
      setIsSyncing(true);
      await calendarService.syncCalendar();
      await fetchEvents(); // Refresh events after sync
      setLastSyncTime(new Date());
      setError(null);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to synchronize calendar";
      setError(errorMessage);
      handleApiErrorWithToast(err, "synchronizing calendar");
    } finally {
      setIsSyncing(false);
    }
  };

  // Update Chewy-managed event
  const updateEvent = async (
    eventId: string,
    eventData: {
      subject?: string;
      start?: Date;
      end?: Date;
    }
  ) => {
    try {
      setLoading(true);
      const formattedData = formatEventForApi(eventData);
      await calendarService.updateEvent(eventId, formattedData);
      await fetchEvents(); // Refresh events after update
      return true;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to update event";
      setError(errorMessage);
      handleApiErrorWithToast(err, "updating event");
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Fetch data when week range changes
  useEffect(() => {
    const loadData = async () => {
      await fetchEvents();
      await fetchSchedule();
    };
    loadData();
  }, [fetchEvents, fetchSchedule]);

  return {
    currentDate,
    startDate,
    endDate,
    events,
    scheduledTasks,
    loading,
    error,
    isSyncing,
    isGenerating,
    lastSyncTime,
    nextWeek,
    prevWeek,
    goToToday,
    syncCalendar,
    generateSchedule,
    updateEvent,
    updateScheduledTask,
    refreshEvents: fetchEvents,
    refreshSchedule: fetchSchedule,
  };
}
