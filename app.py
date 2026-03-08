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
import json
from pathlib import Path
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

# Path to static apps
APPS_DIR = Path("static/apps")

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

# --- App Framework API ---

@app.get("/api/apps")
async def get_apps():
    """Get list of all available apps"""
    apps = []
    
    if not APPS_DIR.exists():
        return apps
    
    for app_folder in APPS_DIR.iterdir():
        if app_folder.is_dir():
            manifest_file = app_folder / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                        apps.append(manifest)
                except:
                    pass
    
    # Sort by sort_order
    apps.sort(key=lambda x: x.get('sort_order', 999))
    return apps

@app.get("/api/app/{app_id}")
async def get_app(app_id: str):
    """Get app content by ID"""
    app_path = APPS_DIR / app_id
    
    if not app_path.exists():
        raise HTTPException(404, "App not found")
    
    # Load manifest
    manifest_file = app_path / "manifest.json"
    if not manifest_file.exists():
        raise HTTPException(404, "App manifest not found")
    
    with open(manifest_file) as f:
        manifest = json.load(f)
    
    # Load HTML content
    html_content = ""
    index_file = app_path / "index.html"
    if index_file.exists():
        with open(index_file) as f:
            html_content = f.read()
    
    return {
        "id": manifest.get("id"),
        "name": manifest.get("name"),
        "icon": manifest.get("icon"),
        "timeout_seconds": manifest.get("timeout_seconds", 60),
        "description": manifest.get("description", ""),
        "html": html_content
    }

# --- Existing API Endpoints ---

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

@app.get("/api/config")
async def get_config():
    """Get system configuration"""
    return {
        "led_ip": "192.168.1.100",
        "feeder_enabled": True,
        "camera_enabled": True,
        "pellet_budget": 40,
        "bonus_max": 10
    }

@app.get("/api/camera/status")
async def camera_status():
    """Get camera status"""
    return {
        "motion_detected": False,
        "sound_detected": False,
        "connected": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)