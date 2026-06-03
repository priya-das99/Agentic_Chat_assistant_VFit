import json
from sqlalchemy.orm import Session
from app.models.db_models import ContentLibrary, ContentCategory, UserContentInteraction


class ContentLibraryRepository:
    
    def ensure_categories_seeded(self, db: Session):
        """Seed initial categories if empty"""
        if db.query(ContentCategory).count() > 0:
            return
        
        # Default categories will be added when you provide data
        pass
    
    def add_category(self, db: Session, category_data: dict) -> ContentCategory:
        """Add a new category"""
        category = ContentCategory(**category_data)
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    
    def add_content(self, db: Session, content_data: dict) -> ContentLibrary:
        """Add a new content item"""
        content = ContentLibrary(**content_data)
        db.add(content)
        db.commit()
        db.refresh(content)
        return content
    
    def bulk_add_categories(self, db: Session, categories: list[dict]):
        """Add multiple categories at once"""
        for cat_data in categories:
            # Check if category already exists
            existing = db.query(ContentCategory).filter(
                ContentCategory.category_key == cat_data["category_key"]
            ).first()
            
            if not existing:
                db.add(ContentCategory(**cat_data))
        
        db.commit()
    
    def bulk_add_content(self, db: Session, content_items: list[dict]):
        """Add multiple content items at once"""
        for content_data in content_items:
            db.add(ContentLibrary(**content_data))
        
        db.commit()
    
    def get_all_categories(self, db: Session) -> list[ContentCategory]:
        """Get all active categories"""
        return (
            db.query(ContentCategory)
            .filter(ContentCategory.is_active == 1)
            .order_by(ContentCategory.sort_order.asc(), ContentCategory.category_label.asc())
            .all()
        )
    
    def get_content_by_category(
        self,
        db: Session,
        category_key: str,
        limit: int = 10
    ) -> list[ContentLibrary]:
        """Get content by category"""
        return (
            db.query(ContentLibrary)
            .filter(
                ContentLibrary.category_key == category_key,
                ContentLibrary.is_active == 1
            )
            .order_by(ContentLibrary.is_featured.desc(), ContentLibrary.rating.desc())
            .limit(limit)
            .all()
        )
    
    def get_content_by_mood(
        self,
        db: Session,
        mood: str,
        limit: int = 5
    ) -> list[ContentLibrary]:
        """Get content matching a mood"""
        # SQLite doesn't have JSON functions, so we use LIKE
        return (
            db.query(ContentLibrary)
            .filter(
                ContentLibrary.mood_tags.like(f'%"{mood}"%'),
                ContentLibrary.is_active == 1
            )
            .order_by(ContentLibrary.rating.desc())
            .limit(limit)
            .all()
        )
    
    def get_featured_content(self, db: Session, limit: int = 5) -> list[ContentLibrary]:
        """Get featured content"""
        return (
            db.query(ContentLibrary)
            .filter(
                ContentLibrary.is_featured == 1,
                ContentLibrary.is_active == 1
            )
            .order_by(ContentLibrary.rating.desc())
            .limit(limit)
            .all()
        )
    
    def get_all_content(self, db: Session) -> list[ContentLibrary]:
        """Get all active content"""
        return (
            db.query(ContentLibrary)
            .filter(ContentLibrary.is_active == 1)
            .order_by(ContentLibrary.category_key.asc(), ContentLibrary.title.asc())
            .all()
        )
    
    def list_all_active(self, db: Session) -> list[ContentLibrary]:
        """Alias for get_all_content - used by recommendation service"""
        return self.get_all_content(db)
    
    def record_interaction(
        self,
        db: Session,
        user_id: int,
        content_id: int,
        interaction_type: str,
        **kwargs
    ):
        """Record user interaction with content"""
        interaction = UserContentInteraction(
            user_id=user_id,
            content_id=content_id,
            interaction_type=interaction_type,
            **kwargs
        )
        db.add(interaction)
        db.commit()
        
        # Update view count
        if interaction_type == "viewed":
            content = db.query(ContentLibrary).get(content_id)
            if content:
                content.view_count += 1
                db.commit()
    
    def get_user_history(
        self,
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> list[UserContentInteraction]:
        """Get user's content history"""
        return (
            db.query(UserContentInteraction)
            .filter(UserContentInteraction.user_id == user_id)
            .order_by(UserContentInteraction.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def search_content(
        self,
        db: Session,
        query: str,
        content_type: str = None,
        category_key: str = None,
        limit: int = 10
    ) -> list[ContentLibrary]:
        """Search content by title or description"""
        filters = [ContentLibrary.is_active == 1]
        
        if query:
            search_filter = (
                ContentLibrary.title.like(f"%{query}%") |
                ContentLibrary.description.like(f"%{query}%")
            )
            filters.append(search_filter)
        
        if content_type:
            filters.append(ContentLibrary.content_type == content_type)
        
        if category_key:
            filters.append(ContentLibrary.category_key == category_key)
        
        return (
            db.query(ContentLibrary)
            .filter(*filters)
            .order_by(ContentLibrary.rating.desc())
            .limit(limit)
            .all()
        )
