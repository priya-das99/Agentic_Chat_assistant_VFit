from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str
    user_id: int = 1


class ChatMessageResponse(BaseModel):
    reply: str


class MoodLogItem(BaseModel):
    mood_label: str
    mood_score: int | None = None
    reason: str | None = None
    created_at: str | None = None


class ActivityLogItem(BaseModel):
    activity_category: str
    activity_name: str
    value: float | None = None
    unit: str | None = None
    duration_minutes: int | None = None
    notes: str | None = None
    created_at: str | None = None


class RecentLogsResponse(BaseModel):
    moods: list[MoodLogItem]
    activities: list[ActivityLogItem]


class UserProfileItem(BaseModel):
    fitness_goal: str | None = None
    activity_level: str | None = None
    preferred_activities: str | None = None
    limitations: str | None = None


class UserMemoryItem(BaseModel):
    memory_type: str
    fact_text: str
    source: str
    confidence: int


class ActivityLogInput(BaseModel):
    activity_name: str
    value: float | None = None
    unit: str | None = None
    duration_minutes: int | None = None
    notes: str | None = None


class ActivityParseResult(BaseModel):
    matched: bool
    activity_name: str | None = None
    activity_category: str | None = None
    value: float | None = None
    unit: str | None = None
    duration_minutes: int | None = None
    notes: str | None = None


class MoodLogInput(BaseModel):
    mood_label: str
    reason: str | None = None


class MoodQuickActionOption(BaseModel):
    label: str
    mood_label: str
    emoji: str
    requires_reason: bool = False


class MoodQuickActionRequest(BaseModel):
    user_id: int = 1
    mood_label: str
    reason: str | None = None


class MoodQuickActionResponse(BaseModel):
    success: bool
    message: str
    mood_label: str | None = None
    mood_score: int | None = None
    emoji: str | None = None
    reason: str | None = None
    needs_reason: bool = False
    available_options: list[MoodQuickActionOption] = Field(default_factory=list)
    reason_options: list[MoodQuickActionOption] = Field(default_factory=list)


class MoodOptionsResponse(BaseModel):
    options: list[MoodQuickActionOption]


class MoodDraftStartRequest(BaseModel):
    user_id: int = 1
    session_id: int | None = None
    mood_label: str
    raw_text: str | None = None


class MoodDraftUpdateRequest(BaseModel):
    reason: str | None = None
    reason_label: str | None = None
    raw_text: str | None = None


class MoodDraftResponse(BaseModel):
    draft_id: int
    session_id: int
    user_id: int
    step: str
    status: str
    prompt: str
    can_submit: bool
    draft: dict[str, Any]
    log_result: dict[str, Any] | None = None
    available_options: list[MoodQuickActionOption] = Field(default_factory=list)
    reason_options: list[MoodQuickActionOption] = Field(default_factory=list)


class MoodParseResult(BaseModel):
    matched: bool
    mood_label: str | None = None
    mood_score: int | None = None
    reason: str | None = None


class ActivityDecisionAction(BaseModel):
    entity: str
    action: str
    data: dict[str, Any] = Field(default_factory=dict)


class ActivityDecisionResult(BaseModel):
    actions: list[ActivityDecisionAction]
    clarifications: list[str] = Field(default_factory=list)
    message: str = ""


class ActivityCatalogEntry(BaseModel):
    category_key: str
    category_label: str
    activity_key: str
    activity_label: str
    default_unit: str | None = None
    sort_order: int = 0


class ActivityCategoryGroup(BaseModel):
    category_key: str
    category_label: str
    activities: list[ActivityCatalogEntry]


class ActivityCatalogResponse(BaseModel):
    categories: list[ActivityCategoryGroup]


class ActivityDraftStartRequest(BaseModel):
    user_id: int = 1
    session_id: int | None = None
    category_key: str | None = None
    activity_key: str | None = None


class ActivityDraftUpdateRequest(BaseModel):
    category_key: str | None = None
    activity_key: str | None = None
    activity_date: str | None = None
    activity_time: str | None = None
    duration_minutes: int | None = None
    raw_text: str | None = None


class ActivityDraftResponse(BaseModel):
    draft_id: int
    session_id: int
    user_id: int
    step: str
    status: str
    prompt: str
    can_submit: bool
    draft: dict[str, Any]
    log_result: dict[str, Any] | None = None


class ChallengeTemplateItem(BaseModel):
    code: str
    name: str
    description: str
    metric_key: str
    goal_value: int
    unit: str | None = None
    points: int
    reminder_message: str | None = None


class ChallengeReminderItem(BaseModel):
    reminder_id: int
    reminder_type: str
    message: str
    status: str
    due_at: str | None = None
    sent_at: str | None = None


class UserChallengeItem(BaseModel):
    challenge_id: int
    code: str
    name: str
    description: str
    metric_key: str
    goal_value: int
    progress_value: int
    remaining_value: int
    status: str
    points_awarded: int
    week_start: str
    week_end: str
    completed_at: str | None = None
    last_event_at: str | None = None
    reminder_count: int = 0
    unit: str | None = None


class ChallengeSummaryResponse(BaseModel):
    user_id: int
    week_start: str
    week_end: str
    total_points: int
    active_challenges: list[UserChallengeItem] = Field(default_factory=list)
    reminders: list[ChallengeReminderItem] = Field(default_factory=list)
    message: str


class ChallengeProgressRequest(BaseModel):
    user_id: int = 1
    challenge_code: str | None = None
    metric_key: str | None = None
    value: int | None = None
    message: str | None = None


class ChallengeProgressResponse(BaseModel):
    updated: bool
    reason: str | None = None
    challenge: UserChallengeItem | None = None
    event_id: int | None = None


class ReminderActionRequest(BaseModel):
    user_id: int = 1
    snooze_minutes: int = 30


class DashboardStatItem(BaseModel):
    label: str
    value: str
    detail: str | None = None
    tone: str = "neutral"


class DashboardLogItem(BaseModel):
    item_type: str
    title: str
    detail: str
    created_at: str | None = None


class DashboardSuggestionItem(BaseModel):
    content_id: int | None = None
    title: str
    category_label: str
    reason: str
    action_prompt: str
    content_type: str | None = None
    duration: str | None = None
    url: str | None = None
    score: float | None = None


class DashboardWeeklySnapshot(BaseModel):
    week_start: str
    week_end: str
    mood_logs: int
    activity_sessions: int
    exercise_minutes: int
    completed_challenges: int
    total_points: int


class DashboardOverviewResponse(BaseModel):
    user_id: int
    date: str
    daily_stats: list[DashboardStatItem] = Field(default_factory=list)
    calorie_balance: dict = Field(default_factory=dict)
    today_logs: list[DashboardLogItem] = Field(default_factory=list)
    weekly_snapshot: DashboardWeeklySnapshot
    suggestions: list[DashboardSuggestionItem] = Field(default_factory=list)
