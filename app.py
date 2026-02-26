"""
ParrotOS - Main Application
Raspberry Pi parrot enrichment system
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
app_state = {
    "current_mode": "home",  # home, game, calm, admin
    "pellets_today": 0,
    "pellet_budget": 40,
    "bonus_earned": 0,
    "last_feeding": None,
    "is_calm_gate_active": False,
    "calm_cooldown_seconds": 120,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ParrotOS starting up...")
    yield
    logger.info("ParrotOS shutting down...")

app = FastAPI(title="ParrotOS", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# --- API Endpoints ---

@app.get("/api/state")
async def get_state():
    """Get current system state"""
    return app_state

@app.get("/api/mode/{mode}")
async def set_mode(mode: str):
    """Switch between home, game, calm, admin"""
    valid_modes = ["home", "game", "calm", "admin"]
    if mode not in valid_modes:
        raise HTTPException(400, f"Invalid mode. Use: {valid_modes}")
    app_state["current_mode"] = mode
    logger.info(f"Mode switched to: {mode}")
    return {"mode": mode, "state": app_state}

@app.post("/api/feed")
async def feed(amount: int = 10):
    """Dispense pellets (base feeding or bonus)"""
    if app_state["pellets_today"] + amount > app_state["pellet_budget"] + app_state["bonus_earned"]:
        raise HTTPException(400, "Pellet budget exceeded")
    
    app_state["pellets_today"] += amount
    app_state["last_feeding"] = datetime.now().isoformat()
    logger.info(f"Fed {amount}g. Total today: {app_state['pellets_today']}g")
    
    # TODO: Actual feeder control via Tuya API
    return {"fed": amount, "total_today": app_state["pellets_today"]}

@app.post("/api/game/score")
async def game_score(points: int):
    """Record game score (can earn bonus pellets)"""
    # TODO: Implement calm gate check before awarding
    app_state["bonus_earned"] = min(app_state["bonus_earned"] + points, 10)
    logger.info(f"Game score: {points}, bonus earned: {app_state['bonus_earned']}")
    return {"bonus_earned": app_state["bonus_earned"]}

@app.get("/api/wled/{effect}")
async def wled_effect(effect: str):
    """Trigger WLED effect"""
    # TODO: Actual WLED control
    logger.info(f"WLED effect: {effect}")
    return {"effect": effect}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)