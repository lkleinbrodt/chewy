import { appConfig } from "@/constants/appConfig";

interface TimeGridProps {
  startHour?: number;
  endHour?: number;
}

const TimeGrid = ({
  startHour = appConfig.calendar.workingHours.start,
  endHour = appConfig.calendar.workingHours.end,
}: TimeGridProps) => {
  // Generate time slots (1-hour intervals)
  const hours = Array.from(
    { length: endHour - startHour },
    (_, i) => startHour + i
  );

  return (
    <div className="w-16 relative border-r pr-2 text-right">
      {/* Empty space for day header alignment */}
      <div className="h-12 border-b"></div>

      {/* Hour labels - positioned to align with the top of each hour slot */}
      <div className="relative h-[calc(100%-3rem)]">
        {hours.map((hour) => (
          <div key={hour} className="h-16 flex items-start justify-end">
            <span className="text-xs text-muted-foreground mt-0 pt-0">
              {hour}:00
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TimeGrid;
