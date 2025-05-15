import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Button } from "@/components/ui/button";
import type { ScheduledTask } from "@/types/schedule";
import { dateUtils } from "@/utils/dateUtils";

interface ScheduledTaskDetailsProps {
  task: ScheduledTask | null;
  onClose: () => void;
  onUpdate: (
    taskId: string,
    updateData: { status?: string }
  ) => Promise<boolean>;
}

const ScheduledTaskDetails = ({
  task,
  onClose,
  onUpdate,
}: ScheduledTaskDetailsProps) => {
  if (!task) return null;

  const handleStatusChange = async (status: string) => {
    const success = await onUpdate(task.id, { status });
    if (success) {
      onClose();
    }
  };

  const formatDateTime = (dateValue: string | Date) => {
    // If it's already a Date object, format it directly
    if (dateValue instanceof Date) {
      return dateUtils.formatToLocalDateTime(dateValue, "MMM d, yyyy h:mm a");
    }

    // Otherwise parse the string first
    const date = dateUtils.parseUtcISOString(dateValue);
    return dateUtils.formatToLocalDateTime(date, "MMM d, yyyy h:mm a");
  };

  // Calculate duration in hours and minutes
  const getDurationFormatted = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours > 0 ? `${hours}h ` : ""}${mins > 0 ? `${mins}m` : ""}`;
  };

  return (
    <Dialog open={!!task} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{task.task_content}</DialogTitle>
          <DialogDescription>
            View and update the scheduled task.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">Start:</div>
            <div className="col-span-3 text-sm">
              {formatDateTime(task.start)}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">End:</div>
            <div className="col-span-3 text-sm">{formatDateTime(task.end)}</div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <div className="text-sm font-medium">Duration:</div>
            <div className="col-span-3 text-sm">
              {getDurationFormatted(task.duration)}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 items-center">
            <div className="text-sm font-medium">Status:</div>
            <div className="col-span-3">
              <Select
                defaultValue={task.status}
                onValueChange={handleStatusChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="rescheduled">Rescheduled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ScheduledTaskDetails;
