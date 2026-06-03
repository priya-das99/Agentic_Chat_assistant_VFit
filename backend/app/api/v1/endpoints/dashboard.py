from datetime import date as Date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.api_models import DashboardOverviewResponse
from app.services.dashboard_service import DashboardService
from app.services.activity_service import ActivityService

router = APIRouter()
dashboard_service = DashboardService()
activity_service = ActivityService()


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    user_id: int = 1,
    dashboard_date: Date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    overview = dashboard_service.get_overview(db=db, user_id=user_id, reference_date=dashboard_date)
    return DashboardOverviewResponse(**overview)


@router.get("/fitness-metrics")
def get_fitness_metrics(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get daily fitness metrics (steps, calories, hydration loss, intensity).
    Automatically calculated from exercise activities.
    """
    metrics = activity_service.get_daily_fitness_metrics(db=db, user_id=user_id)
    return metrics
