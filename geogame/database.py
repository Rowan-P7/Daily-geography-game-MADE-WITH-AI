import json
import sqlite3
from contextlib import closing
from pathlib import Path

from geogame.question_bank import build_questions, serialize_question
from geogame.minigames import get_challenge_bank, serialize_challenge


def connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL REFERENCES players(id),
                mode TEXT NOT NULL CHECK (mode IN ('daily', 'practice')),
                game_date TEXT,
                status TEXT NOT NULL CHECK (status IN ('in_progress', 'complete')),
                question_ids_json TEXT NOT NULL,
                questions_json TEXT,
                answers_json TEXT NOT NULL DEFAULT '[]',
                round_state_json TEXT NOT NULL DEFAULT '{}',
                score INTEGER NOT NULL DEFAULT 0,
                started_at REAL NOT NULL,
                question_started_at REAL NOT NULL,
                completed_at REAL,
                UNIQUE(player_id, mode, game_date)
            );
            CREATE TABLE IF NOT EXISTS daily_challenges (
                game_date TEXT PRIMARY KEY,
                questions_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mini_game_challenges (
                id TEXT PRIMARY KEY,
                game_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                source_json TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS games_completed_idx
                ON games(mode, game_date, status, score DESC);
            CREATE TABLE IF NOT EXISTS question_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL REFERENCES players(id),
                question_id TEXT NOT NULL REFERENCES questions(id),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mini_game_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL REFERENCES players(id),
                challenge_id TEXT NOT NULL REFERENCES mini_game_challenges(id),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        game_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(games)").fetchall()
        }
        if "questions_json" not in game_columns:
            connection.execute("ALTER TABLE games ADD COLUMN questions_json TEXT")
        if "round_state_json" not in game_columns:
            connection.execute("ALTER TABLE games ADD COLUMN round_state_json TEXT NOT NULL DEFAULT '{}'")
        for question in build_questions():
            connection.execute(
                "INSERT INTO questions (id, category, difficulty, data_json) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET category = excluded.category, "
                "difficulty = excluded.difficulty, data_json = excluded.data_json",
                (question["id"], question["category"], question["difficulty"], serialize_question(question)),
            )
        for challenge in get_challenge_bank():
            connection.execute(
                "INSERT INTO mini_game_challenges (id, game_type, difficulty, source_json, data_json) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "game_type = excluded.game_type, difficulty = excluded.difficulty, "
                "source_json = excluded.source_json, data_json = excluded.data_json",
                (
                    challenge["id"], challenge["game_type"], challenge["difficulty"],
                    json.dumps(challenge["source"], ensure_ascii=False),
                    serialize_challenge(challenge),
                ),
            )
        connection.commit()


def get_question(connection, question_id):
    row = connection.execute("SELECT data_json FROM questions WHERE id = ?", (question_id,)).fetchone()
    if row is None:
        raise LookupError(f"Question {question_id} is missing from the question bank")
    return json.loads(row["data_json"])


def load_question_bank(connection):
    rows = connection.execute("SELECT data_json FROM questions ORDER BY id").fetchall()
    return [json.loads(row["data_json"]) for row in rows]


def load_challenge_bank(connection, game_type=None, difficulty=None):
    query = "SELECT data_json FROM mini_game_challenges"
    filters = []
    values = []
    if game_type:
        filters.append("game_type = ?")
        values.append(game_type)
    if difficulty:
        filters.append("difficulty = ?")
        values.append(difficulty)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id"
    rows = connection.execute(query, values).fetchall()
    return [json.loads(row["data_json"]) for row in rows]
