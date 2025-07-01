export interface Objective {
  enabled: boolean;
  weight: number;
}

export interface ObjectiveConfig {
  label: string;
  caption: string;
}

export const objectiveConfig: Record<keyof Objectives, ObjectiveConfig> = {
  FREE_AFTERNOON: {
    label: "End Earlier",
    caption: "Try to end the day early",
  },
  FREE_MORNING: {
    label: "Start Later",
    caption: "Try to start the day later",
  },
  EVEN_WORKLOAD: {
    label: "Spread Evenly",
    caption: "Try to spread the work out over the week",
  },
};

export interface Objectives {
  FREE_AFTERNOON?: Objective;
  FREE_MORNING?: Objective;
  EVEN_WORKLOAD?: Objective;
}
