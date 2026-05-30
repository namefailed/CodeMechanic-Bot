from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import yaml
import json
import os
import subprocess
import psutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bounty_tracker.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
ACTIVITY_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ollama_activity.json")
ORCHESTRATOR_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bugbot.log")
UI_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")
BOT_PROCESS = None

@app.get("/api/status")
def get_status():
    global BOT_PROCESS
    is_running = False
    if BOT_PROCESS:
        try:
            # Check if process is actually running
            p = psutil.Process(BOT_PROCESS.pid)
            if p.status() != psutil.STATUS_ZOMBIE:
                is_running = True
        except psutil.NoSuchProcess:
            BOT_PROCESS = None
    return {"status": "running" if is_running else "stopped"}

@app.post("/api/bot/start")
def start_bot(stealth: bool = False):
    global BOT_PROCESS
    if BOT_PROCESS and psutil.pid_exists(BOT_PROCESS.pid):
        return {"message": "Already running"}
    
    cmd = ["python", "orchestrator.py"]
    if stealth:
        cmd.append("--stealth")
        
    cwd = os.path.dirname(os.path.dirname(__file__))
    BOT_PROCESS = subprocess.Popen(cmd, cwd=cwd)
    return {"message": "Bot started"}

@app.post("/api/bot/stop")
def stop_bot():
    global BOT_PROCESS
    if BOT_PROCESS and psutil.pid_exists(BOT_PROCESS.pid):
        parent = psutil.Process(BOT_PROCESS.pid)
        for child in parent.children(recursive=True):
            child.terminate()
        parent.terminate()
        BOT_PROCESS = None
        return {"message": "Bot stopped"}
    return {"message": "Not running"}

@app.get("/api/config")
def get_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

@app.post("/api/config")
def save_config(config_data: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config_data, f)
    return {"message": "Config saved"}

@app.get("/api/prs")
def get_prs():
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT issue_url, repo_name, status, updated_at FROM processed_issues ORDER BY updated_at DESC")
        rows = cur.fetchall()
        return [{"issue_url": r[0], "repo": r[1], "status": r[2], "updated_at": r[3]} for r in rows]
    except Exception as e:
        return []

@app.get("/api/activity")
def get_activity():
    if not os.path.exists(ACTIVITY_LOG):
        return []
    try:
        with open(ACTIVITY_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

@app.get("/api/logs")
def get_logs():
    if not os.path.exists(ORCHESTRATOR_LOG):
        return {"logs": "No logs yet."}
    try:
        with open(ORCHESTRATOR_LOG, "r", encoding="utf-8") as f:
            # Return last 200 lines
            lines = f.readlines()
            return {"logs": "".join(lines[-200:])}
    except:
        return {"logs": "Error reading logs."}

if os.path.exists(UI_PATH):
    app.mount("/", StaticFiles(directory=UI_PATH, html=True), name="ui")
