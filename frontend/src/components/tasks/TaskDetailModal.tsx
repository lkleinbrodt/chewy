import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { Button } from "@/components/ui/button";
import type { Task } from "@/types/task";
import { dateUtils } from "@/utils/dateUtils";
import { formatDuration } from "@/utils/taskUtils";

interface TaskDetailModalProps {
  task: Task | null;
  onClose: () => void;
  onEdit?: () => void;
}

const TaskDetailModal = ({ task, onClose, onEdit }: TaskDetailModalProps) => {
  if (!task) return null;

  const formatDateTime = (dateValue: string | Date | undefined) => {
    if (!dateValue) return "Not scheduled";

    // If it's already a Date object, format it directly
    if (dateValue instanceof Date) {
      return dateUtils.formatToLocalDateTime(dateValue, "MMM d, yyyy h:mm a");
    }

    // Otherwise parse the string first
    const date = dateUtils.parseUtcISOString(dateValue);
    return dateUtils.formatToLocalDateTime(date, "MMM d, yyyy h:mm a");
  };

  return (
    <Dialog open={!!task} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{task.content}</DialogTitle>
          <DialogDescription>Task details</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">Type:</div>
            <div className="col-span-3 text-sm capitalize">
              {task.task_type}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">Duration:</div>
            <div className="col-span-3 text-sm">
              {formatDuration(task.duration)}
            </div>
          </div>

          {task.task_type === "one-off" && (
            <div className="grid grid-cols-4 gap-2">
              <div className="text-sm font-medium">Due by:</div>
              <div className="col-span-3 text-sm">
                {dateUtils.formatToLocalDate(
                  task.due_by ? new Date(task.due_by) : new Date(),
                  "MMM d, yyyy"
                )}
              </div>
            </div>
          )}

          {task.start && task.end && (
            <>
              <div className="grid grid-cols-4 gap-2">
                <div className="text-sm font-medium">Start:</div>
                <div className="col-span-3 text-sm">
                  {formatDateTime(task.start)}
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2">
                <div className="text-sm font-medium">End:</div>
                <div className="col-span-3 text-sm">
                  {formatDateTime(task.end)}
                </div>
              </div>
            </>
          )}

          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">Status:</div>
            <div className="col-span-3 text-sm">
              {task.is_completed ? "Completed" : "Active"}
            </div>
          </div>
        </div>

        <DialogFooter className="flex justify-between">
          {onEdit && (
            <Button type="button" variant="outline" onClick={onEdit}>
              Edit
            </Button>
          )}
          <Button type="button" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskDetailModal;
