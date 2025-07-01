/**
 * @deprecated This component is deprecated and will be removed in a future version.
 * Calendar syncing is now handled automatically on a schedule.
 */

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RefreshCw, Trash } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatDistanceToNow } from "date-fns";

interface SyncButtonProps {
  /** Function to call when syncing */
  onSync: () => Promise<unknown>;
  /** Function to call when clearing data */
  onClearData: () => Promise<void>;
  /** Whether the sync operation is in progress */
  isSyncing: boolean;
  /** Whether any background operation is in progress */
  isProcessing?: boolean;
  /** The last time a sync was performed */
  lastSyncTime: Date | null;
  /** Button label when syncing */
  syncingLabel?: string;
  /** Label for the sync menu item */
  syncLabel?: string;
  /** Label for the clear data menu item */
  clearLabel?: string;
}

const SyncButton = ({
  onSync,
  onClearData,
  isSyncing,
  isProcessing = false,
  lastSyncTime,
  syncingLabel = "Syncing...",
  syncLabel = "Sync Data",
  clearLabel = "Clear Data",
}: SyncButtonProps) => {
  const isDisabled = isSyncing || isProcessing;
  const lastSyncText = lastSyncTime
    ? `Last synced ${formatDistanceToNow(lastSyncTime)} ago`
    : "Never synced";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="relative"
          disabled={isDisabled}
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${isSyncing ? "animate-spin" : ""}`}
          />
          {isSyncing ? syncingLabel : lastSyncText}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onSync()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {syncLabel}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onClearData}>
          <Trash className="mr-2 h-4 w-4" />
          {clearLabel}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default SyncButton;
