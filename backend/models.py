"""Pydantic models for Raybotix Digital task management app."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


# ---------- Users ----------
class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    first_name: str
    last_name: str = ""
    designation: str = "Other"
    role: str = "team_member"  # super_admin, admin, manager, team_member
    status: str = "pending"    # pending, active, deactivated, rejected
    avatar_url: str = ""
    monthly_salary: float = 0.0
    working_hours_per_day: float = 8.0
    working_days_per_month: int = 25
    theme: str = "system"
    permissions: List[str] = Field(default_factory=list)
    crm_access: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str = ""
    designation: str = "Other"


class UserPublic(UserBase):
    id: str
    last_login: Optional[str] = None
    created_at: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: Optional[str] = None
    new_password: str


class ApproveRequest(BaseModel):
    role: str = "team_member"
    designation: str = "Other"


class UserUpdateAdmin(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    monthly_salary: Optional[float] = None
    working_hours_per_day: Optional[float] = None
    working_days_per_month: Optional[int] = None
    avatar_url: Optional[str] = None
    permissions: Optional[List[str]] = None
    crm_access: Optional[bool] = None


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    theme: Optional[str] = None


# ---------- Projects ----------
class ProjectCreate(BaseModel):
    name: str
    company_name: str = ""
    client_name: str = ""
    description: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "active"
    member_ids: List[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    member_ids: Optional[List[str]] = None


# ---------- Tasks ----------
class Recurrence(BaseModel):
    enabled: bool = False
    frequency: str = "weekly"  # daily | weekly | monthly
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: str = "Medium"   # Low, Medium, Urgent
    status: str = "Assigned"
    scheduled_start_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_duration_minutes: int = 60
    tags: List[str] = Field(default_factory=list)
    instructions: str = ""
    reference_links: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    parent_task_id: Optional[str] = None
    recurrence: Optional[Recurrence] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    scheduled_start_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    instructions: Optional[str] = None
    reference_links: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    recurrence: Optional[Recurrence] = None


class HandoffRequest(BaseModel):
    next_assignee_id: str
    remarks: str = ""
    create_next_task: bool = False
    next_task: Optional[TaskCreate] = None


class ReopenRequest(BaseModel):
    assignee_id: str
    reason: str
    scheduled_start_date: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "Medium"
    instructions: str = ""


class ReviewRequest(BaseModel):
    action: str  # approve, request_changes, reopen
    comment: str = ""


# ---------- Messages ----------
class MessageCreate(BaseModel):
    conversation_id: Optional[str] = None
    recipient_ids: List[str] = Field(default_factory=list)  # for creating new conversation
    body: str
    tagged_task_id: Optional[str] = None
    tagged_project_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    participant_ids: List[str]
    name: str = ""


# ---------- Settings ----------
class CompanySettings(BaseModel):
    company_name: str = "Raybotix Digital"
    company_logo_url: str = ""
    app_logo_url: str = ""
    app_icon_url: str = ""
    address: str = ""
    contact: str = ""
    currency: str = "INR"
    working_days_per_month: int = 25
    default_working_hours_per_day: float = 8.0
    allow_multiple_active_timers: bool = False
    designations: List[str] = Field(
        default_factory=lambda: [
            "Video Editor", "SEO Executive", "Content Writer",
            "Digital Marketing Executive", "Graphic Designer",
            "Social Media Manager", "Performance Marketing Executive",
            "Web Developer", "Manager", "Other",
        ]
    )
    task_statuses: List[str] = Field(
        default_factory=lambda: [
            "Planned", "Scheduled", "Assigned", "Not Started",
            "In Progress", "Paused", "Waiting for Review",
            "Completed", "Reopened", "Overdue", "Cancelled",
        ]
    )
    priorities: List[str] = Field(default_factory=lambda: ["Low", "Medium", "Urgent"])


# ---------- CRM: Leads / Inquiries ----------
LEAD_STAGES = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Onboarded", "Lost"]


class LeadActivity(BaseModel):
    id: str = Field(default_factory=uid)
    kind: str = "note"       # note, call, meeting, task, email
    description: str
    due_date: Optional[str] = None
    done: bool = False
    created_by_id: str
    created_by_name: str = ""
    created_at: str = Field(default_factory=now_iso)


class LeadCreate(BaseModel):
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    source: str = "Website"          # Website, Referral, Cold Call, Ad, Other
    stage: str = "New"
    next_step: str = ""
    follow_up_date: Optional[str] = None
    assigned_to_id: Optional[str] = None
    notes: str = ""
    value_estimate: float = 0.0
    services: List[str] = Field(default_factory=list)


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    stage: Optional[str] = None
    next_step: Optional[str] = None
    follow_up_date: Optional[str] = None
    assigned_to_id: Optional[str] = None
    notes: Optional[str] = None
    value_estimate: Optional[float] = None
    services: Optional[List[str]] = None


class LeadActivityCreate(BaseModel):
    kind: str = "note"
    description: str
    due_date: Optional[str] = None
    done: bool = False


class LeadOnboardRequest(BaseModel):
    project_name: Optional[str] = None
    company_name: Optional[str] = None
    member_ids: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

