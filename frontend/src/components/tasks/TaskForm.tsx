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
import type { Task, TaskFormData } from "@/types/task";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import type { CheckedState } from "@radix-ui/react-checkbox";
import DatePicker from "react-datepicker";
import DependencySelector from "./DependencySelector";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { dateUtils } from "@/utils/dateUtils";
import { useFormik } from "formik";

// Validation schema
const taskSchema = Yup.object({
  content: Yup.string()
    .required("Task content is required")
    .min(3, "Task description must be at least 3 characters")
    .max(200, "Task description cannot exceed 200 characters"),
  duration: Yup.number()
    .required("Duration is required")
    .positive("Duration must be positive")
    .max(1440, "Task duration cannot exceed 24 hours (1440 minutes)"),
  is_completed: Yup.boolean(),
  is_recurring_ui_flag: Yup.boolean(),

  // One-off task fields
  due_by: Yup.date().when("is_recurring_ui_flag", {
    is: false,
    then: (schema) =>
      schema
        .required("Due date is required")
        .min(dateUtils.getNow(), "Due date cannot be in the past"),
    otherwise: (schema) => schema.nullable(),
  }),
  include_time: Yup.boolean(),
  dependencies: Yup.array().of(Yup.string()),

  // Recurring task fields
  recurrence_days: Yup.array()
    .of(Yup.number().min(0).max(6))
    .when("is_recurring_ui_flag", {
      is: true,
      then: (schema) =>
        schema
          .min(1, "Select at least one day of the week")
          .required("Days are required for recurring tasks"),
      otherwise: (schema) => schema.notRequired(),
    }),
  time_window_start: Yup.string().nullable(),
  time_window_end: Yup.string()
    .nullable()
    .when("time_window_start", {
      is: (value: string) => value && value.length > 0,
      then: (schema) =>
        schema.required("End time is required when start time is specified"),
      otherwise: (schema) => schema.nullable(),
    }),
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
  { value: 0, label: "Monday", abbr: "M" },
  { value: 1, label: "Tuesday", abbr: "T" },
  { value: 2, label: "Wednesday", abbr: "W" },
  { value: 3, label: "Thursday", abbr: "T" },
  { value: 4, label: "Friday", abbr: "F" },
];

interface TaskFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: TaskFormData) => Promise<void>;
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
  // Determine if the task is recurring based on the recurrence field
  const isRecurring =
    initialData?.recurrence && initialData.recurrence.length > 0;

  // Initial values for the form
  const initialValues: TaskFormData = {
    content: initialData?.content || "",
    duration: initialData?.duration || 30,
    is_completed: initialData?.is_completed || false,
    status: initialData?.status || "unscheduled",
    is_recurring_ui_flag: isRecurring,

    // One-off task fields
    due_by: isRecurring
      ? null
      : initialData?.due_by
      ? new Date(initialData.due_by)
      : dateUtils.addDays(dateUtils.getNow(), 1),
    include_time: isRecurring
      ? false
      : Boolean(
          initialData?.due_by && new Date(initialData.due_by).getHours() !== 0
        ),
    dependencies: isRecurring ? [] : initialData?.dependencies || [],

    // Recurring task fields
    recurrence_days: isRecurring ? initialData?.recurrence || [] : [],
    time_window_start: isRecurring
      ? initialData?.time_window_start || null
      : null,
    time_window_end: isRecurring ? initialData?.time_window_end || null : null,
  };

  const formik = useFormik({
    initialValues,
    validationSchema: taskSchema,
    onSubmit: async (values) => {
      try {
        await onSubmit(values);
        formik.resetForm();
        onClose();
      } catch (error) {
        console.error("Error submitting form:", error);
      }
    },
    validateOnChange: true,
    validateOnBlur: true,
  });

  // A clean cancel that doesn't trigger validation
  const handleCancel = () => {
    // Bypass validation entirely
    formik.setErrors({});
    formik.resetForm();
    onClose();
  };

  // Helper for duration formatting
  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return { hours, minutes: mins };
  };

  const calculateTotalMinutes = (hours: number, minutes: number) => {
    return hours * 60 + minutes;
  };

  const handleDurationChange = (hours: string, minutes: string) => {
    const totalMinutes = calculateTotalMinutes(
      parseInt(hours) || 0,
      parseInt(minutes) || 0
    );
    formik.setFieldValue("duration", totalMinutes);
  };

  const handleDateChange = (date: Date | null) => {
    if (date) {
      formik.setFieldValue("due_by", date);
    }
  };

  const handleTimeToggle = (checked: CheckedState) => {
    formik.setFieldValue("include_time", Boolean(checked));
    if (!checked && formik.values.due_by) {
      // Reset time to midnight if time is not included
      const date = new Date(formik.values.due_by);
      date.setHours(0, 0, 0, 0);
      formik.setFieldValue("due_by", date);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) handleCancel();
      }}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Edit Task" : "Create New Task"}
          </DialogTitle>
          <DialogDescription>
            Fill in the task details below. Required fields are marked with an
            asterisk (*).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={formik.handleSubmit} className="space-y-6">
          {/* Common Fields */}
          <div className="space-y-4">
            {/* Task Content */}
            <div className="space-y-2">
              <Label htmlFor="content">
                Task Description <span className="text-red-500">*</span>
              </Label>
              <Input
                id="content"
                {...formik.getFieldProps("content")}
                className={
                  formik.touched.content && formik.errors.content
                    ? "border-red-500"
                    : ""
                }
              />
              {formik.touched.content && formik.errors.content && (
                <p className="text-sm text-red-500">{formik.errors.content}</p>
              )}
            </div>

            {/* Duration */}
            <div className="space-y-2">
              <Label htmlFor="duration-hours">
                Duration <span className="text-red-500">*</span>
              </Label>
              <div className="flex items-center space-x-2">
                <Input
                  id="duration-hours"
                  type="number"
                  min="0"
                  max="24"
                  value={formatDuration(formik.values.duration).hours}
                  onChange={(e) =>
                    handleDurationChange(
                      e.target.value,
                      formatDuration(formik.values.duration).minutes.toString()
                    )
                  }
                  className="w-20"
                />
                <span>hours</span>
                <Input
                  id="duration-minutes"
                  type="number"
                  min="0"
                  max="59"
                  value={formatDuration(formik.values.duration).minutes}
                  onChange={(e) =>
                    handleDurationChange(
                      formatDuration(formik.values.duration).hours.toString(),
                      e.target.value
                    )
                  }
                  className="w-20"
                />
                <span>minutes</span>
              </div>
              {formik.touched.duration && formik.errors.duration && (
                <p className="text-sm text-red-500">{formik.errors.duration}</p>
              )}
            </div>

            {/* Task Type Toggle */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Switch
                  id="is-recurring"
                  checked={formik.values.is_recurring_ui_flag}
                  onCheckedChange={(checked: boolean) => {
                    formik.setFieldValue("is_recurring_ui_flag", checked);
                    if (checked) {
                      // Clear one-off fields
                      formik.setFieldValue("due_by", null);
                      formik.setFieldValue("dependencies", []);
                      // When enabling recurring, validate immediately if form was previously touched
                      if (formik.dirty) {
                        formik.validateField("recurrence_days");
                      }
                    } else {
                      // Clear recurring fields
                      formik.setFieldValue("recurrence_days", []);
                      formik.setFieldValue("time_window_start", null);
                      formik.setFieldValue("time_window_end", null);
                      // When disabling recurring, validate immediately if form was previously touched
                      if (formik.dirty) {
                        formik.validateField("due_by");
                      }
                    }
                  }}
                />
                <Label htmlFor="is-recurring">This is a recurring task</Label>
              </div>
            </div>

            {/* Conditional Fields */}
            {formik.values.is_recurring_ui_flag ? (
              // Recurring Task Fields
              <div className="space-y-4">
                {/* Recurrence Days */}
                <div className="space-y-2">
                  <Label htmlFor="recurrence-days">
                    Days <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      {weekDays.map((day) => (
                        <div
                          key={day.value}
                          className={`flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border transition-colors ${
                            formik.values.recurrence_days?.includes(day.value)
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-input hover:bg-muted/50"
                          } ${
                            formik.touched.recurrence_days &&
                            formik.errors.recurrence_days &&
                            formik.values.recurrence_days?.length === 0
                              ? "border-red-500"
                              : ""
                          }`}
                          onClick={() => {
                            const currentDays =
                              formik.values.recurrence_days || [];
                            const newDays = currentDays.includes(day.value)
                              ? currentDays.filter((d) => d !== day.value)
                              : [...currentDays, day.value];
                            formik.setFieldValue("recurrence_days", newDays);
                          }}
                          title={day.label}
                        >
                          {day.abbr}
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-primary"
                      onClick={() => {
                        formik.setFieldValue(
                          "recurrence_days",
                          weekDays.map((day) => day.value)
                        );
                      }}
                    >
                      Daily
                    </button>
                  </div>
                  {formik.touched.recurrence_days &&
                    formik.errors.recurrence_days && (
                      <p className="text-sm text-red-500">
                        {formik.errors.recurrence_days}
                      </p>
                    )}
                </div>

                {/* Time Window */}
                <div className="space-y-2">
                  <Label>Time Window (Optional)</Label>
                  <div className="flex items-center space-x-2">
                    <Input
                      type="time"
                      {...formik.getFieldProps("time_window_start")}
                      className="w-32"
                    />
                    <span>to</span>
                    <Input
                      type="time"
                      {...formik.getFieldProps("time_window_end")}
                      className="w-32"
                    />
                  </div>
                  {formik.touched.time_window_end &&
                    formik.errors.time_window_end && (
                      <p className="text-sm text-red-500">
                        {formik.errors.time_window_end}
                      </p>
                    )}
                </div>
              </div>
            ) : (
              // One-off Task Fields
              <div className="space-y-4">
                {/* Due Date */}
                <div className="space-y-2">
                  <Label htmlFor="due-by">
                    Due Date <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex flex-col space-y-2">
                    <DatePicker
                      selected={formik.values.due_by}
                      onChange={handleDateChange}
                      showTimeSelect={formik.values.include_time}
                      dateFormat={
                        formik.values.include_time
                          ? "MMMM d, yyyy h:mm aa"
                          : "MMMM d, yyyy"
                      }
                      className="w-full rounded-md border p-2"
                    />
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="include-time"
                        checked={formik.values.include_time}
                        onCheckedChange={handleTimeToggle}
                      />
                      <Label htmlFor="include-time">Include time</Label>
                    </div>
                  </div>
                  {formik.touched.due_by && formik.errors.due_by && (
                    <p className="text-sm text-red-500">
                      {formik.errors.due_by}
                    </p>
                  )}
                </div>

                {/* Dependencies */}
                <div className="space-y-2">
                  <Label htmlFor="dependencies">Dependencies (Optional)</Label>
                  <DependencySelector
                    availableTasks={availableTasks.filter(
                      (t) =>
                        (!t.recurrence || t.recurrence.length === 0) &&
                        (!initialData || t.id !== initialData.id)
                    )}
                    selectedTaskIds={formik.values.dependencies || []}
                    onChange={(dependencies) =>
                      formik.setFieldValue("dependencies", dependencies)
                    }
                  />
                </div>
              </div>
            )}

            {/* Completed Status */}
            {initialData && (
              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  id="is-completed"
                  checked={formik.values.is_completed}
                  onCheckedChange={(checked) => {
                    formik.setFieldValue("is_completed", checked);
                    // When changing completion status, also set the status field
                    formik.setFieldValue(
                      "status",
                      checked ? "completed" : "unscheduled"
                    );
                  }}
                />
                <Label htmlFor="is-completed">Task is completed</Label>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={formik.isSubmitting}>
              {initialData ? "Update Task" : "Create Task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default TaskForm;
