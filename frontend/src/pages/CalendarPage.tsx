import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMemo, useState } from "react";

import CalendarDirectorySelector from "@/components/settings/CalendarDirectorySelector";
import type { CalendarEvent } from "@/types/calendar";
import CalendarHeader from "@/components/calendar/CalendarHeader";
import EventDetails from "@/components/calendar/EventDetails";
import { ExclamationTriangleIcon } from "@radix-ui/react-icons";
import type { Task } from "@/types/task";
import TaskDetailModal from "@/components/tasks/TaskDetailModal";
import WeekView from "@/components/calendar/WeekView";
import { handleApiErrorWithToast } from "@/utils/errorUtils";
import scheduleService from "@/services/scheduleService";
import { useCalendar } from "@/hooks/useCalendar";
import { useSchedule } from "@/hooks/useSchedule";
import { useTasks } from "@/hooks/useTasks";
import { useToast } from "@/components/ui/use-toast";

const CalendarPage = () => {
  const {
    startDate: calendarStartDate,
    endDate: calendarEndDate,
    events,
    loading: calendarLoading,
    error: calendarError,
    isSyncing,
    lastSyncTime,
    syncCalendar,
    updateEvent,
    nextWeek: calendarNextWeek,
    prevWeek: calendarPrevWeek,
    goToToday: calendarGoToToday,
  } = useCalendar();

  const {
    isGenerating,
    error: scheduleError,
    generateSchedule,
  } = useSchedule();

  const {
    tasks: allTasks,
    loading: tasksLoading,
    error: tasksError,
    refreshTasks,
    setTasksManually,
  } = useTasks();

  const { toast } = useToast();
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(
    null
  );
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isTaskDetailModalOpen, setIsTaskDetailModalOpen] = useState(false);
  const [showDirectorySelector, setShowDirectorySelector] = useState(false);

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
    }
    return result;
  };

  // First sync calendar, then generate schedule only if sync was successful
  const handleGenerateSchedule = async () => {
    if (allTasks.length === 0) {
      toast({
        title: "No Tasks Available",
        description: "Create some tasks before generating a schedule.",
        variant: "default",
      });
      return false;
    }

    const syncResult = await syncCalendar();
    if (!syncResult.success) {
      toast({
        title: "Sync Failed",
        description: "Cannot generate schedule until calendar is synced.",
        variant: "destructive",
      });
      if (syncResult.needsDirectorySetup) setShowDirectorySelector(true);
      return false;
    }

    try {
      const result = await generateSchedule();
      if (result.success && result.updatedTasks) {
        setTasksManually(result.updatedTasks);
        toast({
          title: "Schedule Generated",
          description: "Your tasks have been scheduled.",
        });
      }
      return result.success;
    } catch (err) {
      handleApiErrorWithToast(err, "generating schedule");
      return false;
    }
  };

  const handleClearScheduleData = async () => {
    if (
      !window.confirm(
        "Are you sure you want to clear all scheduled times from tasks?"
      )
    )
      return;

    try {
      await scheduleService.clearScheduleDataFromTasks();
      await refreshTasks(); // Tell useTasks to re-fetch all tasks
      toast({
        title: "Schedule Cleared",
        description: "All task schedule times have been removed.",
      });
    } catch (err) {
      handleApiErrorWithToast(err, "clearing schedule");
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
        onSync={handleSyncCalendar}
        onGenerateSchedule={handleGenerateSchedule}
        onClearScheduleData={handleClearScheduleData}
        isSyncing={isSyncing}
        isGenerating={isGenerating}
        lastSyncTime={lastSyncTime}
      />

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
