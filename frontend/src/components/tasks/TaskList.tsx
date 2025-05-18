import {
  ArrowUpDown,
  Check,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Trash,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  formatDuration,
  formatTaskSchedule,
  getTaskStatus,
} from "@/utils/taskUtils";
import {
  formatTimeWindow,
  getRecurrenceSummary,
} from "@/utils/recurringEventUtils";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import DependencyVisualizer from "./DependencyVisualizer";
import type { RecurringEvent } from "@/types/recurringEvent";
import type { Task } from "@/types/task";
import { useState } from "react";

interface TaskListProps {
  tasks: Task[];
  recurringEvents?: RecurringEvent[];
  loading: boolean;
  onEdit: (task: Task) => void;
  onEditRecurringEvent?: (recurringEvent: RecurringEvent) => void;
  onDelete: (id: string) => void;
  onDeleteRecurringEvent?: (id: string) => void;
  onComplete: (id: string) => void;
  onResetRecurringEventTasks?: (id: string) => void;
  showRecurringEvents?: boolean;
}

type SortField = "content" | "due_by" | "duration" | "recurrence";

const TaskList = ({
  tasks,
  recurringEvents = [],
  loading,
  onEdit,
  onEditRecurringEvent,
  onDelete,
  onDeleteRecurringEvent,
  onComplete,
  onResetRecurringEventTasks,
  showRecurringEvents = false,
}: TaskListProps) => {
  const [sortField, setSortField] = useState<SortField>("due_by");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Handle task selection for dependency navigation
  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId);
    // Scroll to the selected task
    const taskElement = document.getElementById(`task-${taskId}`);
    if (taskElement) {
      taskElement.scrollIntoView({ behavior: "smooth", block: "center" });
      // Highlight the task briefly
      taskElement.classList.add("bg-amber-50");
      setTimeout(() => {
        taskElement.classList.remove("bg-amber-50");
      }, 2000);
    }
  };

  // Sort tasks based on current sort field and direction
  const sortedTasks = [...tasks].sort((a, b) => {
    if (sortField === "due_by") {
      // Handle sorting for one-off tasks with due dates
      const aIsOneOff = !a.recurrence || a.recurrence.length === 0;
      const bIsOneOff = !b.recurrence || b.recurrence.length === 0;

      if (aIsOneOff && bIsOneOff) {
        if (!a.due_by) return 1;
        if (!b.due_by) return -1;

        const dateA = new Date(a.due_by);
        const dateB = new Date(b.due_by);

        return sortDirection === "asc"
          ? dateA.getTime() - dateB.getTime()
          : dateB.getTime() - dateA.getTime();
      }
      // Sort one-off tasks before recurring tasks
      if (aIsOneOff && !bIsOneOff) return -1;
      if (!aIsOneOff && bIsOneOff) return 1;
    }

    if (sortField === "content") {
      return sortDirection === "asc"
        ? a.content.localeCompare(b.content)
        : b.content.localeCompare(a.content);
    }

    if (sortField === "duration") {
      return sortDirection === "asc"
        ? a.duration - b.duration
        : b.duration - a.duration;
    }

    return 0;
  });

  // Sort recurring events
  const sortedRecurringEvents = [...recurringEvents].sort((a, b) => {
    if (sortField === "content") {
      return sortDirection === "asc"
        ? a.content.localeCompare(b.content)
        : b.content.localeCompare(a.content);
    }

    if (sortField === "duration") {
      return sortDirection === "asc"
        ? a.duration - b.duration
        : b.duration - a.duration;
    }

    if (sortField === "recurrence") {
      // Sort by number of recurrence days first
      if (a.recurrence.length !== b.recurrence.length) {
        return sortDirection === "asc"
          ? a.recurrence.length - b.recurrence.length
          : b.recurrence.length - a.recurrence.length;
      }
      // Then sort by the first day in each recurrence
      const firstDayA = Math.min(...a.recurrence);
      const firstDayB = Math.min(...b.recurrence);
      return sortDirection === "asc"
        ? firstDayA - firstDayB
        : firstDayB - firstDayA;
    }

    return 0;
  });

  if (loading) {
    return <div className="flex justify-center p-8">Loading tasks...</div>;
  }

  if (
    tasks.length === 0 &&
    (!showRecurringEvents || recurringEvents.length === 0)
  ) {
    return (
      <div className="p-8 text-center text-gray-500">
        No tasks found. Create a new task to get started.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>
            <Button variant="ghost" onClick={() => handleSort("content")}>
              Task <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          </TableHead>
          <TableHead>
            {showRecurringEvents ? (
              <Button variant="ghost" onClick={() => handleSort("recurrence")}>
                Schedule / Recurrence <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button variant="ghost" onClick={() => handleSort("due_by")}>
                Due Date <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            )}
          </TableHead>
          <TableHead>
            <Button variant="ghost" onClick={() => handleSort("duration")}>
              Duration <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          </TableHead>
          <TableHead>
            {showRecurringEvents ? "Time Window" : "Dependencies"}
          </TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {/* Display Recurring Event Templates */}
        {showRecurringEvents &&
          sortedRecurringEvents.map((recurringEvent) => (
            <TableRow
              key={`rec-${recurringEvent.id}`}
              className="bg-violet-50 border-l-4 border-violet-400 hover:bg-violet-100 transition-colors"
            >
              <TableCell className="font-medium">
                <div className="flex items-center">
                  <div>
                    <div>{recurringEvent.content}</div>
                    <Badge
                      variant="outline"
                      className="ml-2 bg-violet-100 text-violet-700 border-violet-300"
                    >
                      Recurring Event
                    </Badge>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                {getRecurrenceSummary(recurringEvent.recurrence)}
              </TableCell>
              <TableCell>{formatDuration(recurringEvent.duration)}</TableCell>
              <TableCell>
                {formatTimeWindow(
                  recurringEvent.time_window_start,
                  recurringEvent.time_window_end
                )}
              </TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {onEditRecurringEvent && (
                      <DropdownMenuItem
                        onClick={() => onEditRecurringEvent(recurringEvent)}
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit Event
                      </DropdownMenuItem>
                    )}
                    {onResetRecurringEventTasks && (
                      <DropdownMenuItem
                        onClick={() =>
                          onResetRecurringEventTasks(recurringEvent.id)
                        }
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Reset Tasks
                      </DropdownMenuItem>
                    )}
                    {onDeleteRecurringEvent && (
                      <DropdownMenuItem
                        onClick={() =>
                          onDeleteRecurringEvent(recurringEvent.id)
                        }
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete Event
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}

        {/* Display Regular Tasks */}
        {sortedTasks.map((task) => {
          const status = getTaskStatus(task, tasks);
          const isRecurringInstance = task.task_type === "recurring";
          const isCompleted = task.is_completed;

          return (
            <TableRow
              key={task.id}
              id={`task-${task.id}`}
              className={`transition-colors duration-300 
                ${isCompleted ? "bg-green-50 border-l-4 border-green-300" : ""} 
                ${task.id === selectedTaskId ? "bg-amber-50" : ""}
                ${
                  isRecurringInstance && !isCompleted
                    ? "bg-blue-50 border-l-4 border-blue-300 hover:bg-blue-100"
                    : ""
                }
                ${
                  !isRecurringInstance && !isCompleted
                    ? "bg-white border-l-4 border-gray-300 hover:bg-gray-50"
                    : ""
                }
              `}
            >
              <TableCell className="font-medium">
                <div className="flex items-center">
                  <div
                    className={`h-3 w-3 rounded-full mr-2 ${status.color}`}
                  />
                  <div>
                    <div
                      className={
                        isCompleted ? "line-through text-gray-500" : ""
                      }
                    >
                      {task.content}
                    </div>
                    <div className="text-sm text-gray-500 flex gap-2">
                      {isRecurringInstance ? (
                        <>
                          <Badge
                            variant="outline"
                            className="bg-blue-50 text-blue-700 border-blue-300"
                          >
                            Recurring Instance
                          </Badge>
                          {task.instance_date && (
                            <span className="text-xs">
                              {new Date(
                                task.instance_date
                              ).toLocaleDateString()}
                            </span>
                          )}
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>
              </TableCell>
              <TableCell>{formatTaskSchedule(task)}</TableCell>
              <TableCell>{formatDuration(task.duration)}</TableCell>
              <TableCell>
                {!isRecurringInstance &&
                task.dependencies &&
                task.dependencies.length > 0 ? (
                  <DependencyVisualizer
                    task={task}
                    allTasks={tasks}
                    onTaskClick={handleTaskClick}
                  />
                ) : (
                  "-"
                )}
              </TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {!task.is_completed && (
                      <DropdownMenuItem onClick={() => onComplete(task.id)}>
                        <Check className="mr-2 h-4 w-4" />
                        Mark Complete
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => onEdit(task)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onDelete(task.id)}>
                      <Trash className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
};

export default TaskList;
