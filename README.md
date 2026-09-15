# JARVIS - Personal AI Operating Assistant

JARVIS is a personal AI operating assistant built with Python.

## Features

- Natural language understanding
- English and Hinglish support
- Task management
- Calendar management
- Long-term memory
- Semantic memory using ChromaDB
- Mathematical calculations
- Weather information
- Multi-step planning
- Error recovery
- Confirmation for destructive actions
- Smart study planning
- Text mode
- Voice input
- Voice output

## Technology Stack

- Python
- Groq
- LangChain
- LangGraph
- Pydantic
- SQLite
- ChromaDB
- Requests
- SoundDevice
- SoundFile

## Architecture

User
↓
Understand
↓
Plan
↓
Act
↓
Observe
↓
Re-plan / Respond

## Memory

JARVIS uses:

- SQLite for persistent memory storage
- ChromaDB for semantic memory search

## Task Management

JARVIS can:

- Create tasks
- View tasks
- Update tasks
- Complete tasks
- Detect duplicate tasks
- Protect destructive task deletion with confirmation

## Calendar

JARVIS can:

- Create calendar events
- View calendar events
- Check events for specific dates
- Use calendar information while creating study plans

## Smart Study Planner

JARVIS can combine:

- Pending tasks
- Calendar commitments
- Remembered information

and create a practical study plan while avoiding existing commitments.

## Voice System

Voice pipeline:

Microphone
↓
Speech Recognition
↓
JARVIS AI
↓
Tools
↓
Response
↓
Text-to-Speech
↓
Speaker

## Running JARVIS

### Text Mode

```text
python -m jarvis.main