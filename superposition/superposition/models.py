import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, ForeignKey, MetaData
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .db import Base

# Naming convention for constraints (optional)
# convention = {
#     "ix": "ix_%(column_0_label)s",
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(constraint_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }
# Base = declarative_base(metadata=MetaData(naming_convention=convention))
# Already defined in db.py

def generate_uuid():
    return uuid.uuid4()

class Project(Base):
    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, paused, archived
    priority = Column(Integer, nullable=False, default=2)  # 0-4 (0=critical, 2=medium, 4=backlog)
    urgency = Column(Integer, nullable=False, default=2)
    risk = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    lanes = relationship("Lane", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="todo")  # todo, in_progress, done, blocked
    priority = Column(Integer, nullable=False, default=2)
    urgency = Column(Integer, nullable=False, default=2)
    risk = Column(Integer, nullable=False, default=2)
    due_at = Column(DateTime, nullable=True)
    assigned_agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    approval_state = Column(String, nullable=True)  # pending, approved, rejected
    created_from_ref = Column(String, nullable=True)  # reference to source (message_id, cell_id)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    project = relationship("Project", back_populates="tasks")
    artifacts = relationship("Artifact", back_populates="task", cascade="all, delete-orphan")
    assigned_agent = relationship("Agent", back_populates="assigned_tasks")
    runs = relationship("Run", back_populates="task", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    kind = Column(String, nullable=False)  # file, snippet, chunk, output, patch, note
    title = Column(String, nullable=False)
    content_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    hash = Column(String, nullable=True)  # checksum (sha256 etc)
    source_ref = Column(String, nullable=True)  # e.g., chatbook_message_id, run_id
    tags = Column(JSON, nullable=True)  # array of tags
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    project = relationship("Project", back_populates="artifacts")
    task = relationship("Task", back_populates="artifacts")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    mode = Column(String, nullable=False)  # fulltime, parttime, temporary
    schedule = Column(JSON, nullable=True)  # cron-like schedule dict
    capability_mask = Column(JSON, nullable=True)  # list of capabilities or permissions
    parent_scope = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="idle")  # idle, running, paused

    # relationships
    children = relationship("Agent", backref="parent", remote_side=[id])
    assigned_tasks = relationship("Task", back_populates="assigned_agent")
    runs = relationship("Run", back_populates="actor", cascade="all, delete-orphan")


class Process(Base):
    __tablename__ = "processes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    type = Column(String, nullable=False)  # terminal, agent_job, etc.
    command = Column(String, nullable=False)
    pid = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="starting")  # starting, running, exited, error
    tty_info = Column(JSON, nullable=True)  # e.g., session id, row/col, etc.
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    lane_id = Column(PGUUID(as_uuid=True), nullable=True)  # lane reference (not FK to allow early creation)

    # relationships
    project = relationship("Project", back_populates="runs")
    task = relationship("Task", back_populates="runs")
    runs = relationship("Run", back_populates="process", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    process_id = Column(PGUUID(as_uuid=True), ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    input = Column(JSON, nullable=True)  # input data for the run
    output = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # success, failure, cancelled
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    # relationships
    process = relationship("Process", back_populates="runs")
    actor = relationship("Agent", back_populates="runs")
    project = relationship("Project", back_populates="runs")  # denormalized via process?


class Lane(Base):
    __tablename__ = "lanes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    active_project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    layout_state = Column(JSON, nullable=True)
    pinned_panels = Column(JSON, nullable=True)
    recent_items = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships
    project = relationship("Project", back_populates="lanes")
