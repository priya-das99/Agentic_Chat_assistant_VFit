from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Demo User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mood_label = Column(String(50), nullable=False)
    mood_score = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    activity_category = Column(String(50), nullable=False, index=True)
    activity_name = Column(String(100), nullable=False)
    value = Column(Integer, nullable=True)
    unit = Column(String(50), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Fitness metrics (calculated automatically for exercise activities)
    calories_burned = Column(Integer, nullable=True)
    steps_count = Column(Integer, nullable=True)
    intensity_level = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    age = Column(Integer, nullable=True)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)  # NEW: for BMR calculation
    fitness_goal = Column(String(150), nullable=True)
    activity_level = Column(String(50), nullable=True)
    preferred_activities = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)
    fact_text = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, default="chat")
    confidence = Column(Integer, nullable=False, default=80)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class SessionShortcutState(Base):
    __tablename__ = "session_shortcut_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pending_action = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SessionActivityDecisionState(Base):
    __tablename__ = "session_activity_decision_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pending_type = Column(String(50), nullable=False)
    decision_payload = Column(Text, nullable=False)
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActivityCatalog(Base):
    __tablename__ = "activity_catalog"

    id = Column(Integer, primary_key=True, index=True)
    category_key = Column(String(50), nullable=False, index=True)
    category_label = Column(String(100), nullable=False)
    activity_key = Column(String(50), nullable=False, index=True)
    activity_label = Column(String(100), nullable=False)
    aliases = Column(Text, nullable=True)
    default_unit = Column(String(30), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SessionActivityDraft(Base):
    __tablename__ = "session_activity_drafts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    step = Column(String(50), nullable=False, default="category")
    status = Column(String(50), nullable=False, default="pending")
    category_key = Column(String(50), nullable=True, index=True)
    category_label = Column(String(100), nullable=True)
    activity_key = Column(String(50), nullable=True, index=True)
    activity_label = Column(String(100), nullable=True)
    activity_date = Column(Date, nullable=True)
    activity_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    source = Column(String(50), nullable=False, default="guided")
    raw_text = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SessionMoodDraft(Base):
    __tablename__ = "session_mood_drafts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    step = Column(String(50), nullable=False, default="reason")
    status = Column(String(50), nullable=False, default="pending")
    mood_label = Column(String(50), nullable=False)
    mood_score = Column(Integer, nullable=True)
    emoji = Column(String(20), nullable=True)
    raw_text = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChallengeTemplate(Base):
    __tablename__ = "challenge_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    metric_key = Column(String(50), nullable=False, index=True)
    goal_value = Column(Integer, nullable=False)
    unit = Column(String(30), nullable=True)
    points = Column(Integer, nullable=False, default=50)
    reminder_message = Column(Text, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserChallenge(Base):
    __tablename__ = "user_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("challenge_templates.id"), nullable=False, index=True)
    week_start = Column(Date, nullable=False, index=True)
    week_end = Column(Date, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="active")
    progress_value = Column(Integer, nullable=False, default=0)
    goal_value = Column(Integer, nullable=False, default=0)
    points_awarded = Column(Integer, nullable=False, default=0)
    reminder_count = Column(Integer, nullable=False, default=0)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_reminded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChallengeEvent(Base):
    __tablename__ = "challenge_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_challenge_id = Column(Integer, ForeignKey("user_challenges.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    value = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PointLedger(Base):
    __tablename__ = "point_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    points = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChallengeReminder(Base):
    __tablename__ = "challenge_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_challenge_id = Column(Integer, ForeignKey("user_challenges.id"), nullable=True, index=True)
    reminder_type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    due_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContentCategory(Base):
    __tablename__ = "content_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    category_key = Column(String(50), unique=True, nullable=False, index=True)
    category_label = Column(String(100), nullable=False)
    parent_category_key = Column(String(50))
    
    description = Column(Text)
    icon_emoji = Column(String(10))
    color_hex = Column(String(7))
    
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContentLibrary(Base):
    __tablename__ = "content_library"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    title = Column(String(200), nullable=False)
    description = Column(Text)
    content_type = Column(String(50), nullable=False)  # video, article, audio, app, guide
    
    # Content Location
    url = Column(Text)
    thumbnail_url = Column(Text)
    
    # Categorization
    category_key = Column(String(50), nullable=False, index=True)
    category_label = Column(String(100), nullable=False)
    tags = Column(Text)  # JSON array
    
    # Metadata
    duration_minutes = Column(Integer)
    difficulty = Column(String(20))
    language = Column(String(10), default="en")
    
    # Targeting
    mood_tags = Column(Text)  # JSON array
    energy_level = Column(String(20))
    time_of_day = Column(String(20))
    
    # Quality & Engagement
    rating = Column(Integer)  # Changed from DECIMAL to Integer for SQLite
    view_count = Column(Integer, default=0)
    completion_rate = Column(Integer)  # Changed from DECIMAL to Integer (0-100)
    
    # Source Info
    source = Column(String(100))
    author = Column(String(100))
    published_date = Column(Date)
    
    # Status
    is_active = Column(Integer, default=1)
    is_featured = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserContentInteraction(Base):
    __tablename__ = "user_content_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content_library.id"), nullable=False, index=True)
    
    # Interaction Type
    interaction_type = Column(String(50), nullable=False)  # viewed, completed, liked, saved
    
    # Engagement Metrics
    watch_duration_seconds = Column(Integer)
    completion_percentage = Column(Integer)  # Changed from DECIMAL to Integer (0-100)
    
    # Feedback
    rating = Column(Integer)
    was_helpful = Column(Integer)
    
    # Context
    suggested_by = Column(String(50))
    user_mood_before = Column(String(50))
    user_mood_after = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MealLog(Base):
    __tablename__ = "meal_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Meal Information
    meal_type = Column(String(50), nullable=False)  # breakfast, lunch, dinner, snack
    meal_name = Column(String(200))
    
    # Nutrition Information
    calories = Column(Integer, nullable=False)
    protein_grams = Column(Integer)
    carbs_grams = Column(Integer)
    fat_grams = Column(Integer)
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
