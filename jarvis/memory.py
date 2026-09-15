import sqlite3
from pathlib import Path

import chromadb


BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "memory.db"
CHROMA_PATH = BASE_DIR / "data" / "chroma_db"


def setup_database():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DB_PATH)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def get_chroma_collection():

    CHROMA_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_or_create_collection(
        name="jarvis_memories"
    )

    return collection


def store_fact(fact: str):

    setup_database()

    fact = fact.strip()

    if not fact:
        return "TOOL_ERROR: Memory fact cannot be empty."

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.execute(
        "INSERT INTO memories (fact) VALUES (?)",
        (fact,)
    )

    memory_id = cursor.lastrowid

    connection.commit()
    connection.close()

    collection = get_chroma_collection()

    collection.upsert(
        ids=[str(memory_id)],
        documents=[fact],
        metadatas=[
            {
                "memory_id": memory_id
            }
        ]
    )

    return "Memory saved successfully."


def search_facts(query: str):

    setup_database()

    query = query.strip()

    if not query:
        return []

    collection = get_chroma_collection()

    try:

        results = collection.query(
            query_texts=[query],
            n_results=5
        )

        documents = results.get(
            "documents",
            []
        )

        if documents and documents[0]:

            return documents[0]

    except Exception:
        pass

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.execute(
        """
        SELECT fact
        FROM memories
        WHERE LOWER(fact) LIKE ?
        """,
        (f"%{query.lower()}%",)
    )

    results = [
        row[0]
        for row in cursor.fetchall()
    ]

    connection.close()

    return results