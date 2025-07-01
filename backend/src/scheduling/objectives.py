"""Objective configuration for the scheduler.

This module defines the available objectives and configuration structures
for specifying which objectives to use when generating a schedule.
"""

from dataclasses import dataclass
from typing import Dict, Type

from backend.src.scheduling.rewards import (
    EvenWorkloadReward,
    FreeAfternoonReward,
    FreeMorningReward,
    RewardComponent,
)


@dataclass
class ObjectiveConfig:
    """Configuration for a single objective."""

    enabled: bool = False
    weight: int = 1


class SchedulerObjectives:
    """Container for all scheduler objectives and their configurations."""

    # Registry of available objectives
    AVAILABLE_OBJECTIVES: Dict[str, Type[RewardComponent]] = {
        "FREE_AFTERNOON": FreeAfternoonReward,
        "FREE_MORNING": FreeMorningReward,
        "EVEN_WORKLOAD": EvenWorkloadReward,
    }

    def __init__(self, config: Dict[str, ObjectiveConfig] | None = None):
        """Initialize scheduler objectives.

        Args:
            config: Dictionary mapping objective names to their configurations.
                   If None, all objectives will be disabled.
        """
        self.config = {}

        # Initialize all available objectives as disabled
        for obj_name in self.AVAILABLE_OBJECTIVES:
            self.config[obj_name] = ObjectiveConfig(enabled=False, weight=1)

        # Update with provided config
        if config:
            for obj_name, obj_config in config.items():
                if obj_name in self.AVAILABLE_OBJECTIVES:
                    self.config[obj_name] = obj_config
        else:
            self.config = self.default()

    def enable_objective(self, name: str, weight: int = 1):
        """Enable an objective with the specified weight."""
        if name not in self.AVAILABLE_OBJECTIVES:
            raise ValueError(f"Unknown objective: {name}")
        self.config[name] = ObjectiveConfig(enabled=True, weight=weight)

    def disable_objective(self, name: str):
        """Disable an objective."""
        if name not in self.AVAILABLE_OBJECTIVES:
            raise ValueError(f"Unknown objective: {name}")
        self.config[name] = ObjectiveConfig(enabled=False, weight=1)

    def set_weight(self, name: str, weight: int):
        """Set the weight for an objective."""
        if name not in self.AVAILABLE_OBJECTIVES:
            raise ValueError(f"Unknown objective: {name}")
        current = self.config[name]
        self.config[name] = ObjectiveConfig(enabled=current.enabled, weight=weight)

    def get_enabled_components(self) -> list[RewardComponent]:
        """Get list of enabled reward components with their weights."""
        components = []
        for name, config in self.config.items():
            if config.enabled:
                component_class = self.AVAILABLE_OBJECTIVES[name]
                components.append(component_class(weight=config.weight))
        return components

    @classmethod
    def default(cls) -> "SchedulerObjectives":
        """Create a default configuration with reasonable settings."""
        return cls(
            {
                "FREE_AFTERNOON": ObjectiveConfig(enabled=False, weight=1),
                "FREE_MORNING": ObjectiveConfig(enabled=False, weight=1),
                "EVEN_WORKLOAD": ObjectiveConfig(enabled=False, weight=1),
            }
        )
