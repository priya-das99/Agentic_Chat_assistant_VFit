"""
AI-Powered Nutrition Estimator
Estimates calories and macros for meals based on food name and servings.
Uses common nutrition data and portion sizes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NutritionEstimate:
    """Estimated nutrition for a meal"""
    calories: int
    protein_grams: int
    carbs_grams: int
    fat_grams: int
    confidence: str  # "high", "medium", "low"
    notes: str


class NutritionEstimator:
    """
    Estimates nutrition information for meals.
    Uses a database of common foods and AI-like estimation for unknown foods.
    """
    
    # Common foods database with nutrition per serving
    # Format: {food_name: (calories, protein, carbs, fat)}
    FOOD_DATABASE = {
        # Burgers & Sandwiches
        "hamburger": (500, 25, 45, 22),
        "cheeseburger": (600, 28, 48, 28),
        "chicken burger": (550, 35, 50, 20),
        "veggie burger": (400, 20, 50, 12),
        "sandwich": (350, 15, 40, 12),
        "chicken sandwich": (450, 30, 45, 15),
        
        # Hot Dogs
        "hot dog": (300, 10, 25, 18),
        "chicken hot dog": (250, 12, 22, 12),
        
        # Pizza
        "pizza slice": (285, 12, 36, 10),
        "pizza": (285, 12, 36, 10),  # per slice
        "pepperoni pizza": (300, 13, 35, 12),
        "cheese pizza": (270, 11, 34, 9),
        
        # Rice & Grains
        "rice": (200, 4, 45, 0),  # 1 cup cooked
        "fried rice": (350, 8, 55, 10),
        "biryani": (400, 15, 60, 12),
        "pasta": (220, 8, 43, 1),
        "noodles": (200, 7, 40, 2),
        
        # Indian Food
        "dal": (200, 12, 30, 5),
        "roti": (120, 4, 22, 2),
        "naan": (260, 8, 45, 5),
        "paratha": (300, 6, 35, 15),
        "samosa": (250, 5, 30, 13),
        "dosa": (170, 4, 30, 5),
        "idli": (40, 2, 8, 0),  # per piece
        "curry": (300, 15, 20, 18),
        "paneer curry": (350, 18, 15, 22),
        "chicken curry": (300, 25, 15, 15),
        
        # Chinese Food
        "fried rice": (350, 8, 55, 10),
        "noodles": (200, 7, 40, 2),
        "momos": (200, 8, 30, 5),  # 5-6 pieces
        "spring roll": (150, 5, 20, 6),  # per piece
        
        # Breakfast
        "oatmeal": (150, 5, 27, 3),
        "cereal": (200, 4, 40, 2),
        "eggs": (140, 12, 1, 10),  # 2 eggs
        "toast": (80, 3, 15, 1),  # 1 slice
        "pancake": (175, 5, 30, 4),  # per pancake
        "waffle": (200, 6, 28, 7),
        
        # Protein
        "chicken breast": (165, 31, 0, 4),  # 100g
        "chicken": (200, 25, 0, 10),  # average portion
        "fish": (180, 25, 0, 8),
        "salmon": (200, 22, 0, 12),
        "beef": (250, 26, 0, 15),
        "pork": (240, 27, 0, 14),
        "tofu": (140, 15, 3, 8),
        "paneer": (265, 18, 3, 20),  # 100g
        
        # Vegetables (per cup)
        "salad": (50, 2, 8, 0),
        "vegetables": (50, 2, 10, 0),
        "broccoli": (55, 4, 11, 1),
        "spinach": (40, 5, 7, 1),
        
        # Fruits
        "banana": (105, 1, 27, 0),
        "apple": (95, 0, 25, 0),
        "orange": (62, 1, 15, 0),
        
        # Snacks
        "chips": (150, 2, 15, 10),  # small bag
        "cookies": (150, 2, 20, 7),  # 2-3 cookies
        "chocolate": (230, 3, 26, 13),  # bar
        "protein bar": (200, 15, 25, 6),
        "granola bar": (120, 2, 20, 4),
        
        # Beverages (per cup)
        "milk": (150, 8, 12, 8),
        "coffee": (5, 0, 0, 0),
        "tea": (2, 0, 0, 0),
        "juice": (120, 0, 28, 0),
        "soda": (140, 0, 39, 0),
        "smoothie": (200, 5, 40, 2),
        
        # Desserts
        "ice cream": (275, 5, 30, 15),
        "cake": (350, 4, 50, 15),
        "brownie": (240, 3, 35, 10),
        "donut": (250, 3, 30, 13),
        
        # Fast Food
        "burger": (500, 25, 45, 22),
        "fries": (320, 4, 43, 15),  # medium
        "nuggets": (280, 15, 20, 17),  # 6 pieces
        "taco": (200, 9, 18, 10),
        "burrito": (500, 20, 60, 18),
        
        # Specific branded/special items
        "organic kosher hamburger dill chips": (150, 1, 18, 8),  # per serving
        "kosher hamburger dill chips": (150, 1, 18, 8),
        "chicken hot dogs": (250, 12, 22, 12),
        "coffee ice cream": (200, 4, 24, 11),  # per scoop
        "chicken sandwich sauce": (50, 0, 2, 5),  # per 2 tbsp
        "ice cream sandwiches": (200, 3, 30, 8),  # per piece
        "chicken sausage sweet potato crust pizza": (280, 18, 28, 10),  # per slice
        "pizza dough": (150, 5, 30, 1),  # per serving
        "honey and sriracha chicken": (280, 32, 18, 8),  # per serving
    }
    
    # Category-based estimation patterns
    CATEGORY_PATTERNS = {
        "burger": (550, 28, 48, 24),
        "sandwich": (400, 20, 42, 14),
        "pizza": (285, 12, 36, 10),
        "curry": (300, 18, 18, 16),
        "rice": (250, 5, 50, 3),
        "pasta": (300, 10, 50, 6),
        "salad": (150, 8, 15, 6),
        "soup": (150, 8, 20, 4),
        "chicken": (250, 30, 5, 12),
        "fish": (200, 25, 2, 10),
        "dessert": (300, 4, 45, 12),
    }
    
    def estimate(
        self,
        meal_name: str,
        servings: float = 1.0,
        meal_type: str | None = None
    ) -> NutritionEstimate:
        """
        Estimate nutrition for a meal.
        
        Args:
            meal_name: Name of the food/meal
            servings: Number of servings (default 1.0)
            meal_type: breakfast, lunch, dinner, snack (helps with context)
        
        Returns:
            NutritionEstimate with calories and macros
        """
        meal_name_lower = meal_name.lower().strip()
        
        # Try exact match first
        if meal_name_lower in self.FOOD_DATABASE:
            base_cal, base_protein, base_carbs, base_fat = self.FOOD_DATABASE[meal_name_lower]
            return self._create_estimate(
                base_cal * servings,
                base_protein * servings,
                base_carbs * servings,
                base_fat * servings,
                confidence="high",
                notes=f"Based on common nutrition data for {meal_name}"
            )
        
        # Try fuzzy matching
        for food_key, (cal, protein, carbs, fat) in self.FOOD_DATABASE.items():
            if food_key in meal_name_lower or meal_name_lower in food_key:
                return self._create_estimate(
                    cal * servings,
                    protein * servings,
                    carbs * servings,
                    fat * servings,
                    confidence="high",
                    notes=f"Matched with {food_key} from database"
                )
        
        # Try category matching
        for category, (cal, protein, carbs, fat) in self.CATEGORY_PATTERNS.items():
            if category in meal_name_lower:
                return self._create_estimate(
                    cal * servings,
                    protein * servings,
                    carbs * servings,
                    fat * servings,
                    confidence="medium",
                    notes=f"Estimated based on {category} category"
                )
        
        # Generic estimation based on meal type
        if meal_type:
            base_cal, base_protein, base_carbs, base_fat = self._estimate_by_meal_type(meal_type)
            return self._create_estimate(
                base_cal * servings,
                base_protein * servings,
                base_carbs * servings,
                base_fat * servings,
                confidence="low",
                notes=f"Generic estimate for {meal_type} meal. Please adjust if needed."
            )
        
        # Last resort: generic meal estimate
        return self._create_estimate(
            400 * servings,
            20 * servings,
            45 * servings,
            12 * servings,
            confidence="low",
            notes="Generic meal estimate. Please provide more details for accuracy."
        )
    
    def _estimate_by_meal_type(self, meal_type: str) -> tuple:
        """Estimate based on meal type"""
        meal_type_lower = meal_type.lower()
        
        if meal_type_lower == "breakfast":
            return (350, 15, 45, 12)  # Typical breakfast
        elif meal_type_lower == "lunch":
            return (500, 25, 55, 18)  # Typical lunch
        elif meal_type_lower == "dinner":
            return (600, 30, 65, 20)  # Typical dinner
        elif meal_type_lower == "snack":
            return (200, 8, 25, 8)  # Typical snack
        else:
            return (400, 20, 45, 12)  # Generic meal
    
    def _create_estimate(
        self,
        calories: float,
        protein: float,
        carbs: float,
        fat: float,
        confidence: str,
        notes: str
    ) -> NutritionEstimate:
        """Create nutrition estimate with rounded values"""
        return NutritionEstimate(
            calories=int(round(calories)),
            protein_grams=int(round(protein)),
            carbs_grams=int(round(carbs)),
            fat_grams=int(round(fat)),
            confidence=confidence,
            notes=notes
        )
    
    def search_foods(self, query: str, limit: int = 10) -> list[dict]:
        """Search for foods in database (for autocomplete)"""
        query_lower = query.lower()
        matches = []
        
        for food_name, (cal, protein, carbs, fat) in self.FOOD_DATABASE.items():
            if query_lower in food_name:
                matches.append({
                    "name": food_name.title(),
                    "calories": cal,
                    "protein": protein,
                    "carbs": carbs,
                    "fat": fat
                })
        
        return matches[:limit]


# Singleton instance
nutrition_estimator = NutritionEstimator()
