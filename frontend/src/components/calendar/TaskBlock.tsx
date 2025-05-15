import { Badge } from "@/components/ui/badge";
import type { ScheduledTask } from "@/types/schedule";
import { cn } from "@/lib/utils";
import { dateUtils } from "@/utils/dateUtils";

interface TaskBlockProps {
  task: ScheduledTask;
  onClick?: (task: ScheduledTask) => void;
  style: React.CSSProperties;
}

const TaskBlock = ({ task, onClick, style }: TaskBlockProps) => {
  const handleClick = () => {
    if (onClick) {
      onClick(task);
    }
  };

  // For debugging
  console.log("TaskBlock rendered with onClick handler:", !!onClick);

  const formatTime = (dateValue: string | Date) => {
    let date;
    if (dateValue instanceof Date) {
      date = dateValue;
    } else {
      date = dateUtils.parseUtcISOString(dateValue);
    }
    return dateUtils.formatToLocalTime(date, "h:mm a");
  };

  return (
    <div
      className={cn(
        "absolute p-1 rounded-md shadow-sm border-2 border-green-500 bg-green-50 dark:bg-green-900/20 text-sm cursor-pointer overflow-hidden transition-opacity hover:opacity-90 pointer-events-auto z-10",
        "left-1 right-1"
      )}
      style={style}
      onClick={handleClick}
    >
      <div className="flex justify-between items-start">
        <div className="font-medium line-clamp-2">{task.task_content}</div>
        <Badge
          variant={task.status === "completed" ? "secondary" : "outline"}
          className="text-xs"
        >
          {task.status}
        </Badge>
      </div>
      <div className="text-xs mt-1 text-muted-foreground">
        {formatTime(task.start)} - {formatTime(task.end)}
      </div>
    </div>
  );
};

export default TaskBlock;
