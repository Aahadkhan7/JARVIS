from pydantic import BaseModel, Field
from typing import Optional


class Task(BaseModel):
    title: str
    due_date: Optional[str] = None
    completed: bool = False


class CalendarEvent(BaseModel):
    title: str
    date: str
    time: Optional[str] = None
    description: Optional[str] = None


class MemoryFact(BaseModel):
    fact: str = Field(
        description="A fact to remember about the user"
    )


class AgentPlan(BaseModel):
    steps: list[str] = Field(
        description="Clear ordered steps needed to complete the user's request"
    )