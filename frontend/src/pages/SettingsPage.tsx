import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FolderOpen, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/useSettings";
import { useToast } from "@/hooks/use-toast";

// Custom interface for File with path property
interface FileWithPath extends File {
  path?: string;
}

const SettingsPage = () => {
  const [calendarDir, setCalendarDir] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const {
    loading: settingsLoading,
    checkCalendarDir,
    setCalendarDir: saveCalendarDir,
  } = useSettings();
  const { toast } = useToast();

  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true);
      const result = await checkCalendarDir();
      if (result.calendar_dir) {
        setCalendarDir(result.calendar_dir);
      }
      setIsLoading(false);
    };

    loadSettings();
  }, []);

  const handleSave = async () => {
    if (!calendarDir.trim()) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Please enter a valid directory path",
      });
      return;
    }

    await saveCalendarDir(calendarDir);
  };

  // Function to handle file input change for directory selection
  const handleFileInputChange = (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = input.files;

    if (files && files.length > 0) {
      const file = files[0] as FileWithPath;

      if (file.path) {
        // Get directory path by removing the filename
        const directoryPath = file.path.substring(
          0,
          file.path.lastIndexOf("/")
        );
        setCalendarDir(directoryPath);
      } else if (file.webkitRelativePath) {
        // Alternative approach using webkitRelativePath
        const relativePath = file.webkitRelativePath;
        const directoryPath = relativePath.substring(
          0,
          relativePath.indexOf("/")
        );
        setCalendarDir(directoryPath);
      }
    }
  };

  const handleBrowse = () => {
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
  };

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Calendar Directory</CardTitle>
          <CardDescription>
            Configure the directory where your calendar JSON files are stored.
            These files contain your calendar events that Chewbacca will use for
            scheduling.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="calendar-dir">Calendar Directory Path</Label>
                <div className="flex gap-2">
                  <Input
                    id="calendar-dir"
                    value={calendarDir}
                    onChange={(e) => setCalendarDir(e.target.value)}
                    placeholder="/path/to/calendar/files"
                    className="flex-1"
                  />
                  <Button variant="outline" onClick={handleBrowse}>
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Browse
                  </Button>
                </div>
              </div>

              <Button onClick={handleSave} disabled={settingsLoading}>
                {settingsLoading && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                <Save className="h-4 w-4 mr-2" />
                Save Settings
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;
