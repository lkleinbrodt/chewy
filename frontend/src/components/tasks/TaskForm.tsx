import "react-datepicker/dist/react-datepicker.css";

import * as Yup from "yup";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type {
  OneOffTaskFormData,
  RecurringTaskFormData,
  Task,
} from "@/types/task";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import DatePicker from "react-datepicker";
import DependencySelector from "./DependencySelector";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { dateUtils } from "@/utils/dateUtils";
import { useFormik } from "formik";
import { useState } from "react";

// Validation schemas
const oneOffTaskSchema = Yup.object({
  content: Yup.string()
    .required("Task content is required")
    .min(3, "Task description must be at least 3 characters")
    .max(200, "Task description cannot exceed 200 characters"),
  duration: Yup.number()
    .required("Duration is required")
    .positive("Duration must be positive")
    .max(1440, "Task duration cannot exceed 24 hours (1440 minutes)"),
  due_by: Yup.date()
    .required("Due date is required")
    .min(dateUtils.getNow(), "Due date cannot be in the past"),
  include_time: Yup.boolean(),
  dependencies: Yup.array().of(Yup.string()),
  is_completed: Yup.boolean(),
});

// Validation schema for recurring tasks
const recurringTaskSchema = Yup.object({
  content: Yup.string()
    .required("Task content is required")
    .min(3, "Task description must be at least 3 characters")
    .max(200, "Task description cannot exceed 200 characters"),
  duration: Yup.number()
    .required("Duration is required")
    .positive("Duration must be positive")
    .max(1440, "Task duration cannot exceed 24 hours (1440 minutes)"),
  task_type: Yup.string()
    .oneOf(["recurring"], "Invalid task type")
    .required("Task type is required"),
  recurrence: Yup.object({
    type: Yup.string()
      .oneOf(["daily", "weekly"], "Invalid recurrence type")
      .required("Recurrence type is required"),
    days: Yup.array().when("type", {
      is: "weekly",
      then: (schema) =>
        schema
          .of(Yup.string())
          .min(1, "Select at least one day of the week")
          .required("Days are required for weekly recurrence"),
      otherwise: (schema) => schema.notRequired(),
    }),
  }).required("Recurrence pattern is required"),
  time_window_start: Yup.string().nullable(),
  time_window_end: Yup.string()
    .nullable()
    .when("time_window_start", {
      is: (value: string) => value && value.length > 0,
      then: (schema) =>
        schema.required("End time is required when start time is specified"),
      otherwise: (schema) => schema.nullable(),
    }),
  is_active: Yup.boolean(),
}).test(
  "time-window-valid-range",
  "End time must be after start time",
  function (value) {
    if (value.time_window_start && value.time_window_end) {
      const [startHours, startMinutes] = value.time_window_start
        .split(":")
        .map(Number);
      const [endHours, endMinutes] = value.time_window_end
        .split(":")
        .map(Number);

      const startTotalMinutes = startHours * 60 + startMinutes;
      const endTotalMinutes = endHours * 60 + endMinutes;

      return endTotalMinutes > startTotalMinutes;
    }
    return true;
  }
);

// Days of the week for selection
const weekDays = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
];

interface TaskFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: OneOffTaskFormData | RecurringTaskFormData) => Promise<void>;
  initialData?: Task;
  availableTasks: Task[];
}

const TaskForm = ({
  open,
  onClose,
  onSubmit,
  initialData,
  availableTasks,
}: TaskFormProps) => {
  const [taskType, setTaskType] = useState<"one-off" | "recurring">(
    initialData?.task_type || "one-off"
  );

  // Initial values for one-off tasks
  const initialOneOffValues: OneOffTaskFormData = {
    content: initialData?.content || "",
    duration: initialData?.duration || 30,
    task_type: "one-off",
    due_by:
      initialData?.task_type === "one-off"
        ? dateUtils.parseUtcISOString(initialData.due_by) || dateUtils.getNow()
        : dateUtils.getNow(),
    include_time:
      initialData?.task_type === "one-off"
        ? Boolean(
            initialData.due_by &&
              dateUtils.parseUtcISOString(initialData.due_by)?.getHours() !== 0
          )
        : false,
    dependencies:
      initialData?.task_type === "one-off" ? initialData.dependencies : [],
    is_completed: initialData?.is_completed || false,
  };

  // Initial values for recurring tasks
  const initialRecurringValues: RecurringTaskFormData = {
    content: initialData?.content || "",
    duration: initialData?.duration || 30,
    task_type: "recurring",
    recurrence:
      initialData?.task_type === "recurring"
        ? initialData.recurrence
        : { type: "daily" },
    time_window_start:
      initialData?.task_type === "recurring"
        ? initialData.time_window_start || ""
        : "",
    time_window_end:
      initialData?.task_type === "recurring"
        ? initialData.time_window_end || ""
        : "",
    is_active:
      initialData?.task_type === "recurring" ? initialData.is_active : true,
  };

  // One-off task form
  const oneOffFormik = useFormik({
    initialValues: initialOneOffValues,
    validationSchema: oneOffTaskSchema,
    onSubmit: async (values) => {
      try {
        // The formatTaskForApi function will convert the Date to ISO string
        await onSubmit(values);
        // Reset form to initial values
        oneOffFormik.resetForm({
          values: {
            content: "",
            duration: 30,
            task_type: "one-off",
            due_by: dateUtils.getNow(),
            include_time: false,
            dependencies: [],
            is_completed: false,
          },
        });
        onClose();
      } catch (error) {
        // Handle submission error
        console.error("Error submitting form:", error);
      }
    },
    validateOnChange: true,
    validateOnBlur: true,
  });

  // Recurring task form
  const recurringFormik = useFormik({
    initialValues: initialRecurringValues,
    validationSchema: recurringTaskSchema,
    onSubmit: async (values) => {
      try {
        await onSubmit(values);
        // Reset form to initial values
        recurringFormik.resetForm({
          values: {
            content: "",
            duration: 30,
            task_type: "recurring",
            recurrence: { type: "daily" },
            time_window_start: "",
            time_window_end: "",
            is_active: true,
          },
        });
        onClose();
      } catch (error) {
        // Handle submission error
        console.error("Error submitting form:", error);
      }
    },
    validateOnChange: true,
    validateOnBlur: true,
  });

  // Helper for duration formatting
  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return { hours, minutes: mins };
  };

  // Convert hours and minutes to total minutes
  const calculateTotalMinutes = (hours: number, minutes: number) => {
    return hours * 60 + minutes;
  };

  // Handle duration changes for one-off tasks
  const handleOneOffDurationChange = (hours: string, minutes: string) => {
    const totalMinutes = calculateTotalMinutes(
      parseInt(hours) || 0,
      parseInt(minutes) || 0
    );
    oneOffFormik.setFieldValue("duration", totalMinutes);
  };

  // Handle duration changes for recurring tasks
  const handleRecurringDurationChange = (hours: string, minutes: string) => {
    const totalMinutes = calculateTotalMinutes(
      parseInt(hours) || 0,
      parseInt(minutes) || 0
    );
    recurringFormik.setFieldValue("duration", totalMinutes);
  };

  const oneOffDuration = formatDuration(oneOffFormik.values.duration);
  const recurringDuration = formatDuration(recurringFormik.values.duration);

  // Handle DatePicker change for one-off tasks
  const handleDateChange = (date: Date | null) => {
    if (date) {
      oneOffFormik.setFieldValue("due_by", date);
    } else {
      oneOffFormik.setFieldValue("due_by", dateUtils.getNow());
    }
  };

  const handleTimeToggle = (includeTime: boolean) => {
    oneOffFormik.setFieldValue("include_time", includeTime);

    // If toggling to not include time, set time to midnight
    if (!includeTime) {
      const currentDate = oneOffFormik.values.due_by;
      const midnightDate = new Date(currentDate);
      // Set to 12:01 AM local time (will be converted to UTC when sent to backend)
      midnightDate.setHours(0, 1, 0, 0);
      oneOffFormik.setFieldValue("due_by", midnightDate);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen: boolean) => !isOpen && onClose()}
    >
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Edit Task" : "Create New Task"}
          </DialogTitle>
          <DialogDescription>
            {initialData
              ? "Update task details below"
              : "Add a new task to your list"}
          </DialogDescription>
        </DialogHeader>

        <Tabs
          defaultValue={taskType}
          onValueChange={(value) =>
            setTaskType(value as "one-off" | "recurring")
          }
          className="w-full"
        >
          <TabsList className="grid grid-cols-2 mb-4">
            <TabsTrigger value="one-off">One-off Task</TabsTrigger>
            <TabsTrigger value="recurring">Recurring Task</TabsTrigger>
          </TabsList>

          {/* One-off Task Form */}
          <TabsContent value="one-off">
            <form onSubmit={oneOffFormik.handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="content">Task Description</Label>
                <Input
                  id="content"
                  name="content"
                  placeholder="What needs to be done?"
                  onChange={oneOffFormik.handleChange}
                  onBlur={oneOffFormik.handleBlur}
                  value={oneOffFormik.values.content}
                  className={
                    oneOffFormik.touched.content && oneOffFormik.errors.content
                      ? "border-red-500"
                      : ""
                  }
                />
                {oneOffFormik.touched.content &&
                  oneOffFormik.errors.content && (
                    <p className="text-sm text-red-500">
                      {oneOffFormik.errors.content}
                    </p>
                  )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="due_by">Due Date</Label>
                  <DatePicker
                    selected={oneOffFormik.values.due_by}
                    onChange={handleDateChange}
                    className={`w-full rounded-md border ${
                      oneOffFormik.touched.due_by && oneOffFormik.errors.due_by
                        ? "border-red-500"
                        : "border-input"
                    } bg-transparent px-3 py-2`}
                    dateFormat={
                      oneOffFormik.values.include_time
                        ? "MMMM d, yyyy h:mm aa"
                        : "MMMM d, yyyy"
                    }
                    showTimeSelect={oneOffFormik.values.include_time}
                    timeFormat="h:mm aa"
                    timeIntervals={15}
                    placeholderText="Select due date"
                    minDate={new Date()}
                  />
                  <div className="flex items-center mt-1 space-x-2">
                    <Checkbox
                      id="include-time"
                      checked={oneOffFormik.values.include_time}
                      onCheckedChange={(checked) =>
                        handleTimeToggle(Boolean(checked))
                      }
                    />
                    <Label htmlFor="include-time" className="text-sm">
                      Include specific time
                    </Label>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {oneOffFormik.values.include_time
                      ? "Task will be due at the exact date and time specified."
                      : "Task will be due at 12:01 AM on the selected date."}
                  </p>
                  {oneOffFormik.touched.due_by &&
                    oneOffFormik.errors.due_by && (
                      <p className="text-sm text-red-500">
                        {String(oneOffFormik.errors.due_by)}
                      </p>
                    )}
                </div>

                <div className="space-y-2">
                  <Label>Duration</Label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      placeholder="Hours"
                      min="0"
                      value={oneOffDuration.hours}
                      onChange={(e) =>
                        handleOneOffDurationChange(
                          e.target.value,
                          oneOffDuration.minutes.toString()
                        )
                      }
                      className={`flex-1 ${
                        oneOffFormik.touched.duration &&
                        oneOffFormik.errors.duration
                          ? "border-red-500"
                          : ""
                      }`}
                    />
                    <Input
                      type="number"
                      placeholder="Minutes"
                      min="0"
                      max="59"
                      value={oneOffDuration.minutes}
                      onChange={(e) =>
                        handleOneOffDurationChange(
                          oneOffDuration.hours.toString(),
                          e.target.value
                        )
                      }
                      className={`flex-1 ${
                        oneOffFormik.touched.duration &&
                        oneOffFormik.errors.duration
                          ? "border-red-500"
                          : ""
                      }`}
                    />
                  </div>
                  {oneOffFormik.touched.duration &&
                    oneOffFormik.errors.duration && (
                      <p className="text-sm text-red-500">
                        {String(oneOffFormik.errors.duration)}
                      </p>
                    )}
                </div>
              </div>

              {/* Dependencies selector for one-off tasks */}
              <div className="space-y-2">
                <Label htmlFor="dependencies">Dependencies</Label>
                <DependencySelector
                  selectedDependencies={oneOffFormik.values.dependencies || []}
                  onChange={(deps) =>
                    oneOffFormik.setFieldValue("dependencies", deps)
                  }
                  availableTasks={availableTasks}
                  currentTaskId={initialData?.id}
                />
              </div>

              <DialogFooter>
                <Button type="submit" disabled={oneOffFormik.isSubmitting}>
                  {initialData ? "Update Task" : "Create Task"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          {/* Recurring Task Form */}
          <TabsContent value="recurring">
            <form onSubmit={recurringFormik.handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="recurring-content">Task Description</Label>
                <Input
                  id="recurring-content"
                  name="content"
                  placeholder="What needs to be done?"
                  onChange={recurringFormik.handleChange}
                  onBlur={recurringFormik.handleBlur}
                  value={recurringFormik.values.content}
                  className={
                    recurringFormik.touched.content &&
                    recurringFormik.errors.content
                      ? "border-red-500"
                      : ""
                  }
                />
                {recurringFormik.touched.content &&
                  recurringFormik.errors.content && (
                    <p className="text-sm text-red-500">
                      {recurringFormik.errors.content}
                    </p>
                  )}
              </div>

              <div className="space-y-2">
                <Label>Duration</Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Hours"
                    min="0"
                    value={recurringDuration.hours}
                    onChange={(e) =>
                      handleRecurringDurationChange(
                        e.target.value,
                        recurringDuration.minutes.toString()
                      )
                    }
                    className={`flex-1 ${
                      recurringFormik.touched.duration &&
                      recurringFormik.errors.duration
                        ? "border-red-500"
                        : ""
                    }`}
                  />
                  <Input
                    type="number"
                    placeholder="Minutes"
                    min="0"
                    max="59"
                    value={recurringDuration.minutes}
                    onChange={(e) =>
                      handleRecurringDurationChange(
                        recurringDuration.hours.toString(),
                        e.target.value
                      )
                    }
                    className={`flex-1 ${
                      recurringFormik.touched.duration &&
                      recurringFormik.errors.duration
                        ? "border-red-500"
                        : ""
                    }`}
                  />
                </div>
                {recurringFormik.touched.duration &&
                  recurringFormik.errors.duration && (
                    <p className="text-sm text-red-500">
                      {String(recurringFormik.errors.duration)}
                    </p>
                  )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="recurrence-type">Recurrence Pattern</Label>
                <Select
                  value={recurringFormik.values.recurrence.type}
                  onValueChange={(value) =>
                    recurringFormik.setFieldValue("recurrence.type", value)
                  }
                >
                  <SelectTrigger
                    id="recurrence-type"
                    className={
                      recurringFormik.touched.recurrence?.type &&
                      recurringFormik.errors.recurrence?.type
                        ? "border-red-500"
                        : ""
                    }
                  >
                    <SelectValue placeholder="Select recurrence pattern" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly (Select Days)</SelectItem>
                  </SelectContent>
                </Select>
                {recurringFormik.touched.recurrence?.type &&
                  recurringFormik.errors.recurrence?.type && (
                    <p className="text-sm text-red-500">
                      {String(recurringFormik.errors.recurrence.type)}
                    </p>
                  )}
              </div>

              {recurringFormik.values.recurrence.type === "weekly" && (
                <div className="space-y-2">
                  <Label>Days of Week</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {weekDays.map((day) => (
                      <div
                        key={day.value}
                        className="flex items-center space-x-2"
                      >
                        <Checkbox
                          id={`day-${day.value}`}
                          checked={recurringFormik.values.recurrence.days?.includes(
                            day.value
                          )}
                          onCheckedChange={(checked: boolean) => {
                            const currentDays =
                              recurringFormik.values.recurrence.days || [];
                            const newDays = checked
                              ? [...currentDays, day.value]
                              : currentDays.filter((d) => d !== day.value);
                            recurringFormik.setFieldValue(
                              "recurrence.days",
                              newDays
                            );
                          }}
                        />
                        <Label htmlFor={`day-${day.value}`} className="text-sm">
                          {day.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label>Preferred Time Window (Optional)</Label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label htmlFor="start-time" className="text-xs">
                      Start Time
                    </Label>
                    <Input
                      id="start-time"
                      type="time"
                      value={recurringFormik.values.time_window_start || ""}
                      onChange={(e) =>
                        recurringFormik.setFieldValue(
                          "time_window_start",
                          e.target.value || ""
                        )
                      }
                      className={
                        recurringFormik.errors.time_window_start &&
                        recurringFormik.touched.time_window_start
                          ? "border-red-500"
                          : ""
                      }
                    />
                    {recurringFormik.errors.time_window_start &&
                      recurringFormik.touched.time_window_start && (
                        <p className="text-sm text-red-500">
                          {String(recurringFormik.errors.time_window_start)}
                        </p>
                      )}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="end-time" className="text-xs">
                      End Time
                    </Label>
                    <Input
                      id="end-time"
                      type="time"
                      value={recurringFormik.values.time_window_end || ""}
                      onChange={(e) =>
                        recurringFormik.setFieldValue(
                          "time_window_end",
                          e.target.value || ""
                        )
                      }
                      className={
                        recurringFormik.errors.time_window_end &&
                        recurringFormik.touched.time_window_end
                          ? "border-red-500"
                          : ""
                      }
                    />
                    {recurringFormik.errors.time_window_end &&
                      recurringFormik.touched.time_window_end && (
                        <p className="text-sm text-red-500">
                          {String(recurringFormik.errors.time_window_end)}
                        </p>
                      )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Specify the preferred time range for this task (using your
                  local time).
                </p>
              </div>

              <DialogFooter>
                <Button type="submit" disabled={recurringFormik.isSubmitting}>
                  {initialData ? "Update Task" : "Create Task"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

export default TaskForm;
