"""
Database Schemas for LifeStory

Each Pydantic model below maps to a MongoDB collection.
Collection name is the lowercase of the class name (e.g., Season -> "season").
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class Season(BaseModel):
    title: str = Field(..., description="Season title")
    description: Optional[str] = Field(None, description="Short description for the season")
    start_date: Optional[date] = Field(None, description="When this season starts")
    end_date: Optional[date] = Field(None, description="When this season ends")
    is_active: bool = Field(True, description="Whether this is the active season")

class Episode(BaseModel):
    title: str = Field(..., description="Episode title")
    date: date = Field(..., description="Date of the episode")
    rating: int = Field(..., ge=1, le=10, description="Day rating 1-10")
    plot_points: List[str] = Field(default_factory=list, description="Bulleted list of key moments")
    season_id: Optional[str] = Field(None, description="ID of the season this episode belongs to (string ObjectId)")
