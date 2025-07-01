import { Card, CardContent } from "@/components/ui/card";
import { formatEventTime, getEventTypeStyles } from "@/utils/calendarUtils";

import { Badge } from "@/components/ui/badge";
import type { CalendarEvent } from "@/types/calendar";
import { cn } from "@/lib/utils";

interface EventBlockProps {
  event: CalendarEvent;
  onClick: (event: CalendarEvent) => void;
  style?: React.CSSProperties;
  className?: string;
}

const EventBlock = ({ event, onClick, style, className }: EventBlockProps) => {
  const typeStyles = getEventTypeStyles(event);
  const { startFormatted, endFormatted } = formatEventTime(
    event.start,
    event.end
  );

  return (
    <Card
      className={cn(
        "absolute w-[calc(100%-8px)] overflow-hidden cursor-pointer shadow-sm rounded-sm pointer-events-auto",
        className
      )}
      style={{
        ...typeStyles,
        ...style,
      }}
      onClick={() => onClick(event)}
    >
      <CardContent className="px-2 py-1 text-xs text-left">
        <div className="font-semibold truncate text-left">{event.subject}</div>
        <div className="truncate text-left">
          {startFormatted} - {endFormatted}
          {event.is_chewy_managed && (
            <Badge variant="secondary" className="ml-1 text-[10px] py-0.5">
              Chewy
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default EventBlock;
