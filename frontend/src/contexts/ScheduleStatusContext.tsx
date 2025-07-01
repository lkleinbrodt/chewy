import type { Task } from "@/types/task";
import { type ReactNode, createContext, useContext, useState } from "react";

export interface UnscheduledTaskInfo {
  task: Task;
  reason: string;
}

interface ScheduleStatusContextType {
  unscheduledTasks: UnscheduledTaskInfo[];
  setUnscheduledTasks: (tasks: UnscheduledTaskInfo[]) => void;
}

const ScheduleStatusContext = createContext<
  ScheduleStatusContextType | undefined
>(undefined);

export function ScheduleStatusProvider({ children }: { children: ReactNode }) {
  const [unscheduledTasks, setUnscheduledTasks] = useState<
    UnscheduledTaskInfo[]
  >([]);

  return (
    <ScheduleStatusContext.Provider
      value={{ unscheduledTasks, setUnscheduledTasks }}
    >
      {children}
    </ScheduleStatusContext.Provider>
  );
}

export function useScheduleStatus() {
  const context = useContext(ScheduleStatusContext);
  if (context === undefined)
    throw new Error(
      "useScheduleStatus must be used within a ScheduleStatusProvider"
    );
  return context;
}
