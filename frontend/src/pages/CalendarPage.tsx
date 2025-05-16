import { Alert, AlertDescription } from "@/components/ui/alert";
import { useEffect, useState } from "react";

import CalendarDirectorySelector from "@/components/settings/CalendarDirectorySelector";
import type { CalendarEvent } from "@/types/calendar";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import EventDetails from "@/components/calendar/EventDetails";
import { ExclamationTriangleIcon } from "@radix-ui/react-icons";
import type { ScheduledTask } from "@/types/schedule";
import ScheduledTaskDetails from "@/components/tasks/ScheduledTaskDetails";
import WeekView from "@/components/calendar/WeekView";
import { useCalendar } from "@/hooks/useCalendar";
import { useSchedule } from "@/hooks/useSchedule";

const CalendarPage = () => {
  const {
    startDate: calendarStartDate,
    endDate: calendarEndDate,
    events,
    loading: calendarLoading,
    error: calendarError,
    isSyncing,
    lastSyncTime,
    nextWeek: calendarNextWeek,
    prevWeek: calendarPrevWeek,
    goToToday: calendarGoToToday,
    syncCalendar,
    updateEvent,
  } = useCalendar();

  const {
    startDate: scheduleStartDate,
    scheduledTasks,
    isLoading: scheduleLoading,
    isGenerating,
    error: scheduleError,
    nextWeek: scheduleNextWeek,
    prevWeek: schedulePrevWeek,
    goToToday: scheduleGoToToday,
    generateSchedule,
    updateScheduledTask,
    clearAllScheduledTasks,
  } = useSchedule();

  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(
    null
  );
  const [selectedTask, setSelectedTask] = useState<ScheduledTask | null>(null);
  const [showDirectorySelector, setShowDirectorySelector] = useState(false);

  // Keep calendar and schedule date ranges in sync
  useEffect(() => {
    if (calendarStartDate.getTime() !== scheduleStartDate.getTime()) {
      scheduleGoToToday();
    }
  }, [calendarStartDate, scheduleStartDate, scheduleGoToToday]);

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

  const handleSyncCalendar = async () => {
    const result = await syncCalendar();
    if (result.needsDirectorySetup) {
      setShowDirectorySelector(true);
    }
    return result;
  };

  // First sync calendar, then generate schedule only if sync was successful
  const handleGenerateSchedule = async () => {
    const syncResult = await handleSyncCalendar();
    if (syncResult.success) {
      return await generateSchedule();
    }
    return false;
  };

  // Combined navigation functions to keep both hooks in sync
  const nextWeek = () => {
    calendarNextWeek();
    scheduleNextWeek();
  };

  const prevWeek = () => {
    calendarPrevWeek();
    schedulePrevWeek();
  };

  const goToToday = () => {
    calendarGoToToday();
    scheduleGoToToday();
  };

  // Combine errors from both hooks
  const error = calendarError || scheduleError;
  const loading = calendarLoading || scheduleLoading;

  return (
    <div className="flex flex-col h-full">
      <CalendarHeader
        startDate={calendarStartDate}
        endDate={calendarEndDate}
        onPrevWeek={prevWeek}
        onNextWeek={nextWeek}
        onToday={goToToday}
        onSync={handleSyncCalendar}
        onGenerateSchedule={handleGenerateSchedule}
        onClearAllTasks={clearAllScheduledTasks}
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
          startDate={calendarStartDate}
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

      <CalendarDirectorySelector
        isOpen={showDirectorySelector}
        onClose={() => setShowDirectorySelector(false)}
        onDirectorySet={handleSyncCalendar}
      />
    </div>
  );
};

export default CalendarPage;
