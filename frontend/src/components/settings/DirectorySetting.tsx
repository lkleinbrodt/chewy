import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

interface Directory {
  title: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}

interface DirectorySettingProps {
  directories: Directory[];
  isLoading: boolean;
}

const DirectorySetting = ({
  directories,
  isLoading,
}: DirectorySettingProps) => {
  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Directories</CardTitle>
        <CardDescription className="text-left">
          Configure the directories where your calendar files are stored and
          where tasks will be exported.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            {directories.map((dir) => (
              <div key={dir.title} className="space-y-2">
                <Label
                  htmlFor={`dir-${dir.title
                    .toLowerCase()
                    .replace(/\s+/g, "-")}`}
                >
                  {dir.title} Path
                </Label>
                <Input
                  id={`dir-${dir.title.toLowerCase().replace(/\s+/g, "-")}`}
                  value={dir.value}
                  onChange={(e) => dir.onChange(e.target.value)}
                  placeholder={dir.placeholder}
                  className="flex-1"
                />
              </div>
            ))}
            <p className="text-sm text-muted-foreground">
              Enter the full path to your directories. For example:
              <br />
              - On macOS: /Users/username/Documents/your-directory
              <br />
              - On Windows: C:\Users\username\Documents\your-directory
              <br />- On Linux: /home/username/Documents/your-directory
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DirectorySetting;
