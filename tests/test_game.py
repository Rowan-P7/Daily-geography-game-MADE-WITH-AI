import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from contextlib import closing

from geogame.app import create_app
from geogame.database import connect
from geogame.database import initialize_database
from geogame.minigames import (
    DIFFICULTIES,
    GAME_TYPES,
    get_challenge_bank,
    grade_challenge,
    make_daily_challenge,
    make_practice_challenge,
)
from geogame.question_bank import build_questions, daily_questions
from geogame.scoring import calculate_streak, score_answer


class QuestionBankTests(unittest.TestCase):
    def test_question_bank_is_large_and_well_formed(self):
        questions = build_questions()
        self.assertGreaterEqual(len(questions), 300)
        self.assertEqual(len({question["id"] for question in questions}), len(questions))
        for question in questions:
            if question["answer_type"] == "number":
                self.assertEqual(question["options"], [], question["id"])
                self.assertIn("tolerance", question)
            else:
                self.assertEqual(len(question["options"]), 4, question["id"])
                self.assertEqual(len(set(question["options"])), 4, question["id"])
                self.assertIn(question["correct_answer"], question["options"], question["id"])
            self.assertTrue(question["question"])
            self.assertTrue(question["explanation"])
        categories = {question["category"] for question in questions}
        self.assertTrue({
            "Flags", "Capital cities", "Currencies", "Country borders",
            "Population", "Languages", "Map reading", "Numerical estimation",
        } <= categories)

    def test_daily_set_is_stable_and_order_independent(self):
        questions = build_questions()
        first = daily_questions("2026-10-30", questions)
        second = daily_questions("2026-10-30", list(reversed(questions)))
        self.assertEqual([q["id"] for q in first], [q["id"] for q in second])
        self.assertEqual(len(first), 10)
        self.assertEqual(len({q["id"] for q in first}), 10)
        self.assertEqual(len({q["category"] for q in first}), 10)


class ScoringTests(unittest.TestCase):
    def test_correct_answer_points_and_speed_bonus(self):
        self.assertEqual(score_answer(True, 0), (1000, 250))
        self.assertEqual(score_answer(True, 30), (1000, 0))
        self.assertEqual(score_answer(False, 0), (0, 0))

    def test_streak_uses_consecutive_utc_calendar_dates(self):
        today = date(2026, 10, 30)
        dates = [(today - timedelta(days=offset)).isoformat() for offset in (0, 1, 2, 4)]
        self.assertEqual(calculate_streak(dates, today.isoformat()), (3, 3))
        self.assertEqual(calculate_streak(dates[1:], today.isoformat()), (2, 2))
        self.assertEqual(calculate_streak([], today.isoformat()), (0, 0))


class MiniGameTests(unittest.TestCase):
    def test_daily_challenge_is_stable_varied_and_difficulty_covered(self):
        bank = get_challenge_bank()
        first = make_daily_challenge("2026-10-30", challenge_bank=bank)
        second = make_daily_challenge("2026-10-30", challenge_bank=list(reversed(bank)))
        next_day = make_daily_challenge("2026-10-31", challenge_bank=bank)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertEqual(len(first), 7)
        self.assertEqual(len({item["game_type"] for item in first}), 7)
        self.assertNotEqual([item["id"] for item in first], [item["id"] for item in next_day])
        for game_type in (item["id"] for item in GAME_TYPES):
            for difficulty in DIFFICULTIES:
                self.assertTrue(
                    any(
                        item["game_type"] == game_type and item["difficulty"] == difficulty
                        for item in bank
                    ),
                    f"Missing {difficulty} content for {game_type}",
                )

    def test_scoring_rewards_closeness_and_exact_set_selection(self):
        bank = get_challenge_bank()
        estimate = next(item for item in bank if item["game_type"] == "closest_wins")
        exact = estimate["correct_answer"]["value"]
        self.assertGreater(
            grade_challenge(estimate, exact, 5)["points"],
            grade_challenge(estimate, exact * 1.5, 5)["points"],
        )
        flags = next(item for item in bank if item["game_type"] == "flag_connections")
        self.assertTrue(grade_challenge(flags, flags["correct_answer"], 5)["correct"])
        self.assertFalse(grade_challenge(flags, [], 5)["correct"])
        timed_out = grade_challenge(flags, flags["correct_answer"], flags["payload"]["timer_seconds"])
        self.assertFalse(timed_out["correct"])
        self.assertEqual(timed_out["points"], 0)
        comparison = next(item for item in bank if item["game_type"] == "higher_lower")
        self.assertEqual(
            grade_challenge(comparison, comparison["correct_answer"], 0)["points"],
            1100,
        )

    def test_existing_database_migrates_without_losing_game_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "legacy.sqlite3")
            connection = connect(path)
            connection.executescript(
                """
                CREATE TABLE questions (id TEXT PRIMARY KEY, category TEXT NOT NULL, difficulty TEXT NOT NULL, data_json TEXT NOT NULL);
                CREATE TABLE players (id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
                CREATE TABLE games (
                    id TEXT PRIMARY KEY,
                    player_id TEXT NOT NULL REFERENCES players(id),
                    mode TEXT NOT NULL CHECK (mode IN ('daily', 'practice')),
                    game_date TEXT,
                    status TEXT NOT NULL CHECK (status IN ('in_progress', 'complete')),
                    question_ids_json TEXT NOT NULL,
                    answers_json TEXT NOT NULL DEFAULT '[]',
                    score INTEGER NOT NULL DEFAULT 0,
                    started_at REAL NOT NULL,
                    question_started_at REAL NOT NULL,
                    completed_at REAL,
                    UNIQUE(player_id, mode, game_date)
                );
                INSERT INTO players VALUES ('player', '2026-10-29');
                INSERT INTO games VALUES (
                    'existing-game', 'player', 'daily', '2026-10-29', 'in_progress',
                    '[]', '[]', 450, 1, 1, NULL
                );
                """
            )
            connection.close()
            initialize_database(path)
            with closing(connect(path)) as migrated:
                row = migrated.execute(
                    "SELECT score, status, round_state_json, questions_json FROM games WHERE id = 'existing-game'"
                ).fetchone()
                self.assertEqual(row["score"], 450)
                self.assertEqual(row["status"], "in_progress")
                self.assertEqual(row["round_state_json"], "{}")
                self.assertIsNone(row["questions_json"])
                self.assertGreater(
                    migrated.execute("SELECT COUNT(*) FROM mini_game_challenges").fetchone()[0],
                    0,
                )


class GameApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "atlas.sqlite3")
        self.app = create_app({"TESTING": True, "DATABASE": self.database_path})
        self.client = self.app.test_client()

    def challenge_for_game(self, game):
        with closing(connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT questions_json FROM games WHERE id = ?", (game["id"],)
            ).fetchone()
        return json.loads(row["questions_json"])[game["question_index"]]

    @staticmethod
    def correct_answer(challenge):
        answer = challenge["correct_answer"]
        return answer["value"] if isinstance(answer, dict) else answer

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_users_receive_identical_daily_challenge(self):
        first = self.client.post("/api/games", json={"mode": "daily"})
        second = self.app.test_client().post("/api/games", json={"mode": "daily"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json["round"], second.json["round"])
        self.assertEqual(first.json["question_count"], 7)
        self.assertNotIn("correct_answer", first.json["round"]["payload"])
        with closing(connect(self.database_path)) as connection:
            snapshots = connection.execute(
                "SELECT questions_json FROM games WHERE mode = 'daily' ORDER BY player_id"
            ).fetchall()
        self.assertEqual(snapshots[0]["questions_json"], snapshots[1]["questions_json"])

    def test_homepage_renders_game_interface(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Play today", response.data)
        self.assertIn(b"Your stats", response.data)

    def test_daily_persists_completes_once_and_updates_statistics(self):
        with patch("geogame.app.utc_date", return_value="2026-10-30"):
            started = self.client.post("/api/games", json={"mode": "daily"})
            game = started.json
            for index in range(game["question_count"]):
                challenge = self.challenge_for_game(game)
                correct = self.correct_answer(challenge)
                response = self.client.post(
                    f"/api/games/{game['id']}/answer",
                    json={"question_index": index, "answer": correct},
                )
                self.assertEqual(response.status_code, 200, response.json)
                if index + 1 < game["question_count"]:
                    game["question_index"] = index + 1
            result = response.json["result"]
            self.assertEqual(result["correct"], 7)
            self.assertGreater(result["score"], 0)
            self.assertEqual(len(result["answers"]), 7)

            repeated = self.client.post("/api/games", json={"mode": "daily"})
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(repeated.json["status"], "complete")
            self.assertEqual(repeated.json["result"]["score"], result["score"])
            self.assertNotIn("round", repeated.json)

            stats = self.client.get("/api/stats").json
            self.assertEqual(stats["games_played"], 1)
            self.assertEqual(stats["best_score"], result["score"])
            self.assertEqual(stats["current_streak"], 1)
            self.assertEqual(stats["accuracy"], 100)
            self.assertTrue(stats["completed_today"])
            self.assertEqual(next(day for day in stats["calendar"] if day["date"] == "2026-10-30")["score"], result["score"])
            board = self.client.get("/api/leaderboard?date=2026-10-30").json
            self.assertEqual(board["entries"][0]["score"], result["score"])

    def test_practice_does_not_change_daily_statistics(self):
        game = self.client.post(
            "/api/games", json={"mode": "practice", "game_type": "closest_wins", "difficulty": "easy"}
        ).json
        challenge = self.challenge_for_game(game)
        correct = self.correct_answer(challenge)
        response = self.client.post(
            f"/api/games/{game['id']}/answer",
            json={"question_index": 0, "answer": correct},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json["result"]["date"])
        self.assertEqual(response.json["result"]["max_score"], 1100)
        self.assertEqual(self.client.get("/api/stats").json["games_played"], 0)

    def test_answer_validation_and_question_reports(self):
        invalid_mode = self.client.post("/api/games", json={"mode": []})
        self.assertEqual(invalid_mode.status_code, 400)
        game = self.client.post("/api/games", json={"mode": "daily"}).json
        invalid = self.client.post(
            f"/api/games/{game['id']}/answer",
            json={"question_index": 0, "answer": {}},
        )
        self.assertEqual(invalid.status_code, 400)
        report = self.client.post(
            "/api/reports",
            json={"question_id": game["round"]["id"], "message": "Please verify this fact."},
        )
        self.assertEqual(report.status_code, 201)
        invalid_report = self.client.post(
            "/api/reports", json={"question_id": "missing", "message": "This looks wrong."}
        )
        self.assertEqual(invalid_report.status_code, 404)

    def test_each_minigame_has_a_working_practice_round(self):
        for game_type in (item["id"] for item in GAME_TYPES):
            with self.subTest(game_type=game_type):
                challenge = next(item for item in get_challenge_bank() if item["game_type"] == game_type)
                game = self.client.post(
                    "/api/games",
                    json={"mode": "practice", "game_type": game_type, "difficulty": challenge["difficulty"]},
                ).json
                self.assertEqual(game["round"]["game_type"], game_type)
                saved = self.challenge_for_game(game)
                if game_type == "country_outline":
                    payload = game["round"]["payload"]
                    self.assertNotIn("geo_name", payload)
                    self.assertNotIn("country", payload)
                    self.assertTrue(payload["outline_geometry"]["coordinates"])
                if game_type == "where_in_world":
                    payload = game["round"]["payload"]
                    self.assertNotIn("photo_source", payload)
                    self.assertNotIn("landmark", payload)
                    self.assertTrue((Path(__file__).parent.parent / payload["photo_url"].lstrip("/")).is_file())
                if game_type == "border_battle":
                    map_response = self.client.get(f"/api/games/{game['id']}/map")
                    self.assertEqual(map_response.status_code, 200)
                    self.assertGreater(len(map_response.json["features"]), 100)
                    self.assertEqual(
                        self.client.get("/static/data/countries.geojson").status_code,
                        404,
                    )
                answer = self.client.post(
                    f"/api/games/{game['id']}/answer",
                    json={"question_index": 0, "answer": self.correct_answer(saved)},
                )
                self.assertEqual(answer.status_code, 200, answer.json)
                self.assertTrue(answer.json["feedback"]["is_correct"])

    def test_mystery_wrong_guess_reveals_clue_without_disclosing_answer(self):
        game = self.client.post(
            "/api/games",
            json={"mode": "practice", "game_type": "mystery_country", "difficulty": "easy"},
        ).json
        challenge = self.challenge_for_game(game)
        wrong = self.client.post(
            f"/api/games/{game['id']}/answer",
            json={"question_index": 0, "answer": "not the country"},
        )
        self.assertEqual(wrong.status_code, 200)
        self.assertNotIn("correct_answer", wrong.json["feedback"])
        self.assertEqual(wrong.json["round"]["revealed_hints"], 2)
        correct = self.client.post(
            f"/api/games/{game['id']}/answer",
            json={"question_index": 0, "answer": challenge["correct_answer"]},
        )
        self.assertTrue(correct.json["feedback"]["is_correct"])

    def test_practice_answer_validation_rejects_out_of_range_values(self):
        game = self.client.post(
            "/api/games",
            json={"mode": "practice", "game_type": "closest_wins", "difficulty": "easy"},
        ).json
        invalid = self.client.post(
            f"/api/games/{game['id']}/answer",
            json={"question_index": 0, "answer": -1},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_daily_challenge_resets_on_utc_date_change(self):
        with patch("geogame.app.utc_date", return_value="2026-10-30"):
            first = self.client.post("/api/games", json={"mode": "daily"}).json
        with patch("geogame.app.utc_date", return_value="2026-10-31"):
            second = self.client.post("/api/games", json={"mode": "daily"}).json
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(second["date"], "2026-10-31")

    def test_database_seeds_more_than_three_hundred_questions(self):
        with closing(connect(self.database_path)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        self.assertGreaterEqual(count, 300)


if __name__ == "__main__":
    unittest.main()
