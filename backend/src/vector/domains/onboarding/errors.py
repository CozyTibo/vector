"""Domain errors for onboarding HTTP orchestration."""

from __future__ import annotations


class OnboardingAlreadyCompletedError(Exception):
    """PATCH attempted while onboarding row is already completed."""


class InvalidOnboardingStepError(Exception):
    """``current_step`` is not a known onboarding step."""

    def __init__(self, step: str) -> None:
        super().__init__(step)
        self.step = step


class SlackNotConnectedForWorkspaceError(Exception):
    """Slack workspace link missing for this tenant."""


class SlackMembersLoadError(Exception):
    """Slack API or member list failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WorkspaceSettingsForbiddenError(Exception):
    """Only workspace owners may change post-onboarding workspace settings."""
