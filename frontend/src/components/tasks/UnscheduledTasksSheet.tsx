import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import type { Task } from "@/types/task";
import type { UnscheduledTaskInfo } from "@/contexts/ScheduleStatusContext";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  tasks: UnscheduledTaskInfo[];
}

function formatTaskDisplayName(task: Task): string {
  // If this is a recurring task with an instance date, format it nicely
  if (task.recurring_event_id && task.instance_date) {
    const date = new Date(task.instance_date);
    const dateStr = date.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    return `${task.content} (${dateStr})`;
  }
  return task.content;
}

export function UnscheduledTasksSheet({ isOpen, onClose, tasks }: Props) {
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-[600px] sm:w-[600px]">
        <SheetHeader>
          <SheetTitle>Scheduling Failures</SheetTitle>
          <SheetDescription>
            The following tasks could not be scheduled. You may need to adjust
            their constraints, move conflicting calendar events, or free up more
            time.
          </SheetDescription>
        </SheetHeader>
        <div className="py-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map(({ task, reason }) => (
                <TableRow key={task.id}>
                  <TableCell className="font-medium">
                    {formatTaskDisplayName(task)}
                  </TableCell>
                  <TableCell>{reason}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </SheetContent>
    </Sheet>
  );
}
