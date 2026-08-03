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

    # 1) 30-minute-extension expiries — pause any session whose extension_ends_at <= now.
    ext_now = now_utc.isoformat()
    ext_open = await db.timer_sessions.find(
        {"ended_at": None, "extension_ends_at": {"$ne": None, "$lte": ext_now}},
        {"_id": 0},
    ).to_list(1000)
    for s in ext_open:
        try:
            started = _iso_to_dt(s["started_at"])
            if not started:
                continue
            duration = (s.get("duration_seconds", 0) or 0) + int((now_utc - started).total_seconds())
            await db.timer_sessions.update_one(
                {"id": s["id"]},
                {"$set": {"ended_at": now_utc.isoformat(),
                          "duration_seconds": duration,
                          "auto_paused": True,
                          "auto_paused_at": now_utc.isoformat(),
                          "paused_reason": "extension_expired"}},
            )
            await db.tasks.update_one(
                {"id": s["task_id"]},
                {"$set": {"status": "Paused", "updated_at": now_iso(),
                          "auto_paused_at": now_utc.isoformat()}},
            )
            task = await db.tasks.find_one({"id": s["task_id"]}, {"_id": 0, "title": 1})
            if task:
                await push_notification(
                    s["user_id"], "task_still_working",
                    "Still working? Tap to restart the timer",
                    f"{task.get('title', 'Task')} — auto-paused after 30 minutes",
                    link_type="task", link_id=s["task_id"],
                )
            await log_activity_raw(
                s["user_id"], "task_extension_expired", "task",
                s["task_id"], task_id=s["task_id"], new={"reason": "30m extension"},
            )
        except Exception as e:
            logger.exception("extension expiry failed: %s", e)

    if now_utc < cutoff_utc:
        return len(ext_open)

    # 2) 18:00 IST cutoff — pause sessions that started before it.
    open_sessions = await db.timer_sessions.find(
        {"ended_at": None, "started_at": {"$lt": cutoff_utc.isoformat()},
         "$or": [{"extension_ends_at": None}, {"extension_ends_at": {"$exists": False}}]},
        {"_id": 0},
    ).to_list(5000)
    paused = 0
    for s in open_sessions:
        try:
            if await _autopause_session(s, cutoff_utc):
                paused += 1
                # Nag notification: still working?
                task = await db.tasks.find_one({"id": s["task_id"]}, {"_id": 0, "title": 1})
                if task:
                    await push_notification(
                        s["user_id"], "task_still_working",
                        "Timer stopped at 6 PM IST — still working?",
                        f"{task.get('title', 'Task')} — tap to restart if you're continuing.",
                        link_type="task", link_id=s["task_id"],
                    )
        except Exception as e:
            logger.exception("auto-pause failed for session %s: %s", s.get("id"), e)
    if paused:
        logger.info("Auto-paused %d timer sessions at 18:00 IST", paused)
    return paused + len(ext_open)


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
