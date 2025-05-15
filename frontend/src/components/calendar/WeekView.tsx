import { getEventsForDay, getWeekDays } from "@/utils/dateUtils";

import type { CalendarEvent } from "@/types/calendar";
import DayColumn from "./DayColumn";
import type { ScheduledTask } from "@/types/schedule";
import { Skeleton } from "@/components/ui/skeleton";
import TimeGrid from "./TimeGrid";
import { appConfig } from "@/constants/appConfig";

interface WeekViewProps {
  startDate: Date;
  events: CalendarEvent[];
  scheduledTasks?: ScheduledTask[];
  loading: boolean;
  onEventClick: (event: CalendarEvent) => void;
  onTaskClick?: (task: ScheduledTask) => void;
}

const WeekView = ({
  startDate,
  events,
  scheduledTasks = [],
  loading,
  onEventClick,
  onTaskClick,
}: WeekViewProps) => {
  const { start: configStartHour, end: configEndHour } =
    appConfig.calendar.workingHours;

  // Calculate dynamic start/end hours based on events and tasks
  const calculateDisplayHours = () => {
    let displayStartHour = configStartHour;
    let displayEndHour = configEndHour;

    // Check if any events fall outside the working hours
    events.forEach((event) => {
      const eventStart = new Date(event.start);
      const eventEnd = new Date(event.end);

      const eventStartHour = eventStart.getHours();
      const eventEndHour = Math.ceil(
        eventEnd.getHours() + (eventEnd.getMinutes() > 0 ? 1 : 0)
      );

      // Adjust display range if events fall outside configured hours
      if (eventStartHour < displayStartHour) {
        displayStartHour = eventStartHour;
      }

      if (eventEndHour > displayEndHour) {
        displayEndHour = eventEndHour;
      }
    });

    // Also check scheduled tasks
    scheduledTasks.forEach((task) => {
      const taskStart = new Date(task.start);
      const taskEnd = new Date(task.end);

      const taskStartHour = taskStart.getHours();
      const taskEndHour = Math.ceil(
        taskEnd.getHours() + (taskEnd.getMinutes() > 0 ? 1 : 0)
      );

      if (taskStartHour < displayStartHour) {
        displayStartHour = taskStartHour;
      }

      if (taskEndHour > displayEndHour) {
        displayEndHour = taskEndHour;
      }
    });

    return { displayStartHour, displayEndHour };
  };

  const { displayStartHour, displayEndHour } = calculateDisplayHours();

  // Get array of days for the week
  const weekDays = getWeekDays(startDate);

  // Function to get scheduled tasks for a specific day
  const getTasksForDay = (tasks: ScheduledTask[], date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const day = date.getDate();

    return tasks.filter((task) => {
      const taskDate = new Date(task.start);
      return (
        taskDate.getFullYear() === year &&
        taskDate.getMonth() === month &&
        taskDate.getDate() === day
      );
    });
  };

  if (loading) {
    return (
      <div className="flex-1 flex">
        <div className="w-16 relative border-r">
          <Skeleton className="h-12 w-full" />
          <div className="space-y-2 pt-2 px-2">
            {Array.from({ length: configEndHour - configStartHour }).map(
              (_, i) => (
                <Skeleton key={i} className="h-8 w-10" />
              )
            )}
          </div>
        </div>
        <div className="flex-1 grid grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="border-r">
              <Skeleton className="h-12 w-full" />
              <div className="p-2 space-y-2">
                {Array.from({ length: (i % 3) + 1 }).map((_, j) => (
                  <Skeleton key={j} className="h-16 w-full" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto flex">
      {/* Time indicators */}
      <TimeGrid startHour={displayStartHour} endHour={displayEndHour} />

      {/* Day columns */}
      <div className="flex flex-1">
        {weekDays.map((day) => (
          <DayColumn
            key={day.toString()}
            date={day}
            events={getEventsForDay(events, day)}
            scheduledTasks={getTasksForDay(scheduledTasks, day)}
            onEventClick={onEventClick}
            onTaskClick={onTaskClick}
            startHour={displayStartHour}
            endHour={displayEndHour}
          />
        ))}
      </div>
    </div>
  );
};

export default WeekView;
