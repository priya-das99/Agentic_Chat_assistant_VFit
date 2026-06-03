from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.services.reminder_service import ReminderService
from app.services.agent_decision_service import AgentDecisionService
from app.services.proactive_intervention_service import ProactiveInterventionService


class ReminderScheduler:
    logger = logging.getLogger(__name__)

    def __init__(self, interval_seconds: int = 900):
        self.interval_seconds = interval_seconds
        self.reminder_service = ReminderService()
        self.decision_service = AgentDecisionService()
        self.intervention_service = ProactiveInterventionService()
        self._stop_event = asyncio.Event()
        self.cycle_count = 0

    async def run_forever(self) -> None:
        self.logger.info("Reminder scheduler started with interval=%ss", self.interval_seconds)
        while not self._stop_event.is_set():
            self.logger.info("Reminder scheduler waking up for cycle #%s", self.cycle_count)
            
            # Run reminder cycle (existing functionality)
            await self.run_reminder_cycle()
            
            # Run proactive intervention cycle (NEW - every 4th cycle = every hour)
            if self.cycle_count % 4 == 0:
                await self.run_intervention_cycle()
            
            self.cycle_count += 1
            
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue
        self.logger.info("Reminder scheduler stopped")

    async def run_reminder_cycle(self) -> list[dict]:
        """Run reminder cycle (existing functionality)"""
        db = SessionLocal()
        try:
            created = self.reminder_service.run_cycle(db=db, now=datetime.now(ZoneInfo("Asia/Kolkata")))
            self.logger.info("Reminder cycle complete: created=%s", len(created))
            return created
        finally:
            db.close()
    
    async def run_intervention_cycle(self) -> None:
        """Run proactive intervention cycle (NEW)"""
        self.logger.info("Starting proactive intervention cycle")
        db = SessionLocal()
        
        try:
            # Get all active users
            user_ids = self._get_active_users(db)
            self.logger.info("Checking %s users for proactive interventions", len(user_ids))
            
            intervention_count = 0
            
            for user_id in user_ids:
                try:
                    # Check if intervention needed
                    decision = self.decision_service.should_intervene(db, user_id)
                    
                    if decision.should_intervene:
                        self.logger.info(
                            "Intervention needed for user_id=%s type=%s priority=%s",
                            user_id,
                            decision.intervention_type,
                            decision.priority
                        )
                        
                        # Trigger intervention (async)
                        await self.intervention_service.run_intervention_check(user_id)
                        intervention_count += 1
                        
                        # Rate limiting between interventions
                        await asyncio.sleep(1)
                
                except Exception as e:
                    self.logger.error("Error checking user_id=%s: %s", user_id, e)
            
            self.logger.info("Intervention cycle complete: interventions=%s", intervention_count)
        
        finally:
            db.close()
    
    def _get_active_users(self, db) -> list[int]:
        """Get list of active user IDs"""
        # Reuse existing method from ReminderService
        return self.reminder_service._list_user_ids(db)
    
    async def run_once(self) -> list[dict]:
        """For backward compatibility and testing"""
        return await self.run_reminder_cycle()

    def stop(self) -> None:
        self._stop_event.set()
