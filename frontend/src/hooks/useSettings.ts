import { AxiosError } from "axios";
import axiosInstance from "@/utils/axiosInstance";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

export const useSettings = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const checkCalendarDir = async (): Promise<{
    calendar_dir: string | null;
    is_set: boolean;
  }> => {
    setLoading(true);
    setError(null);

    try {
      const response = await axiosInstance.get("/settings/calendar-dir");
      return response.data;
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Failed to check calendar directory";
      setError(errorMessage);
      toast({
        variant: "destructive",
        title: "Error",
        description: errorMessage,
      });
      return { calendar_dir: null, is_set: false };
    } finally {
      setLoading(false);
    }
  };

  const setCalendarDir = async (directory: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response = await axiosInstance.post("/settings/calendar-dir", {
        calendar_dir: directory,
      });

      toast({
        title: "Success",
        description: `Calendar directory set successfully with ${response.data.files_found} JSON files found.`,
      });

      return true;
    } catch (err) {
      const axiosError = err as AxiosError<{ error: string }>;
      const errorMessage =
        axiosError.response?.data?.error ||
        (err instanceof Error
          ? err.message
          : "Failed to set calendar directory");
      setError(errorMessage);
      toast({
        variant: "destructive",
        title: "Error",
        description: errorMessage,
      });
      return false;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    checkCalendarDir,
    setCalendarDir,
  };
};
