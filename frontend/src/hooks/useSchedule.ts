import { useCallback, useState } from "react";

import { handleApiErrorWithToast } from "@/utils/errorUtils";
import scheduleService from "@/services/scheduleService";
import { toast } from "@/hooks/use-toast";
import { useCalendar } from "./useCalendar";
import { useScheduleStatus } from "@/contexts/ScheduleStatusContext";
import { useTasks } from "./useTasks";

/**
 * Hook for managing schedule generation state
 * Only regenerates the schedule when explicitly called
 */
export function useSchedule() {
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { syncCalendar } = useCalendar();
  const { setTasksManually } = useTasks();
  const { setUnscheduledTasks } = useScheduleStatus();

  const generateSchedule = useCallback(
    async (forceSyncCalendar = true, showSuccessToast = true) => {
      setIsGenerating(true);
      setError(null);
      setUnscheduledTasks([]); // Clear old failures

      if (forceSyncCalendar) {
        const syncResult = await syncCalendar();
        if (!syncResult.success) {
          setIsGenerating(false);
          if (syncResult.needsDirectorySetup) {
            return {
              success: false,
              updatedTasks: null,
              error: "CALENDAR_DIR_NOT_SET",
              needsDirectorySetup: true,
            };
          }
          setError("Calendar sync failed. Schedule generation aborted.");
          return { success: false, updatedTasks: null, error: "SYNC_FAILED" };
        }
      }

      try {
        const response = await scheduleService.generateSchedule();
        if (
          response.unscheduled_tasks &&
          response.unscheduled_tasks.length > 0
        ) {
          setUnscheduledTasks(response.unscheduled_tasks);
        }
        setTasksManually(response.scheduled_tasks);

        // Show success toast only if requested
        if (showSuccessToast) {
          toast({
            title: "Schedule Updated",
            description:
              "Your calendar has been successfully updated with the new schedule.",
          });
        }

        return { success: true, ...response };
      } catch (err) {
        const errorMessage = "Failed to generate schedule. Please try again.";
        setError(errorMessage);
        console.error("Error generating schedule:", err);
        handleApiErrorWithToast(err, "generating schedule");
        return {
          success: false,
          updatedTasks: null,
          error: "GENERATION_FAILED",
        };
      } finally {
        setIsGenerating(false);
      }
    },
    [syncCalendar, setTasksManually, setUnscheduledTasks]
  );

  return {
    isGenerating,
    error,
    generateSchedule,
  };
}
