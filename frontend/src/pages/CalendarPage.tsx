import { Alert, AlertDescription } from "@/components/ui/alert";

import type { CalendarEvent } from "@/types/calendar";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import EventDetails from "@/components/calendar/EventDetails";
import { ExclamationTriangleIcon } from "@radix-ui/react-icons";
import type { ScheduledTask } from "@/types/schedule";
import ScheduledTaskDetails from "@/components/tasks/ScheduledTaskDetails";
import WeekView from "@/components/calendar/WeekView";
import { useCalendar } from "@/hooks/useCalendar";
import { useState } from "react";

const CalendarPage = () => {
  const {
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
  } = useCalendar();

  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(
    null
  );
  const [selectedTask, setSelectedTask] = useState<ScheduledTask | null>(null);

  const handleEventClick = (event: CalendarEvent) => {
    setSelectedEvent(event);
  };

  const handleTaskClick = (task: ScheduledTask) => {
    setSelectedTask(task);
  };

  const handleCloseEventModal = () => {
    setSelectedEvent(null);
  };

  const handleCloseTaskModal = () => {
    setSelectedTask(null);
  };

  const handleUpdateEvent = async (
    eventId: string,
    eventData: { subject?: string; start?: Date; end?: Date }
  ) => {
    const success = await updateEvent(eventId, eventData);
    if (success) {
      setSelectedEvent(null);
    }
    return success;
  };

  return (
    <div className="flex flex-col h-full">
      <CalendarHeader
        startDate={startDate}
        endDate={endDate}
        onPrevWeek={prevWeek}
        onNextWeek={nextWeek}
        onToday={goToToday}
        onSync={syncCalendar}
        onGenerateSchedule={generateSchedule}
        isSyncing={isSyncing}
        isGenerating={isGenerating}
        lastSyncTime={lastSyncTime}
      />

      {error && (
        <Alert variant="destructive" className="my-2">
          <ExclamationTriangleIcon className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex-1 bg-white dark:bg-slate-900 rounded-md border overflow-hidden">
        <WeekView
          startDate={startDate}
          events={events}
          scheduledTasks={scheduledTasks}
          loading={loading}
          onEventClick={handleEventClick}
          onTaskClick={handleTaskClick}
        />
      </div>

      {selectedEvent && (
        <EventDetails
          event={selectedEvent}
          onClose={handleCloseEventModal}
          onUpdate={handleUpdateEvent}
        />
      )}

      {selectedTask && (
        <ScheduledTaskDetails
          task={selectedTask}
          onClose={handleCloseTaskModal}
          onUpdate={updateScheduledTask}
        />
      )}
    </div>
  );
};

export default CalendarPage;
