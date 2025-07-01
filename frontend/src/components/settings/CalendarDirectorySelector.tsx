import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";
import { useSettings } from "@/hooks/useSettings";
import { useState } from "react";

interface CalendarDirectorySelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onDirectorySet: () => void;
}

const CalendarDirectorySelector = ({
  isOpen,
  onClose,
  onDirectorySet,
}: CalendarDirectorySelectorProps) => {
  const [directory, setDirectory] = useState("");
  const { loading, setCalendarDir } = useSettings();

  const handleSubmit = async () => {
    if (!directory.trim()) return;

    const success = await setCalendarDir(directory);
    if (success) {
      setDirectory("");
      onClose();
      onDirectorySet();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Calendar Directory Setup</DialogTitle>
          <DialogDescription>
            Please enter the full path to the directory where your calendar JSON
            files are stored. These files contain your calendar events that
            Chewbacca will use for scheduling.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Input
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="/Users/username/path/to/calendar/files"
              className="flex-1"
            />
            <p className="text-sm text-muted-foreground">
              Enter the full path to your calendar directory. For example:
              <br />
              - On macOS: /Users/username/Documents/calendar
              <br />
              - On Windows: C:\Users\username\Documents\calendar
              <br />- On Linux: /home/username/Documents/calendar
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={!directory.trim() || loading}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Set Directory
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CalendarDirectorySelector;
