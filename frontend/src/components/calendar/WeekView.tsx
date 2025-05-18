import { getEventsForDay, getWeekDays } from "@/utils/dateUtils";

import type { CalendarEvent } from "@/types/calendar";
import DayColumn from "./DayColumn";
import type { Task } from "@/types/task";
import TimeGrid from "./TimeGrid";
import { appConfig } from "@/constants/appConfig";
import { isSameDay } from "date-fns";

interface WeekViewProps {
  startDate: Date;
  events: CalendarEvent[];
  tasksToDisplayOnCalendar?: Task[];
  loading: boolean;
  onEventClick: (event: CalendarEvent) => void;
  onTaskClick?: (task: Task) => void;
}

const WeekView = ({
  startDate,
  events,
  tasksToDisplayOnCalendar = [],
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
    tasksToDisplayOnCalendar.forEach((task) => {
      if (!task.start || !task.end) return;

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
  const getTasksForDay = (tasks: Task[], date: Date): Task[] => {
    return tasks.filter((task) => {
      if (!task.start) return false; // Only consider tasks that have a start time
      const taskStartDate =
        typeof task.start === "string" ? new Date(task.start) : task.start;
      return isSameDay(taskStartDate, date);
    });
  };

  if (loading) {
    return (
      <div className="flex-1 overflow-auto flex">
        <TimeGrid startHour={displayStartHour} endHour={displayEndHour} />

        {/* Day columns */}
        <div className="flex flex-1">
          {weekDays.map((day) => (
            <DayColumn
              key={day.toString()}
              date={day}
              events={[]}
              tasksToDisplayOnCalendar={[]}
              onEventClick={() => {}}
              onTaskClick={() => {}}
              startHour={displayStartHour}
              endHour={displayEndHour}
            />
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
            tasksToDisplayOnCalendar={getTasksForDay(
              tasksToDisplayOnCalendar,
              day
            )}
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
