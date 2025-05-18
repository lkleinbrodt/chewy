import { calculateEventPosition, dateUtils } from "@/utils/dateUtils";

import type { CalendarEvent } from "@/types/calendar";
import EventBlock from "./EventBlock";
import type { Task } from "@/types/task";
import TaskBlock from "../calendar/TaskBlock";
import { appConfig } from "@/constants/appConfig";
import { cn } from "@/lib/utils";
import { isToday } from "date-fns";

interface DayColumnProps {
  date: Date;
  events: CalendarEvent[];
  tasksToDisplayOnCalendar?: Task[];
  onEventClick: (event: CalendarEvent) => void;
  onTaskClick?: (task: Task) => void;
  startHour?: number;
  endHour?: number;
}

const DayColumn = ({
  date,
  events,
  tasksToDisplayOnCalendar = [],
  onEventClick,
  onTaskClick,
  startHour: propStartHour,
  endHour: propEndHour,
}: DayColumnProps) => {
  // Use props if provided, otherwise use config values
  const { start: configStartHour, end: configEndHour } =
    appConfig.calendar.workingHours;
  const workStartHour =
    propStartHour !== undefined ? propStartHour : configStartHour;
  const workEndHour = propEndHour !== undefined ? propEndHour : configEndHour;

  // Generate time slots background (1-hour intervals) only for working hours
  const timeSlots = Array.from({ length: workEndHour - workStartHour }).map(
    (_, i) => {
      const hour = workStartHour + i;
      const isBusinessHour = hour >= configStartHour && hour < configEndHour;
      return (
        <div
          key={hour}
          className={cn(
            "h-16 border-t border-gray-200 relative",
            isBusinessHour ? "bg-gray-50/50" : ""
          )}
        >
          {/* Add a small hour indicator inside each slot for debugging/alignment */}
          {/* <div className="absolute top-0 left-1 text-[10px] text-gray-400">
            {hour}:00
          </div> */}
        </div>
      );
    }
  );

  // Position events within the day column
  const eventBlocks = events.map((event) => {
    const position = calculateEventPosition(
      {
        start: event.start,
        end: event.end,
      },
      workStartHour,
      workEndHour
    );

    return (
      <EventBlock
        key={event.id}
        event={event}
        onClick={onEventClick}
        style={position}
      />
    );
  });

  // Position scheduled tasks within the day column
  const taskBlocks = tasksToDisplayOnCalendar
    .map((task) => {
      // Skip tasks without start or end times
      if (!task.start || !task.end) return null;

      // Calculate position using the same utility as events
      const position = calculateEventPosition(
        {
          start: task.start,
          end: task.end,
        },
        workStartHour,
        workEndHour
      );

      return (
        <TaskBlock
          key={task.id}
          task={task}
          onClick={onTaskClick}
          style={position}
        />
      );
    })
    .filter(Boolean); // Filter out null values

  const dayIsToday = isToday(date);
  const now = dateUtils.getNow();

  return (
    <div className="flex-1 relative min-w-[120px]">
      {/* Day header */}
      <div
        className={cn(
          "h-12 px-2 border-b border-r text-center flex flex-col justify-center",
          dayIsToday ? "bg-blue-50 dark:bg-blue-900/20" : ""
        )}
      >
        <div className="text-sm font-medium">
          {dateUtils.formatToLocalDate(date, "EEE")}
        </div>
        <div
          className={cn(
            "text-lg",
            dayIsToday ? "text-blue-600 dark:text-blue-400 font-bold" : ""
          )}
        >
          {dateUtils.formatToLocalDate(date, "d")}
        </div>
      </div>

      {/* Time slots */}
      <div className="relative h-[calc(100%-3rem)] border-r">
        {/* Time slot grid */}
        <div className="absolute inset-0">{timeSlots}</div>

        {/* Current time indicator */}
        {dayIsToday && (
          <div
            className="absolute left-0 right-0 border-t border-red-400 z-10"
            style={{
              top: `${
                ((now.getHours() + now.getMinutes() / 60 - workStartHour) /
                  (workEndHour - workStartHour)) *
                100
              }%`,
              display:
                now.getHours() < workStartHour || now.getHours() >= workEndHour
                  ? "none"
                  : "block",
            }}
          >
            <div className="absolute -left-1 -top-1 w-2 h-2 rounded-full bg-red-400" />
          </div>
        )}

        {/* Events */}
        <div className="absolute inset-0 px-1">
          {eventBlocks}
          {taskBlocks}
        </div>
      </div>
    </div>
  );
};

export default DayColumn;
