import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Plus, XCircle } from "lucide-react";
import type { Task, TaskFormData } from "@/types/task";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import type { RecurringEvent } from "@/types/recurringEvent";
import TaskForm from "@/components/tasks/TaskForm";
import TaskList from "@/components/tasks/TaskList";
import { dateUtils } from "@/utils/dateUtils";
import recurringEventService from "@/services/recurringEventService";
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

  // Load recurring events
  useEffect(() => {
    loadRecurringEvents();
  }, []);

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
        } else {
          // Create new recurring event
          await recurringEventService.createRecurringEvent(recurringEventData);
          toast({
            title: "Recurring event created",
            description: "The recurring event has been created.",
          });
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
      } else {
        await createTask(data);
        toast({
          title: "Task created",
          description: "The new task has been created successfully.",
        });
      }
      return Promise.resolve();
    } catch (error: unknown) {
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
    return {
      id: event.id,
      content: event.content,
      duration: event.duration,
      is_completed: false,
      created_at: event.created_at,
      updated_at: event.updated_at,
      task_type: "recurring",
      recurrence: event.recurrence,
      time_window_start: event.time_window_start || undefined,
      time_window_end: event.time_window_end || undefined,
    } as Task;
  };

  return (
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

      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <TaskList
          tasks={allTasks.filter(
            (task) =>
              // Don't show recurring instances
              !(task.task_type === "recurring" && task.recurring_event_id)
          )}
          recurringEvents={recurringEvents}
          loading={loading || loadingRecurringEvents}
          onEdit={handleEditTask}
          onEditRecurringEvent={handleRecurringEventEdit}
          onDelete={handleDeleteTask}
          onDeleteRecurringEvent={handleDeleteRecurringEvent}
          onComplete={handleCompleteTask}
          onResetRecurringEventTasks={handleResetRecurringEventTasks}
          showRecurringEvents={true}
        />
      </div>

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
              // Only allow one-off tasks as dependencies
              (!task.recurrence || task.recurrence.length === 0)
          )}
        />
      )}
    </div>
  );
};

export default TaskListPage;
