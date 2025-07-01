import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Plus, XCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Task, TaskFormData } from "@/types/task";
import { dateUtils, utcTimeToLocal } from "@/utils/dateUtils";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import type { RecurringEvent } from "@/types/recurringEvent";
import { ScheduleWarning } from "@/components/common/ScheduleWarning";
import TaskForm from "@/components/tasks/TaskForm";
import TaskList from "@/components/tasks/TaskList";
import recurringEventService from "@/services/recurringEventService";
import { useSchedule } from "@/hooks/useSchedule";
import { useTasks } from "@/hooks/useTasks";
import { useToast } from "@/hooks/use-toast";

const TaskListPage = () => {
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const [selectedRecurringEvent, setSelectedRecurringEvent] =
    useState<RecurringEvent | null>(null);
  const [recurringEvents, setRecurringEvents] = useState<RecurringEvent[]>([]);
  const [loadingRecurringEvents, setLoadingRecurringEvents] = useState(false);

  const { toast } = useToast();

  // Use the tasks hook with empty initial filters to get all tasks
  const {
    tasks: allTasks,
    loading,
    error,
    clearError,
    createTask,
    updateTask,
    deleteTask,
    completeTask,
    refreshTasks,
  } = useTasks();

  const { generateSchedule } = useSchedule();

  // Load recurring events
  useEffect(() => {
    loadRecurringEvents();
  }, []);

  // Filter tasks based on completion status
  const activeTasks = allTasks.filter(
    (task) =>
      !task.is_completed &&
      // Don't show recurring instances
      !(task.task_type === "recurring" && task.recurring_event_id)
  );

  const completedTasks = allTasks.filter(
    (task) =>
      task.is_completed &&
      // Don't show recurring instances
      !(task.task_type === "recurring" && task.recurring_event_id)
  );

  const loadRecurringEvents = async () => {
    try {
      setLoadingRecurringEvents(true);
      const events = await recurringEventService.getRecurringEvents();
      setRecurringEvents(events);
    } catch (error) {
      console.error("Error loading recurring events:", error);
      toast({
        title: "Error",
        description: "Failed to load recurring events",
        variant: "destructive",
      });
    } finally {
      setLoadingRecurringEvents(false);
    }
  };

  // Handle recurring event form open
  const handleRecurringEventEdit = (event: RecurringEvent) => {
    setSelectedRecurringEvent(event);
    setSelectedTask(undefined);
    setIsFormOpen(true);
  };

  // Handle task form submission
  const handleTaskFormSubmit = async (data: TaskFormData) => {
    try {
      // If this is a recurring task, create or update a recurring event
      if (data.is_recurring_ui_flag) {
        const recurringEventData = {
          content: data.content,
          duration: data.duration,
          recurrence_days: data.recurrence_days || [],
          time_window_start: data.time_window_start,
          time_window_end: data.time_window_end,
        };

        if (selectedRecurringEvent) {
          // Update existing recurring event
          await recurringEventService.updateRecurringEvent(
            selectedRecurringEvent.id,
            recurringEventData
          );
          toast({
            title: "Recurring event updated",
            description: "The recurring event has been updated.",
          });
          await generateSchedule(false, false); // Regenerate after updating recurring event, no success toast
        } else {
          // Create new recurring event
          await recurringEventService.createRecurringEvent(recurringEventData);
          toast({
            title: "Recurring event created",
            description: "The recurring event has been created.",
          });
          await generateSchedule(false, false); // Regenerate after creating recurring event, no success toast
        }

        // Refresh both recurring events and tasks
        await loadRecurringEvents();
        await refreshTasks();
        return Promise.resolve();
      }

      // Otherwise, handle as a regular task
      if (selectedTask) {
        await updateTask(selectedTask.id, data);
        toast({
          title: "Task updated",
          description: "The task has been updated successfully.",
        });
        await generateSchedule(false, false); // Regenerate after updating task, no success toast
      } else {
        await createTask(data);
        toast({
          title: "Task created",
          description: "The new task has been created successfully.",
        });
        await generateSchedule(false, false); // Regenerate after creating task, no success toast
      }
      return Promise.resolve();
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "An error occurred. Please try again.";

      toast({
        variant: "destructive",
        title: "Error",
        description: errorMessage,
      });
      return Promise.reject(error);
    }
  };

  // Handle form close
  const handleFormClose = () => {
    setIsFormOpen(false);
    setSelectedTask(undefined);
    setSelectedRecurringEvent(null);
  };

  // Handle editing task
  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setSelectedRecurringEvent(null);
    setIsFormOpen(true);
  };

  const handleDeleteTask = async (taskId: string) => {
    if (window.confirm("Are you sure you want to delete this task?")) {
      try {
        await deleteTask(taskId);
        toast({
          title: "Task deleted",
          description: "The task has been deleted successfully.",
        });
        await generateSchedule(false, false); // Regenerate after deleting task, no success toast
      } catch (err) {
        console.error("Failed to delete task:", err);
      }
    }
  };

  const handleDeleteRecurringEvent = async (id: string) => {
    if (
      window.confirm(
        "Are you sure you want to delete this recurring event? This will also delete all associated tasks."
      )
    ) {
      try {
        await recurringEventService.deleteRecurringEvent(id);
        toast({
          title: "Success",
          description: "Recurring event deleted",
        });
        // Refresh both recurring events and tasks
        await loadRecurringEvents();
        await refreshTasks();
        await generateSchedule(false, false); // Regenerate after deleting recurring event, no success toast
      } catch (error) {
        console.error("Error deleting recurring event:", error);
        toast({
          title: "Error",
          description: "Failed to delete recurring event",
          variant: "destructive",
        });
      }
    }
  };

  const handleResetRecurringEventTasks = async (id: string) => {
    try {
      // Use a 3-month window for task regeneration
      const startDate = dateUtils.getNow().toISOString();
      const endDate = dateUtils.addDays(dateUtils.getNow(), 90).toISOString();

      await recurringEventService.resetRecurringEventTasks(
        id,
        startDate,
        endDate
      );
      toast({
        title: "Success",
        description: "Tasks have been reset for this recurring event",
      });
      await refreshTasks();
      await generateSchedule(false, false); // Regenerate after resetting recurring event tasks, no success toast
    } catch (error) {
      console.error("Error resetting tasks:", error);
      toast({
        title: "Error",
        description: "Failed to reset tasks",
        variant: "destructive",
      });
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      await completeTask(taskId);
      toast({
        title: "Task completed",
        description: "The task has been marked as complete.",
      });
      await generateSchedule(false, false); // Regenerate after completing task, no success toast
    } catch (err) {
      console.error("Failed to complete task:", err);
    }
  };

  const handleCreateTask = () => {
    setSelectedTask(undefined);
    setSelectedRecurringEvent(null);
    setIsFormOpen(true);
  };

  // Convert RecurringEvent to a Task object for the TaskForm component
  const eventToTaskForm = (event: RecurringEvent): Task => {
    // Convert UTC time window values to local times for form display
    const baseDate = dateUtils.getNow();
    const localTimeWindowStart = utcTimeToLocal(
      event.time_window_start || null,
      baseDate
    );
    const localTimeWindowEnd = utcTimeToLocal(
      event.time_window_end || null,
      baseDate
    );

    return {
      id: event.id,
      content: event.content,
      duration: event.duration,
      is_completed: false,
      created_at: event.created_at,
      updated_at: event.updated_at,
      task_type: "recurring",
      recurrence: event.recurrence,
      time_window_start: localTimeWindowStart || undefined,
      time_window_end: localTimeWindowEnd || undefined,
    } as Task;
  };

  return (
    <div className="flex flex-col h-full">
      <ScheduleWarning />
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Tasks</h1>
          <div className="flex gap-2">
            <Button onClick={handleCreateTask} className="gap-2">
              <Plus className="h-4 w-4" /> New Task
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              {error.message}
              <Button
                variant="link"
                onClick={clearError}
                className="p-0 ml-2 h-auto font-normal text-sm underline"
              >
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="active" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
          </TabsList>
          <TabsContent value="active">
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
              <TaskList
                tasks={activeTasks}
                recurringEvents={recurringEvents}
                loading={loading || loadingRecurringEvents}
                onEdit={handleEditTask}
                onEditRecurringEvent={handleRecurringEventEdit}
                onDelete={handleDeleteTask}
                onDeleteRecurringEvent={handleDeleteRecurringEvent}
                onComplete={handleCompleteTask}
                onResetRecurringEventTasks={handleResetRecurringEventTasks}
                showRecurringEvents={true}
                tabType="active"
              />
            </div>
          </TabsContent>
          <TabsContent value="completed">
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
              <TaskList
                tasks={completedTasks}
                recurringEvents={[]}
                loading={loading || loadingRecurringEvents}
                onEdit={handleEditTask}
                onEditRecurringEvent={handleRecurringEventEdit}
                onDelete={handleDeleteTask}
                onDeleteRecurringEvent={handleDeleteRecurringEvent}
                onComplete={handleCompleteTask}
                onResetRecurringEventTasks={handleResetRecurringEventTasks}
                showRecurringEvents={false}
                tabType="completed"
              />
            </div>
          </TabsContent>
        </Tabs>

        {isFormOpen && (
          <TaskForm
            open={isFormOpen}
            onClose={handleFormClose}
            onSubmit={handleTaskFormSubmit}
            initialData={
              selectedRecurringEvent
                ? eventToTaskForm(selectedRecurringEvent)
                : selectedTask
            }
            availableTasks={allTasks.filter(
              (task) =>
                // Filter out completed tasks and the currently selected task
                !task.is_completed &&
                task.id !== selectedTask?.id &&
                // Only allow one-off tasks as dependencies (no recurring events or recurring instances)
                (!task.recurrence || task.recurrence.length === 0) &&
                // Exclude recurring task instances
                !task.recurring_event_id
            )}
          />
        )}
      </div>
    </div>
  );
};

export default TaskListPage;
