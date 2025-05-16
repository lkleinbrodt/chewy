import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { format } from "date-fns";

interface SyncButtonProps {
  onSync: () => Promise<{
    success: boolean;
    needsDirectorySetup?: boolean;
    message?: string;
  }>;
  isSyncing: boolean;
  lastSyncTime: Date | null;
}

const SyncButton = ({ onSync, isSyncing, lastSyncTime }: SyncButtonProps) => {
  const handleSync = async () => {
    if (!isSyncing) {
      await onSync();
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Sync Calendar
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {lastSyncTime
            ? `Last synced: ${format(lastSyncTime, "MMM d, yyyy h:mm a")}`
            : "Calendar has not been synced yet"}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default SyncButton;
