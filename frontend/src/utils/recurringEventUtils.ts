import type { RecurringEventFormData } from "@/types/recurringEvent";
import { dateUtils } from "@/utils/dateUtils";

/**
 * Format a recurring event form data object for the API
 */
export const formatRecurringEventForApi = (
  formData: RecurringEventFormData
): Record<string, unknown> => {
  return {
    content: formData.content,
    duration: formData.duration,
    recurrence: formData.recurrence_days, // Backend expects 'recurrence' instead of 'recurrence_days'
    time_window_start: formData.time_window_start || null,
    time_window_end: formData.time_window_end || null,
  };
};

/**
 * Format the recurring pattern into readable text
 */
export const formatRecurrencePattern = (recurrence: number[]): string => {
  if (!recurrence || recurrence.length === 0) {
    return "Not recurring";
  }

  // Sort the days to ensure they're in order
  const sortedDays = [...recurrence].sort((a, b) => a - b);

  // Day names starting with Monday as 0
  const dayNames = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];

  // Special cases for common patterns
  if (sortedDays.length === 7) {
    return "Every day";
  }

  if (
    sortedDays.length === 5 &&
    sortedDays.every((day) => day >= 0 && day <= 4)
  ) {
    return "Weekdays (Mon-Fri)";
  }

  if (
    sortedDays.length === 2 &&
    sortedDays.includes(5) &&
    sortedDays.includes(6)
  ) {
    return "Weekends (Sat-Sun)";
  }

  // For other patterns, list the days
  const dayList = sortedDays.map((day) => dayNames[day]).join(", ");
  return `Every ${dayList}`;
};

/**
 * Get a short summary of recurrence with upcoming date range
 */
export const getRecurrenceSummary = (recurrence: number[]): string => {
  const pattern = formatRecurrencePattern(recurrence);
  const now = dateUtils.getNow();
  const threeMonthsLater = dateUtils.addDays(now, 90);

  return `${pattern} (${now.toLocaleDateString()} - ${threeMonthsLater.toLocaleDateString()})`;
};

/**
 * Format the time window of a recurring event
 */
export const formatTimeWindow = (
  startTime: string | null | undefined,
  endTime: string | null | undefined
): string => {
  if (!startTime || !endTime) {
    return "Any time";
  }

  // Format times to be more readable (HH:MM → h:mm AM/PM)
  const formatTimeString = (timeStr: string): string => {
    try {
      const [hours, minutes] = timeStr.split(":").map(Number);
      const period = hours >= 12 ? "PM" : "AM";
      const hour12 = hours % 12 || 12; // Convert 0 to 12 for 12 AM
      return `${hour12}:${minutes.toString().padStart(2, "0")} ${period}`;
    } catch {
      return timeStr; // Return original if parsing fails
    }
  };

  return `${formatTimeString(startTime)} - ${formatTimeString(endTime)}`;
};
