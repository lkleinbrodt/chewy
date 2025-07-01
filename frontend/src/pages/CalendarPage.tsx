import { Alert, AlertDescription } from "@/components/ui/alert";
import { useEffect, useMemo, useState } from "react";

import CalendarDirectorySelector from "@/components/settings/CalendarDirectorySelector";
import type { CalendarEvent } from "@/types/calendar";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import EventDetails from "@/components/calendar/EventDetails";
import { ExclamationTriangleIcon } from "@radix-ui/react-icons";
import { ScheduleWarning } from "@/components/common/ScheduleWarning";
import type { Task } from "@/types/task";
import TaskDetailModal from "@/components/tasks/TaskDetailModal";
import WeekView from "@/components/calendar/WeekView";
import { useCalendar } from "@/hooks/useCalendar";
import { useSchedule } from "@/hooks/useSchedule";
import { useTasks } from "@/hooks/useTasks";

const SYNC_INTERVAL = 300000; // 5 minutes in milliseconds

const CalendarPage = () => {
  const {
    startDate: calendarStartDate,
    endDate: calendarEndDate,
    events,
    loading: calendarLoading,
    error: calendarError,
    syncCalendar,
    updateEvent,
    nextWeek: calendarNextWeek,
    prevWeek: calendarPrevWeek,
    goToToday: calendarGoToToday,
  } = useCalendar();

  const {
    error: scheduleError,
    generateSchedule,
    isGenerating,
  } = useSchedule();

  const {
    tasks: allTasks,
    loading: tasksLoading,
    error: tasksError,
  } = useTasks();

  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(
    null
  );
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isTaskDetailModalOpen, setIsTaskDetailModalOpen] = useState(false);
  const [showDirectorySelector, setShowDirectorySelector] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);

  // Set up automatic syncing and initial calendar sync on page load
  useEffect(() => {
    const initializeCalendar = async () => {
      // Initial sync
      await handleSyncCalendar();
      setHasInitialized(true);
    };

    if (!hasInitialized) {
      initializeCalendar();
    }

    // Set up interval for periodic syncing
    const intervalId = setInterval(() => {
      handleSyncCalendar();
    }, SYNC_INTERVAL);

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, [hasInitialized]); // Only depend on hasInitialized to prevent re-runs

  // Filter tasks with start and end dates for calendar display
  const tasksToDisplayOnCalendar = useMemo(() => {
    return allTasks.filter((task) => !!task.start && !!task.end);
  }, [allTasks]);

  const handleEventClick = (event: CalendarEvent) => {
    setSelectedEvent(event);
  };

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsTaskDetailModalOpen(true);
  };

  const handleCloseEventModal = () => {
    setSelectedEvent(null);
  };

  const handleCloseTaskModal = () => {
    setSelectedTask(null);
    setIsTaskDetailModalOpen(false);
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
      return;
    }
    if (result.success && result.changes_detected) {
      await generateSchedule(false, false); // forceSyncCalendar = false since we just synced, and don't show toast for automatic generation
    }
  };

  const handleManualRegenerate = async () => {
    const result = await generateSchedule(true, true); // forceSyncCalendar = true for manual regeneration, and show success toast
    if (result.error === "CALENDAR_DIR_NOT_SET") {
      setShowDirectorySelector(true);
    }
  };

  // Combined navigation functions to keep both hooks in sync
  const nextWeek = () => {
    calendarNextWeek();
  };

  const prevWeek = () => {
    calendarPrevWeek();
  };

  const goToToday = () => {
    calendarGoToToday();
  };

  // Combine errors from all hooks
  const error = calendarError || scheduleError || tasksError;
  const loading = calendarLoading || tasksLoading;

  return (
    <div className="flex flex-col h-full">
      <CalendarHeader
        startDate={calendarStartDate}
        endDate={calendarEndDate}
        onPrevWeek={prevWeek}
        onNextWeek={nextWeek}
        onToday={goToToday}
        onRegenerateSchedule={handleManualRegenerate}
        isGeneratingSchedule={isGenerating}
      />
      <ScheduleWarning />

      {error && (
        <Alert variant="destructive" className="my-2">
          <ExclamationTriangleIcon className="h-4 w-4" />
          <AlertDescription>{error?.toString()}</AlertDescription>
        </Alert>
      )}

      <div className="flex-1 bg-white dark:bg-slate-900 rounded-md border overflow-hidden">
        <WeekView
          startDate={calendarStartDate}
          events={events}
          tasksToDisplayOnCalendar={tasksToDisplayOnCalendar}
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

      {selectedTask && isTaskDetailModalOpen && (
        <TaskDetailModal task={selectedTask} onClose={handleCloseTaskModal} />
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
