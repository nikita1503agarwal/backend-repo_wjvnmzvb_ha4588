import os
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="LifeStory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Utilities --------------------

def to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = {**doc}
    if d.get("_id") is not None:
        d["id"] = str(d.pop("_id"))
    # Convert any ObjectId fields to str
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d

# -------------------- Schemas --------------------

class SeasonIn(BaseModel):
    title: str = Field(...)
    description: Optional[str] = Field(None)
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)
    is_active: bool = Field(True)

class SeasonOut(SeasonIn):
    id: str

class EpisodeIn(BaseModel):
    title: str
    date: date
    rating: int = Field(..., ge=1, le=10)
    plot_points: List[str] = Field(default_factory=list)
    season_id: Optional[str] = Field(None)

class EpisodeOut(EpisodeIn):
    id: str

# -------------------- Basic --------------------

@app.get("/")
def read_root():
    return {"message": "LifeStory Backend is running"}

@app.get("/test")
def test_database():
    response: Dict[str, Any] = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:60]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:60]}"
    return response

# -------------------- Season Routes --------------------

@app.get("/api/seasons", response_model=List[SeasonOut])
def list_seasons():
    items = get_documents("season")
    return [SeasonOut(**to_str_id(i)) for i in items]

@app.post("/api/seasons", response_model=SeasonOut)
def create_season(payload: SeasonIn):
    data = payload.model_dump()
    # If creating an active season, set other seasons to inactive
    if data.get("is_active"):
        db["season"].update_many({}, {"$set": {"is_active": False}})
    new_id = create_document("season", data)
    created = db["season"].find_one({"_id": ObjectId(new_id)})
    return SeasonOut(**to_str_id(created))

@app.patch("/api/seasons/{season_id}", response_model=SeasonOut)
def update_season(season_id: str, payload: SeasonIn):
    try:
        oid = ObjectId(season_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid season id")
    data = payload.model_dump()
    if data.get("is_active"):
        db["season"].update_many({}, {"$set": {"is_active": False}})
    res = db["season"].find_one_and_update({"_id": oid}, {"$set": data}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Season not found")
    return SeasonOut(**to_str_id(res))

@app.delete("/api/seasons/{season_id}")
def delete_season(season_id: str):
    try:
        oid = ObjectId(season_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid season id")
    result = db["season"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Season not found")
    # Orphan episodes move to unsorted (season_id None)
    db["episode"].update_many({"season_id": season_id}, {"$set": {"season_id": None}})
    return {"status": "ok"}

# -------------------- Episode Routes --------------------

@app.get("/api/episodes", response_model=List[EpisodeOut])
def list_episodes(season_id: Optional[str] = Query(None), unsorted: bool = Query(False)):
    q: Dict[str, Any] = {}
    if unsorted:
        q["season_id"] = None
    elif season_id is not None:
        q["season_id"] = season_id
    items = get_documents("episode", q)
    return [EpisodeOut(**to_str_id(i)) for i in items]

@app.post("/api/episodes", response_model=EpisodeOut)
def create_episode(payload: EpisodeIn):
    data = payload.model_dump()
    new_id = create_document("episode", data)
    created = db["episode"].find_one({"_id": ObjectId(new_id)})
    return EpisodeOut(**to_str_id(created))

@app.patch("/api/episodes/{episode_id}", response_model=EpisodeOut)
def update_episode(episode_id: str, payload: EpisodeIn):
    try:
        oid = ObjectId(episode_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid episode id")
    data = payload.model_dump()
    res = db["episode"].find_one_and_update({"_id": oid}, {"$set": data}, return_document=True)
    if not res:
        raise HTTPException(status_code=404, detail="Episode not found")
    return EpisodeOut(**to_str_id(res))

@app.delete("/api/episodes/{episode_id}")
def delete_episode(episode_id: str):
    try:
        oid = ObjectId(episode_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid episode id")
    result = db["episode"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"status": "ok"}

# -------------------- Schema Introspection --------------------

@app.get("/schema")
def get_schema_definitions():
    # Expose basic schema info for inspector tools
    from schemas import Season, Episode  # type: ignore
    return {
        "season": Season.model_json_schema(),
        "episode": Episode.model_json_schema(),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
