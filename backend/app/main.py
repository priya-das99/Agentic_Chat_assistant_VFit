import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME
from app.core.database import Base, engine, SessionLocal
from app.api.v1.endpoints import activity, challenges, chat, dashboard, health, meals, mood, proactive, profile
from app.services.reminder_scheduler import ReminderScheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["Activity"])
app.include_router(mood.router, prefix="/api/v1/mood", tags=["Mood"])
app.include_router(challenges.router, prefix="/api/v1/challenges", tags=["Challenges"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(proactive.router, prefix="/api/v1/proactive", tags=["Proactive"])
app.include_router(meals.router, prefix="/api/v1/meals", tags=["Meals"])

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

reminder_scheduler = ReminderScheduler(interval_seconds=900)


def seed_default_content():
    """Seed content library with default content if empty"""
    import json
    from app.models.db_models import ContentLibrary, ContentCategory
    
    db = SessionLocal()
    try:
        # Check if content already exists
        if db.query(ContentLibrary).count() > 0:
            return
        
        # Seed categories
        categories = [
            {"category_key": "meditation", "category_label": "Meditation", "description": "Guided meditation and mindfulness exercises", "is_active": 1, "sort_order": 1},
            {"category_key": "yoga", "category_label": "Yoga", "description": "Yoga flows and stretching routines", "is_active": 1, "sort_order": 2},
            {"category_key": "cardio", "category_label": "Cardio", "description": "High-energy cardiovascular exercises", "is_active": 1, "sort_order": 3},
            {"category_key": "strength", "category_label": "Strength Training", "description": "Strength and resistance exercises", "is_active": 1, "sort_order": 4},
            {"category_key": "nutrition", "category_label": "Nutrition", "description": "Nutrition tips and healthy eating guides", "is_active": 1, "sort_order": 5},
            {"category_key": "sleep", "category_label": "Sleep", "description": "Sleep improvement and relaxation content", "is_active": 1, "sort_order": 6},
            {"category_key": "stress_relief", "category_label": "Stress Relief", "description": "Stress management and anxiety relief", "is_active": 1, "sort_order": 7}
        ]
        
        for cat_data in categories:
            if not db.query(ContentCategory).filter(ContentCategory.category_key == cat_data["category_key"]).first():
                db.add(ContentCategory(**cat_data))
        db.commit()
        
        # Seed content
        content_items = [
            {"title": "15-Minute Full Body Workout", "description": "A dynamic full-body workout that requires no equipment", "category_key": "cardio", "category_label": "Cardio", "content_type": "video", "duration_minutes": 15, "url": "/content/15-min-full-body", "difficulty": "intermediate", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 120, "mood_tags": json.dumps(["energetic", "motivated", "stressed"])},
            {"title": "Morning Yoga Flow", "description": "Start your day with this 20-minute gentle yoga flow", "category_key": "yoga", "category_label": "Yoga", "content_type": "video", "duration_minutes": 20, "url": "/content/morning-yoga", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 200, "mood_tags": json.dumps(["calm", "peaceful", "tired"])},
            {"title": "10-Minute Meditation for Stress", "description": "Quick meditation session to reduce stress and anxiety", "category_key": "meditation", "category_label": "Meditation", "content_type": "audio", "duration_minutes": 10, "url": "/content/stress-meditation", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 350, "mood_tags": json.dumps(["anxious", "stressed", "overwhelmed"])},
            {"title": "Evening Wind-Down Routine", "description": "Relaxing activities to prepare for better sleep", "category_key": "sleep", "category_label": "Sleep", "content_type": "guide", "duration_minutes": 15, "url": "/content/evening-routine", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 280, "mood_tags": json.dumps(["tired", "anxious", "restless"])},
            {"title": "Strength Training Basics", "description": "Learn fundamental strength training techniques and exercises", "category_key": "strength", "category_label": "Strength Training", "content_type": "video", "duration_minutes": 25, "url": "/content/strength-basics", "difficulty": "intermediate", "is_featured": 0, "is_active": 1, "rating": 4, "view_count": 150, "mood_tags": json.dumps(["motivated", "energetic"])},
            {"title": "Healthy Eating Guide", "description": "Complete guide to balanced nutrition and meal planning", "category_key": "nutrition", "category_label": "Nutrition", "content_type": "guide", "duration_minutes": 30, "url": "/content/healthy-eating", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 200, "mood_tags": json.dumps(["motivated", "tired"])},
            {"title": "Anxiety Relief Breathing", "description": "Proven breathing techniques to manage anxiety", "category_key": "stress_relief", "category_label": "Stress Relief", "content_type": "audio", "duration_minutes": 8, "url": "/content/breathing-anxiety", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 400, "mood_tags": json.dumps(["anxious", "stressed", "overwhelmed"])},
            {"title": "Desk Yoga Breaks", "description": "Quick yoga stretches you can do at your desk", "category_key": "yoga", "category_label": "Yoga", "content_type": "video", "duration_minutes": 5, "url": "/content/desk-yoga", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 250, "mood_tags": json.dumps(["stressed", "tired", "overwhelmed"])},
            {"title": "HIIT Cardio Blast", "description": "High-intensity interval training for maximum results", "category_key": "cardio", "category_label": "Cardio", "content_type": "video", "duration_minutes": 20, "url": "/content/hiit-blast", "difficulty": "advanced", "is_featured": 0, "is_active": 1, "rating": 5, "view_count": 180, "mood_tags": json.dumps(["energetic", "motivated"])},
            {"title": "Sleep Hypnosis Session", "description": "Deep relaxation hypnosis for quality sleep", "category_key": "sleep", "category_label": "Sleep", "content_type": "audio", "duration_minutes": 45, "url": "/content/sleep-hypnosis", "difficulty": "beginner", "is_featured": 1, "is_active": 1, "rating": 5, "view_count": 320, "mood_tags": json.dumps(["tired", "anxious", "restless"])}
        ]
        
        for content_data in content_items:
            if not db.query(ContentLibrary).filter(ContentLibrary.title == content_data["title"]).first():
                db.add(ContentLibrary(**content_data))
        db.commit()
    except Exception as e:
        print(f"Error seeding content: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
async def start_reminder_scheduler():
    # Seed default content
    seed_default_content()
    
    app.state.reminder_scheduler_task = asyncio.create_task(reminder_scheduler.run_forever())


@app.on_event("shutdown")
async def stop_reminder_scheduler():
    reminder_scheduler.stop()
    task = getattr(app.state, "reminder_scheduler_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/")
def serve_frontend():
    return FileResponse(frontend_dir / "vantage-dashboard.html")
