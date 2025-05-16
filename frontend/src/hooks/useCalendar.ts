import { addWeeks, startOfWeek, subWeeks } from "date-fns";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AxiosError } from "axios";
import type { CalendarEvent } from "@/types/calendar";
import { appConfig } from "@/constants/appConfig";
import calendarService from "@/services/calendarApi";
import { formatEventForApi } from "@/utils/calendarUtils";
import { handleApiErrorWithToast } from "@/utils/errorUtils";

export function useCalendar(initialDate = new Date()) {
  const [currentDate, setCurrentDate] = useState<Date>(initialDate);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
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
      return { success: true };
    } catch (err) {
      // Check for the special calendar directory error
      const axiosError = err as AxiosError<{ error: string; message: string }>;
      if (axiosError.response?.data?.error === "CALENDAR_DIR_NOT_SET") {
        return {
          success: false,
          needsDirectorySetup: true,
          message:
            axiosError.response.data.message ||
            "Calendar directory not configured",
        };
      }

      const errorMessage =
        err instanceof Error ? err.message : "Failed to synchronize calendar";
      setError(errorMessage);
      handleApiErrorWithToast(err, "synchronizing calendar");
      return { success: false };
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
    fetchEvents();
  }, [fetchEvents]);

  return {
    currentDate,
    startDate,
    endDate,
    events,
    loading,
    error,
    isSyncing,
    lastSyncTime,
    nextWeek,
    prevWeek,
    goToToday,
    syncCalendar,
    updateEvent,
    refreshEvents: fetchEvents,
  };
}
