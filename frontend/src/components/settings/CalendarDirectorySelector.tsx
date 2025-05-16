import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FolderOpen, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSettings } from "@/hooks/useSettings";
import { useState } from "react";

interface CalendarDirectorySelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onDirectorySet: () => void;
}

// Define a custom interface for File with path property
interface FileWithPath extends File {
  path?: string; // The path property that some browsers provide
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

  // Function to handle file input change for directory selection
  const handleFileInputChange = (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = input.files;

    if (files && files.length > 0) {
      // For directory selection, we get the path from the first file
      // and extract the directory path
      const file = files[0] as FileWithPath;

      if (file.path) {
        // Get directory path by removing the filename
        const directoryPath = file.path.substring(
          0,
          file.path.lastIndexOf("/")
        );
        setDirectory(directoryPath);
      } else if (file.webkitRelativePath) {
        // Alternative approach using webkitRelativePath
        const relativePath = file.webkitRelativePath;
        const directoryPath = relativePath.substring(
          0,
          relativePath.indexOf("/")
        );
        setDirectory(directoryPath);
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Calendar Directory Setup</DialogTitle>
          <DialogDescription>
            Please select the directory where your calendar JSON files are
            stored. These files contain your calendar events that Chewbacca will
            use for scheduling.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="flex items-center gap-2">
            <Input
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="Path to calendar directory"
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                // Create a file input element to select a directory
                const input = document.createElement("input");
                input.type = "file";
                // Use setAttribute for non-standard attributes
                input.setAttribute("webkitdirectory", "true");
                input.setAttribute("directory", "true");
                input.multiple = true;

                // Listen for changes
                input.onchange = handleFileInputChange;

                // Trigger the file dialog
                input.click();
              }}
            >
              <FolderOpen className="h-4 w-4 mr-2" />
              Browse
            </Button>
          </div>

          <p className="text-sm text-muted-foreground">
            The directory should contain JSON files exported from your calendar
            application.
          </p>
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
