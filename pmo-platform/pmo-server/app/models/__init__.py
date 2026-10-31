"""所有 SQLAlchemy 模型（基于 TSD §3 DDL，适配 SQLite）。"""
from app.models.base import Base  # noqa: F401
from app.models.identity import Dept, User, Role, RoleBinding, DataDomain, SyncConflict, ExternalAccount
from app.models.project import (
    Program, ProjectType, Project, ProjectStakeholder,
    StageTemplate, GateTemplate, ChecklistTemplate,
    ProjectStage, Gate, ChecklistInstance, Review, ReviewItem, ReviewSignoff,
)
from app.models.task import Wbs, Task, TaskRaci, Dependency, Baseline, BaselineTask, Milestone
from app.models.collab import (
    Ticket, TicketAction, Meeting, MeetingDecision,
    WeeklyReport, TodoItem, Notification, NotificationRule,
)
from app.models.platform import (
    Attachment, AuditLog, ImportJob, Dictionary, Template,
    SecrecyChangeRequest, IntegrationConfig, AiCallLog,
)
from app.models.resource import (
    Skill, MemberSkill, ResourcePool, Reservation,
    LabResource, LabBooking, Batch, BatchMilestone, CostShare,
    Budget, CostLedger, Timesheet,
)
from app.models.risk import Risk, Issue, ChangeRequest
from app.models.handoff import Deliverable
