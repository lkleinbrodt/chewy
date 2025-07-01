import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UnscheduledTasksSheet } from "@/components/tasks/UnscheduledTasksSheet";
import { useScheduleStatus } from "@/contexts/ScheduleStatusContext";
import { useState } from "react";

export function ScheduleWarning() {
  const { unscheduledTasks } = useScheduleStatus();
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  if (unscheduledTasks.length === 0) return null;

  return (
    <>
      <Alert variant="destructive" className="my-4">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Scheduling Incomplete</AlertTitle>
        <AlertDescription>
          {unscheduledTasks.length} task(s) could not be scheduled.
          <Button
            variant="link"
            className="p-0 ml-2 h-auto"
            onClick={() => setIsSheetOpen(true)}
          >
            View Details
          </Button>
        </AlertDescription>
      </Alert>
      <UnscheduledTasksSheet
        isOpen={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        tasks={unscheduledTasks}
      />
    </>
  );
}
