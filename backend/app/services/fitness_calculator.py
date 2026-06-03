"""
Fitness calculation engine for steps, calories, hydration, and intensity.
Uses standard fitness formulas and user profile data.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FitnessMetrics:
    """Calculated fitness metrics for an activity"""
    steps: int
    calories: float
    hydration_loss_ml: float
    intensity: str  # "low", "moderate", "high", "very_high"
    met_value: float  # Metabolic Equivalent of Task


class FitnessCalculator:
    """
    Calculates fitness metrics based on activity type, duration, and user profile.
    
    Formulas used:
    - Calories: MET × weight(kg) × duration(hours)
    - Steps: Based on activity type and duration
    - Hydration: Based on intensity and duration
    """
    
    # MET (Metabolic Equivalent of Task) values for different activities
    # Source: Compendium of Physical Activities
    MET_VALUES = {
        # Cardio activities
        "running": 9.8,          # ~10 min/mile pace
        "jogging": 7.0,          # ~12 min/mile pace
        "walking": 3.5,          # ~3 mph
        "hiking": 6.0,
        "cycling": 7.5,          # moderate effort
        "swimming": 8.0,         # moderate effort
        "dancing": 5.0,
        
        # Sports
        "basketball": 6.5,
        "soccer": 7.0,
        "tennis": 7.3,
        "badminton": 5.5,
        "volleyball": 4.0,
        "cricket": 4.8,
        
        # Gym activities
        "weightlifting": 6.0,
        "strength_training": 5.0,
        "gym": 5.5,
        "cardio": 7.0,
        
        # Mind-body
        "yoga": 2.5,
        "pilates": 3.0,
        "stretching": 2.3,
        "meditation": 1.0,
        
        # Other
        "stairs": 8.0,
        "jump_rope": 12.0,
        "elliptical": 5.0,
        "rowing": 7.0,
    }
    
    # Steps per minute for different activities
    STEPS_PER_MINUTE = {
        "running": 160,          # ~160 steps/min
        "jogging": 140,          # ~140 steps/min
        "walking": 100,          # ~100 steps/min
        "hiking": 110,
        "dancing": 120,
        "basketball": 130,
        "soccer": 140,
        "tennis": 100,
        "badminton": 110,
        "volleyball": 90,
        "cricket": 80,
        "stairs": 150,
        "jump_rope": 180,
        # Activities with minimal steps
        "cycling": 0,
        "swimming": 0,
        "yoga": 20,
        "pilates": 30,
        "stretching": 10,
        "meditation": 0,
        "weightlifting": 40,
        "strength_training": 40,
        "gym": 50,
        "rowing": 0,
        "elliptical": 120,
    }
    
    def __init__(self):
        pass
    
    def calculate_metrics(
        self,
        activity_name: str,
        duration_minutes: int,
        user_weight_kg: float = 70.0,  # Default average weight
        user_age: int = 30,
        user_gender: str = "male"
    ) -> FitnessMetrics:
        """
        Calculate comprehensive fitness metrics for an activity.
        
        Args:
            activity_name: Type of activity (e.g., "running", "yoga")
            duration_minutes: Duration in minutes
            user_weight_kg: User's weight in kg
            user_age: User's age
            user_gender: User's gender ("male" or "female")
        
        Returns:
            FitnessMetrics with calculated values
        """
        # Normalize activity name
        activity_name = activity_name.lower().strip()
        
        # Get MET value
        met_value = self._get_met_value(activity_name)
        
        # Calculate calories
        calories = self._calculate_calories(met_value, user_weight_kg, duration_minutes)
        
        # Calculate steps
        steps = self._calculate_steps(activity_name, duration_minutes)
        
        # Calculate hydration loss
        hydration_loss_ml = self._calculate_hydration_loss(
            met_value, duration_minutes, user_weight_kg
        )
        
        # Determine intensity
        intensity = self._determine_intensity(met_value)
        
        return FitnessMetrics(
            steps=steps,
            calories=round(calories, 1),
            hydration_loss_ml=round(hydration_loss_ml, 0),
            intensity=intensity,
            met_value=met_value
        )
    
    def _get_met_value(self, activity_name: str) -> float:
        """Get MET value for activity, with fuzzy matching"""
        # Direct match
        if activity_name in self.MET_VALUES:
            return self.MET_VALUES[activity_name]
        
        # Fuzzy matching
        for key in self.MET_VALUES:
            if key in activity_name or activity_name in key:
                return self.MET_VALUES[key]
        
        # Default to moderate activity
        return 5.0
    
    def _calculate_calories(
        self, 
        met_value: float, 
        weight_kg: float, 
        duration_minutes: int
    ) -> float:
        """
        Calculate calories burned using MET formula.
        Formula: Calories = MET × weight(kg) × duration(hours)
        """
        duration_hours = duration_minutes / 60.0
        calories = met_value * weight_kg * duration_hours
        return calories
    
    def _calculate_steps(self, activity_name: str, duration_minutes: int) -> int:
        """Calculate estimated steps for activity"""
        # Get steps per minute
        steps_per_min = self.STEPS_PER_MINUTE.get(activity_name, 0)
        
        # Fuzzy matching
        if steps_per_min == 0:
            for key in self.STEPS_PER_MINUTE:
                if key in activity_name or activity_name in key:
                    steps_per_min = self.STEPS_PER_MINUTE[key]
                    break
        
        # Calculate total steps
        total_steps = steps_per_min * duration_minutes
        return int(total_steps)
    
    def _calculate_hydration_loss(
        self, 
        met_value: float, 
        duration_minutes: int,
        weight_kg: float
    ) -> float:
        """
        Calculate estimated hydration loss (sweat) in ml.
        
        Formula: Sweat rate increases with intensity
        - Light activity: ~300-500 ml/hour
        - Moderate activity: ~500-800 ml/hour
        - High activity: ~800-1200 ml/hour
        """
        duration_hours = duration_minutes / 60.0
        
        # Base sweat rate (ml/hour) based on MET value
        if met_value < 3:
            sweat_rate = 300  # Light
        elif met_value < 6:
            sweat_rate = 600  # Moderate
        elif met_value < 9:
            sweat_rate = 900  # High
        else:
            sweat_rate = 1100  # Very high
        
        # Adjust for body weight (heavier people sweat more)
        weight_factor = weight_kg / 70.0  # Normalized to 70kg
        adjusted_sweat_rate = sweat_rate * weight_factor
        
        # Calculate total loss
        total_loss = adjusted_sweat_rate * duration_hours
        return total_loss
    
    def _determine_intensity(self, met_value: float) -> str:
        """Determine workout intensity based on MET value"""
        if met_value < 3:
            return "low"
        elif met_value < 6:
            return "moderate"
        elif met_value < 9:
            return "high"
        else:
            return "very_high"
    
    def get_recommendation(self, metrics: FitnessMetrics) -> dict:
        """
        Generate proactive recommendations based on calculated metrics.
        
        Returns:
            Dict with recommendations for hydration, recovery, nutrition
        """
        recommendations = {
            "hydration": None,
            "recovery": None,
            "nutrition": None,
            "next_activity": None
        }
        
        # Hydration recommendation
        if metrics.hydration_loss_ml > 500:
            water_glasses = int(metrics.hydration_loss_ml / 250)  # 250ml per glass
            recommendations["hydration"] = (
                f"Great workout! Drink {water_glasses} glasses of water "
                f"({int(metrics.hydration_loss_ml)}ml) to rehydrate."
            )
        
        # Recovery recommendation based on intensity
        if metrics.intensity == "very_high":
            recommendations["recovery"] = (
                "That was intense! Take 24-48 hours to recover. "
                "Consider light stretching or yoga tomorrow."
            )
        elif metrics.intensity == "high":
            recommendations["recovery"] = (
                "Nice effort! Rest for 12-24 hours. "
                "Light activity tomorrow is fine."
            )
        
        # Nutrition recommendation based on calories
        if metrics.calories > 300:
            recommendations["nutrition"] = (
                f"You burned {int(metrics.calories)} calories! "
                "Consider a protein-rich snack within 30 minutes for recovery."
            )
        
        # Next activity suggestion
        if metrics.intensity in ["low", "moderate"]:
            recommendations["next_activity"] = (
                "You can do another workout today if you feel energized!"
            )
        
        return recommendations


# Singleton instance
fitness_calculator = FitnessCalculator()
