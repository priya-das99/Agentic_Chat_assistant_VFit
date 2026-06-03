import json

from sqlalchemy.orm import Session

from app.models.db_models import ActivityCatalog


DEFAULT_ACTIVITY_CATALOG = [
    {
        "category_key": "well_being",
        "category_label": "Well Being",
        "activity_key": "book_reading",
        "activity_label": "Book Reading",
        "aliases": ["reading", "book", "study"],
        "default_unit": "minutes",
        "sort_order": 1,
    },
    {
        "category_key": "well_being",
        "category_label": "Well Being",
        "activity_key": "meditation",
        "activity_label": "Meditation",
        "aliases": ["mindfulness"],
        "default_unit": "minutes",
        "sort_order": 2,
    },
    {
        "category_key": "well_being",
        "category_label": "Well Being",
        "activity_key": "stretching",
        "activity_label": "Stretching",
        "aliases": ["stretch"],
        "default_unit": "minutes",
        "sort_order": 3,
    },
    {
        "category_key": "most_popular",
        "category_label": "Most Popular",
        "activity_key": "hiking",
        "activity_label": "Hiking",
        "aliases": ["trekking"],
        "default_unit": "minutes",
        "sort_order": 1,
    },
    {
        "category_key": "most_popular",
        "category_label": "Most Popular",
        "activity_key": "swimming",
        "activity_label": "Swimming",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 2,
    },
    {
        "category_key": "cardio_vascular",
        "category_label": "Cardio Vascular",
        "activity_key": "aerobics",
        "activity_label": "Aerobics",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 1,
    },
    {
        "category_key": "cardio_vascular",
        "category_label": "Cardio Vascular",
        "activity_key": "zumba",
        "activity_label": "Zumba",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 2,
    },
    {
        "category_key": "cardio_vascular",
        "category_label": "Cardio Vascular",
        "activity_key": "jump_rope",
        "activity_label": "Jump Rope",
        "aliases": ["skipping"],
        "default_unit": "minutes",
        "sort_order": 3,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "badminton",
        "activity_label": "Badminton",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 1,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "basketball",
        "activity_label": "Basketball",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 2,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "boxing",
        "activity_label": "Boxing",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 3,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "cricket",
        "activity_label": "Cricket",
        "aliases": [],
        "default_unit": "minutes",
        "sort_order": 4,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "football",
        "activity_label": "Football",
        "aliases": ["soccer"],
        "default_unit": "minutes",
        "sort_order": 5,
    },
    {
        "category_key": "sports",
        "category_label": "Sports",
        "activity_key": "martial_arts",
        "activity_label": "Martial Arts",
        "aliases": ["karate", "taekwondo"],
        "default_unit": "minutes",
        "sort_order": 6,
    },
]


class ActivityCatalogRepository:
    def ensure_seeded(self, db: Session) -> None:
        if db.query(ActivityCatalog).count() > 0:
            return

        for row in DEFAULT_ACTIVITY_CATALOG:
            db.add(
                ActivityCatalog(
                    category_key=row["category_key"],
                    category_label=row["category_label"],
                    activity_key=row["activity_key"],
                    activity_label=row["activity_label"],
                    aliases=json.dumps(row["aliases"]),
                    default_unit=row["default_unit"],
                    sort_order=row["sort_order"],
                    is_active=1,
                )
            )
        db.commit()

    def list_all(self, db: Session) -> list[ActivityCatalog]:
        self.ensure_seeded(db)
        return (
            db.query(ActivityCatalog)
            .filter(ActivityCatalog.is_active == 1)
            .order_by(ActivityCatalog.category_label.asc(), ActivityCatalog.sort_order.asc(), ActivityCatalog.activity_label.asc())
            .all()
        )

    def get_by_activity_key(self, db: Session, activity_key: str) -> ActivityCatalog | None:
        self.ensure_seeded(db)
        return (
            db.query(ActivityCatalog)
            .filter(ActivityCatalog.activity_key == activity_key, ActivityCatalog.is_active == 1)
            .order_by(ActivityCatalog.sort_order.asc())
            .first()
        )

    def find_by_name(self, db: Session, name: str) -> ActivityCatalog | None:
        self.ensure_seeded(db)
        normalized = name.strip().lower()
        rows = self.list_all(db)
        for row in rows:
            aliases = []
            if row.aliases:
                try:
                    aliases = [alias.strip().lower() for alias in json.loads(row.aliases)]
                except json.JSONDecodeError:
                    aliases = []
            if normalized in {row.activity_key.lower(), row.activity_label.lower(), row.category_key.lower(), row.category_label.lower(), *aliases}:
                return row
        return None

    def get_by_category_key(self, db: Session, category_key: str) -> list[ActivityCatalog]:
        self.ensure_seeded(db)
        return (
            db.query(ActivityCatalog)
            .filter(ActivityCatalog.category_key == category_key, ActivityCatalog.is_active == 1)
            .order_by(ActivityCatalog.sort_order.asc(), ActivityCatalog.activity_label.asc())
            .all()
        )
