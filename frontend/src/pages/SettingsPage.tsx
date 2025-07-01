import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import DirectorySetting from "@/components/settings/DirectorySetting";
import { Label } from "@/components/ui/label";
import type { Objectives } from "@/types/objectives";
import { RotateCcw } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { objectiveConfig } from "@/types/objectives";
import settingsService from "@/services/settingsService";
import { useSettings } from "@/hooks/useSettings";
import { useToast } from "@/hooks/use-toast";

const SettingsPage = () => {
  const [calendarDir, setCalendarDir] = useState("");
  const [exportDir, setExportDir] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [objectives, setObjectives] = useState<Objectives>(
    settingsService.getObjectives()
  );
  const {
    checkCalendarDir,
    setCalendarDir: saveCalendarDir,
    checkExportDir,
    setExportDir: saveExportDir,
  } = useSettings();
  const { toast } = useToast();

  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true);
      const calResult = await checkCalendarDir();
      if (calResult.calendar_dir) setCalendarDir(calResult.calendar_dir);

      const expResult = await checkExportDir();
      if (expResult.export_dir) setExportDir(expResult.export_dir);

      setIsLoading(false);
    };
    loadSettings();
  }, []);

  const handleCalendarDirectoryChange = async (value: string) => {
    setCalendarDir(value);
    if (value.trim()) {
      await saveCalendarDir(value);
    }
  };

  const handleExportDirectoryChange = async (value: string) => {
    setExportDir(value);
    if (value.trim()) {
      await saveExportDir(value);
    }
  };

  const handleObjectiveToggle = (objectiveKey: keyof Objectives) => {
    const newObjectives = { ...objectives };
    if (newObjectives[objectiveKey]) {
      newObjectives[objectiveKey]!.enabled =
        !newObjectives[objectiveKey]!.enabled;
      setObjectives(newObjectives);
      settingsService.setObjectives(newObjectives);
    }
  };

  const handleWeightChange = (
    objectiveKey: keyof Objectives,
    weight: string
  ) => {
    const newWeight = parseInt(weight);
    if (!isNaN(newWeight) && newWeight >= 0) {
      const newObjectives = { ...objectives };
      if (newObjectives[objectiveKey]) {
        newObjectives[objectiveKey]!.weight = newWeight;
        setObjectives(newObjectives);
        settingsService.setObjectives(newObjectives);
      }
    }
  };

  const handleResetObjectives = () => {
    settingsService.resetObjectives();
    setObjectives(settingsService.getObjectives());
    toast({
      title: "Success",
      description: "Objectives have been reset to default values",
    });
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      <DirectorySetting
        directories={[
          {
            title: "Calendar Directory",
            value: calendarDir,
            onChange: handleCalendarDirectoryChange,
            placeholder: "/Users/username/path/to/calendar/files",
          },
          {
            title: "Task Export Directory",
            value: exportDir,
            onChange: handleExportDirectoryChange,
            placeholder: "/Users/username/path/to/export/files",
          },
        ]}
        isLoading={isLoading}
      />

      <Card>
        <CardHeader>
          <CardTitle>Scheduling Objectives</CardTitle>
          <CardDescription className="text-left">
            Configure how Chewy should schedule your tasks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {Object.entries(objectives).map(([key, objective]) => (
              <div key={key} className="space-y-2">
                <div className="flex items-start gap-6">
                  <div className="w-[150px] shrink-0 text-left">
                    <Label htmlFor={`objective-${key}`} className="block">
                      {
                        objectiveConfig[key as keyof typeof objectiveConfig]
                          ?.label
                      }
                    </Label>
                    <p className="text-xs text-muted-foreground break-words">
                      {
                        objectiveConfig[key as keyof typeof objectiveConfig]
                          ?.caption
                      }
                    </p>
                  </div>
                  <div className="flex items-center gap-6 flex-1">
                    <Switch
                      id={`objective-${key}`}
                      checked={objective.enabled}
                      onCheckedChange={() =>
                        handleObjectiveToggle(key as keyof Objectives)
                      }
                    />
                    {objective.enabled && (
                      <>
                        <div className="flex-1">
                          <Slider
                            id={`weight-${key}`}
                            min={0}
                            max={100}
                            step={1}
                            value={[objective.weight]}
                            onValueChange={(value: number[]) =>
                              handleWeightChange(
                                key as keyof Objectives,
                                value[0].toString()
                              )
                            }
                            className="w-full"
                          />
                        </div>
                        <div className="w-12 text-sm text-muted-foreground">
                          {objective.weight}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <CardFooter className="flex justify-end">
            <Button
              variant="outline"
              size="icon"
              onClick={handleResetObjectives}
              title="Reset to default objectives"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </CardFooter>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;
