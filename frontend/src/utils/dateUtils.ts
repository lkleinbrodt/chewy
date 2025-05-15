import {
  eachDayOfInterval,
  format,
  getHours,
  getMinutes,
  isSameDay,
  isValid,
  parseISO,
  startOfWeek,
} from "date-fns";

import type { CalendarEvent } from "@/types/calendar";
import { appConfig } from "@/constants/appConfig";

/**
 * Utility functions for handling dates and times in local timezone
 */
export const dateUtils = {
  parseUtcISOString: (isoString: string | null | undefined): Date | null => {
    if (!isoString) return null;
    const parsedDate = parseISO(isoString);
    return isValid(parsedDate) ? parsedDate : null;
  },

  formatToLocalDate: (
    date: Date | null | undefined,
    formatStr: string = "PP"
  ): string => {
    // PP = Oct 20, 2023
    if (!date || !isValid(date)) return "";
    return format(date, formatStr);
  },

  formatToLocalTime: (
    date: Date | null | undefined,
    formatStr: string = "p"
  ): string => {
    // p = 12:30 PM
    if (!date || !isValid(date)) return "";
    return format(date, formatStr);
  },

  formatToLocalDateTime: (
    date: Date | null | undefined,
    formatStr: string = "PP p"
  ): string => {
    if (!date || !isValid(date)) return "";
    return format(date, formatStr);
  },

  formatToIsoUTC: (date: Date | null | undefined): string | null => {
    if (!date || !isValid(date)) return null;
    return date.toISOString();
  },

  getNow: (): Date => {
    // Return the current date in local timezone
    return new Date();
  },
};

// Format date range for display (e.g., "May 10-14, 2025" for Mon-Fri)
export const formatDateRange = (start: Date, end: Date): string => {
  if (start.getMonth() === end.getMonth()) {
    return `${format(start, "MMM d")}-${format(end, "d, yyyy")}`;
  }
  return `${format(start, "MMM d")} - ${format(end, "MMM d, yyyy")}`;
};

// Get array of days for the current week view
export const getWeekDays = (currentDate: Date): Date[] => {
  const { weekStartsOn, weekLength } = appConfig.calendar;

  // Convert weekStartsOn to 0|1|2|3|4|5|6 type that date-fns expects
  const startDay = weekStartsOn as 0 | 1 | 2 | 3 | 4 | 5 | 6;

  const start = startOfWeek(currentDate, { weekStartsOn: startDay });
  const end = new Date(start);
  end.setDate(start.getDate() + weekLength - 1);

  return eachDayOfInterval({ start, end });
};

// Get events for a specific day
export const getEventsForDay = (
  events: CalendarEvent[] | null | undefined,
  date: Date
): CalendarEvent[] => {
  // If events is null, undefined, or not an array, return empty array
  if (!events || !Array.isArray(events)) {
    return [];
  }

  return events.filter((event) => {
    const eventDate = new Date(event.start);
    return isSameDay(eventDate, date);
  });
};

// Interface for items that have start and end times
interface TimeSlotItem {
  start: string;
  end: string;
  [key: string]: unknown;
}

/**
 * Calculate position and height for event or task display
 * This function converts time-based positions to percentage-based CSS positions
 */
export const calculateEventPosition = (
  item: TimeSlotItem,
  dayStartHour?: number,
  dayEndHour?: number
): { top: string; height: string } => {
  const { start: configStartHour, end: configEndHour } =
    appConfig.calendar.workingHours;

  // Use provided hours or fall back to config values
  const startHour = dayStartHour !== undefined ? dayStartHour : configStartHour;
  const endHour = dayEndHour !== undefined ? dayEndHour : configEndHour;

  const startTime = new Date(item.start);
  const endTime = new Date(item.end);

  // Calculate with precision to minutes
  const eventStartHour = getHours(startTime) + getMinutes(startTime) / 60;
  const eventEndHour = getHours(endTime) + getMinutes(endTime) / 60;

  // Total visible hours in the day view
  const totalVisibleHours = endHour - startHour;

  // Calculate position as percentage of the total day height
  let topPercentage = ((eventStartHour - startHour) / totalVisibleHours) * 100;
  let heightPercentage =
    ((eventEndHour - eventStartHour) / totalVisibleHours) * 100;

  // Handle events that start before the visible range
  if (eventStartHour < startHour) {
    heightPercentage = ((eventEndHour - startHour) / totalVisibleHours) * 100;
    topPercentage = 0;
  }

  // Handle events that end after the visible range
  if (eventEndHour > endHour) {
    heightPercentage =
      ((endHour - Math.max(startHour, eventStartHour)) / totalVisibleHours) *
      100;
  }

  // Handle events completely outside the visible range
  if (eventStartHour >= endHour || eventEndHour <= startHour) {
    // For events outside the range, we'll show a minimal indicator
    // at the top or bottom edge of the visible area
    const minimumHeightPercentage = 4; // Minimum height as percentage of day height

    if (eventEndHour <= startHour) {
      // Event ends before visible range - show at top
      topPercentage = 0;
      heightPercentage = minimumHeightPercentage;
    } else {
      // Event starts after visible range - show at bottom
      topPercentage = 100 - minimumHeightPercentage;
      heightPercentage = minimumHeightPercentage;
    }
  }

  // Ensure minimum height for very short events
  const minimumHeight = 4; // Minimum height percentage
  heightPercentage = Math.max(heightPercentage, minimumHeight);

  return {
    top: `${topPercentage}%`,
    height: `${heightPercentage}%`,
  };
};

// Convert string time to Date object
export const timeStringToDate = (
  timeString: string,
  baseDate: Date
): Date | null => {
  if (!timeString) return null;

  const [hours, minutes] = timeString.split(":").map(Number);
  if (isNaN(hours) || isNaN(minutes)) return null;

  const result = new Date(baseDate);
  result.setHours(hours, minutes, 0, 0);

  return result;
};
