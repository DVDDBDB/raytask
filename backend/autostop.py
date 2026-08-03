"""Timer auto-stop scheduler.

At every tick, any timer_sessions that are still open (`ended_at is None`)
past 18:00 Asia/Kolkata are auto-paused so we don't accrue overnight cost.
Users then see a "Resume yesterday?" popup on next login.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta, time as dtime
from db import db
from utils import now_iso, push_notification, log_activity_raw

logger = logging.getLogger("raybotix.autostop")

IST = timezone(timedelta(hours=5, minutes=30))
CUTOFF_HOUR_IST = 18  # 6 PM IST


def _iso_to_dt(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _ist_cutoff_today_utc(ref: datetime) -> datetime:
    """Return the 18:00 IST cutoff for the IST calendar day that `ref` (UTC) falls in — expressed in UTC."""
    ist = ref.astimezone(IST)
    cutoff_ist = datetime.combine(ist.date(), dtime(hour=CUTOFF_HOUR_IST), tzinfo=IST)
    return cutoff_ist.astimezone(timezone.utc)


async def _autopause_session(session: dict, cutoff_utc: datetime):
    """Pause a session at the cutoff time and update the task."""
    started = _iso_to_dt(session["started_at"])
    if not started:
        return False
    # If the session actually started AFTER the cutoff today, don't touch it.
    if started >= cutoff_utc:
        return False
    # Session was already ended by someone else in the meantime
    fresh = await db.timer_sessions.find_one({"id": session["id"]}, {"_id": 0})
    if not fresh or fresh.get("ended_at"):
        return False
    added = int((cutoff_utc - started).total_seconds())
    if added < 0:
        added = 0
    duration = added + (fresh.get("duration_seconds", 0) or 0)
    await db.timer_sessions.update_one(
        {"id": session["id"]},
        {"$set": {
            "ended_at": cutoff_utc.isoformat(),
            "duration_seconds": duration,
            "auto_paused": True,
            "auto_paused_at": cutoff_utc.isoformat(),
        }},
    )
    await db.tasks.update_one(
        {"id": session["task_id"]},
        {"$set": {"status": "Paused", "updated_at": now_iso(),
                  "auto_paused_at": cutoff_utc.isoformat()}},
    )
    task = await db.tasks.find_one({"id": session["task_id"]}, {"_id": 0, "title": 1})
    if task:
        await push_notification(
            session["user_id"], "task_auto_paused",
            "Timer auto-stopped at 6 PM IST",
            task.get("title", "Task"),
            link_type="task", link_id=session["task_id"],
        )
    await log_activity_raw(
        session["user_id"], "task_auto_paused", "task",
        session["task_id"], task_id=session["task_id"], new={"reason": "6pm IST cutoff"},
    )
    return True


async def _tick():
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = _ist_cutoff_today_utc(now_utc)
    if now_utc < cutoff_utc:
        return 0  # cutoff hasn't happened yet in IST
    # Find open sessions started before today's cutoff.
    open_sessions = await db.timer_sessions.find(
        {"ended_at": None, "started_at": {"$lt": cutoff_utc.isoformat()}},
        {"_id": 0},
    ).to_list(5000)
    paused = 0
    for s in open_sessions:
        try:
            if await _autopause_session(s, cutoff_utc):
                paused += 1
        except Exception as e:
            logger.exception("auto-pause failed for session %s: %s", s.get("id"), e)
    if paused:
        logger.info("Auto-paused %d timer sessions at 18:00 IST", paused)
    return paused


async def loop(interval_seconds: int = 60):
    while True:
        try:
            await _tick()
        except Exception as e:
            logger.exception("Auto-stop tick failed: %s", e)
        await asyncio.sleep(interval_seconds)


_scheduler_task = None


def start_scheduler(loop_object):
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = loop_object.create_task(loop())
