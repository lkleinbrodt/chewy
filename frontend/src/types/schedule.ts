/**
 * Interface for scheduled tasks
 */
export interface ScheduledTask {
  id: string;
  task_id: string;
  task_content: string;
  start: string | Date;
  end: string | Date;
  status: string;
  duration: number;
}

/**
 * Interface for schedule generation response
 */
export interface ScheduleGenerationResponse {
  message: string;
  scheduled_tasks: ScheduledTask[];
}
