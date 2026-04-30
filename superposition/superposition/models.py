import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, ForeignKey
)
from sqlalchemy.orm import relationship

from .db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")
    priority = Column(Integer, nullable=False, default=2)
    urgency = Column(Integer, nullable=False, default=2)
    risk = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    lanes = relationship("Lane", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="todo")
    priority = Column(Integer, nullable=False, default=2)
    urgency = Column(Integer, nullable=False, default=2)
    risk = Column(Integer, nullable=False, default=2)
    due_at = Column(DateTime, nullable=True)
    assigned_agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    approval_state = Column(String, nullable=True)
    created_from_ref = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="tasks")
    artifacts = relationship("Artifact", back_populates="task", cascade="all, delete-orphan")
    assigned_agent = relationship("Agent", back_populates="assigned_tasks")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    kind = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content_text = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    hash = Column(String, nullable=True)
    source_ref = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="artifacts")
    task = relationship("Task", back_populates="artifacts")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    schedule = Column(JSON, nullable=True)
    capability_mask = Column(JSON, nullable=True)
    parent_scope = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="idle")

    children = relationship("Agent", backref="parent", remote_side=[id])
    assigned_tasks = relationship("Task", back_populates="assigned_agent")
    runs = relationship("Run", back_populates="actor", cascade="all, delete-orphan")


class Process(Base):
    __tablename__ = "processes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    type = Column(String, nullable=False)
    command = Column(String, nullable=False)
    pid = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="starting")
    tty_info = Column(JSON, nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    lane_id = Column(String(36), nullable=True)

    runs = relationship("Run", back_populates="process", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    process_id = Column(String(36), ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    input = Column(JSON, nullable=True)
    output = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    process = relationship("Process", back_populates="runs")
    actor = relationship("Agent", back_populates="runs")
    project = relationship("Project", back_populates="runs")


class Lane(Base):
    __tablename__ = "lanes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    active_project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    layout_state = Column(JSON, nullable=True)
    pinned_panels = Column(JSON, nullable=True)
    recent_items = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="lanes")
