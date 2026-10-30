import json
import re
import secrets
import sqlite3
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

from geogame.database import connect, get_question, initialize_database, load_challenge_bank
from geogame.minigames import (
    DIFFICULTIES,
    GAME_TYPES,
    grade_challenge,
    make_daily_challenge,
    make_practice_challenge,
    public_challenge,
)
from geogame.question_bank import public_question
from geogame.scoring import calculate_streak, score_answer


COOKIE_NAME = "atlas_player"
PLAYER_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def utc_now():
    return datetime.now(timezone.utc)


def utc_date():
    return utc_now().date().isoformat()


@lru_cache(maxsize=1)
def natural_earth_features():
    data_path = Path(__file__).resolve().parent / "data" / "countries.geojson"
    with data_path.open(encoding="utf-8") as file:
        return json.load(file)["features"]


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        root_path=str(project_root),
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "atlas.sqlite3"),
        SECRET_KEY=secrets.token_hex(32),
        COOKIE_SECURE=False,
    )
    if test_config:
        app.config.update(test_config)
    initialize_database(app.config["DATABASE"])

    @app.before_request
    def prepare_request():
        cookie_id = request.cookies.get(COOKIE_NAME, "")
        g.player_id = cookie_id if PLAYER_ID_PATTERN.fullmatch(cookie_id) else uuid.uuid4().hex
        g.db = connect(app.config["DATABASE"])
        g.db.execute(
            "INSERT OR IGNORE INTO players (id, created_at) VALUES (?, ?)",
            (g.player_id, utc_now().isoformat()),
        )
        g.db.commit()

    @app.teardown_request
    def close_database(_error=None):
        database = g.pop("db", None)
        if database is not None:
            database.close()

    @app.after_request
    def persist_player_cookie(response):
        response.set_cookie(
            COOKIE_NAME,
            g.player_id,
            max_age=60 * 60 * 24 * 365 * 10,
            httponly=True,
            secure=app.config["COOKIE_SECURE"],
            samesite="Lax",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    def json_body():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return None
        return body

    def game_by_id(game_id):
        return g.db.execute(
            "SELECT * FROM games WHERE id = ? AND player_id = ?", (game_id, g.player_id)
        ).fetchone()

    def questions_for_game(game):
        stored_questions = game["questions_json"]
        if stored_questions:
            return json.loads(stored_questions)
        return [
            get_question(g.db, question_id)
            for question_id in json.loads(game["question_ids_json"])
        ]

    def public_round(challenge, round_state=None):
        round_state = round_state or {}
        revealed_hints = round_state.get(
            "revealed_hints", 1 if challenge["game_type"] == "mystery_country" else 0
        )
        public = public_challenge(
            challenge, revealed_hints, round_state.get("attempts", 0)
        )
        if challenge["game_type"] == "country_outline":
            geo_name = challenge["payload"]["geo_name"]
            feature = next(
                (item for item in natural_earth_features() if item["properties"]["ADMIN"] == geo_name),
                None,
            )
            if feature is None:
                raise LookupError(f"Natural Earth outline not found for {geo_name}")
            public["payload"]["outline_geometry"] = feature["geometry"]
        return public

    def current_game_payload(game):
        questions = questions_for_game(game)
        answers = json.loads(game["answers_json"])
        index = len(answers)
        is_mini_game = bool(questions and "game_type" in questions[0])
        payload = {
            "id": game["id"],
            "mode": game["mode"],
            "date": game["game_date"],
            "status": game["status"],
            "question_index": index,
            "question_count": len(questions),
            "score": game["score"],
        }
        if game["status"] == "complete":
            payload["result"] = result_for(game)
        elif is_mini_game:
            round_state = json.loads(game["round_state_json"] or "{}").get(str(index), {})
            payload["round"] = public_round(questions[index], round_state)
        else:
            payload["question"] = public_question(questions[index])
        return payload

    def result_for(game):
        answers = json.loads(game["answers_json"])
        question_ids = json.loads(game["question_ids_json"])
        elapsed = round(sum(answer["elapsed_seconds"] for answer in answers))
        correct = sum(answer.get("is_correct", answer.get("correct", False)) for answer in answers)
        mini_game_rounds = bool(answers and "game_type" in answers[0])
        return {
            "score": game["score"],
            "correct": correct,
            "total": len(question_ids),
            "accuracy": round(correct / len(question_ids) * 100) if question_ids else 0,
            "time_seconds": elapsed,
            "answers": answers,
            "date": game["game_date"],
            "streak": get_stats(g.player_id)["current_streak"] if game["mode"] == "daily" else None,
            "game_types": [answer.get("game_type") for answer in answers],
            "max_score": (
                len(question_ids) * 1100
                + sum(min(100, index * 50) for index in range(len(question_ids)))
                if mini_game_rounds
                else len(question_ids) * 1250
            ),
        }

    def get_stats(player_id):
        rows = g.db.execute(
            "SELECT game_date, score, answers_json, question_ids_json FROM games "
            "WHERE player_id = ? AND mode = 'daily' AND status = 'complete' ORDER BY game_date",
            (player_id,),
        ).fetchall()
        completed_dates = [row["game_date"] for row in rows]
        today = utc_date()
        current_streak, longest_streak = calculate_streak(completed_dates, today)
        total_games = len(rows)
        total_score = sum(row["score"] for row in rows)
        total_answers = sum(len(json.loads(row["answers_json"])) for row in rows)
        correct_answers = sum(
            sum(answer["is_correct"] for answer in json.loads(row["answers_json"])) for row in rows
        )
        calendar = set(completed_dates)
        scores_by_date = {row["game_date"]: row["score"] for row in rows}
        current_date = datetime.fromisoformat(today).date()
        return {
            "games_played": total_games,
            "average_score": round(total_score / total_games) if total_games else 0,
            "best_score": max((row["score"] for row in rows), default=0),
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "accuracy": round(correct_answers / total_answers * 100) if total_answers else 0,
            "completed_today": today in calendar,
            "calendar": [
                {
                    "date": (current_date - timedelta(days=offset)).isoformat(),
                    "completed": (current_date - timedelta(days=offset)).isoformat() in calendar,
                    "score": scores_by_date.get((current_date - timedelta(days=offset)).isoformat()),
                }
                for offset in range(34, -1, -1)
            ]
        }

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/daily")
    def daily_overview():
        today = utc_date()
        existing = g.db.execute(
            "SELECT * FROM games WHERE player_id = ? AND mode = 'daily' AND game_date = ?",
            (g.player_id, today),
        ).fetchone()
        stats = get_stats(g.player_id)
        tomorrow = date.fromisoformat(today) + timedelta(days=1)
        seconds_until_midnight = int(
            (datetime.combine(tomorrow, datetime.min.time(), timezone.utc) - utc_now()).total_seconds()
        )
        return jsonify({
            "date": today,
            "stats": stats,
            "completed": bool(existing and existing["status"] == "complete"),
            "in_progress": bool(existing and existing["status"] == "in_progress"),
            "seconds_until_reset": max(seconds_until_midnight, 0),
        })

    @app.get("/api/stats")
    def stats():
        return jsonify(get_stats(g.player_id))

    @app.get("/api/minigames")
    def minigames():
        return jsonify({"games": list(GAME_TYPES), "difficulties": list(DIFFICULTIES)})

    @app.get("/api/leaderboard")
    def leaderboard():
        target_date = request.args.get("date", utc_date())
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            return jsonify(error="Use a valid YYYY-MM-DD date."), 400
        if parsed_date.isoformat() != target_date:
            return jsonify(error="Use a valid YYYY-MM-DD date."), 400
        rows = g.db.execute(
            "SELECT player_id, score, answers_json FROM games "
            "WHERE mode = 'daily' AND game_date = ? AND status = 'complete' "
            "ORDER BY score DESC, completed_at ASC LIMIT 10",
            (target_date,),
        ).fetchall()
        return jsonify({
            "date": target_date,
            "entries": [
                {
                    "rank": rank,
                    "name": f"Explorer {row['player_id'][:4].upper()}",
                    "score": row["score"],
                    "correct": sum(a["is_correct"] for a in json.loads(row["answers_json"])),
                    "total": len(json.loads(row["answers_json"])),
                }
                for rank, row in enumerate(rows, 1)
            ],
        })

    @app.post("/api/games")
    def start_game():
        body = json_body()
        if body is None or not isinstance(body.get("mode"), str) or body["mode"] not in {"daily", "practice"}:
            return jsonify(error="Choose either daily or practice mode."), 400
        mode = body["mode"]
        if mode == "practice":
            game_type = body.get("game_type")
            difficulty = body.get("difficulty", "medium")
            if game_type is not None and (
                not isinstance(game_type, str)
                or game_type not in {item["id"] for item in GAME_TYPES}
            ):
                return jsonify(error="Choose a supported mini-game."), 400
            if not isinstance(difficulty, str) or difficulty not in DIFFICULTIES:
                return jsonify(error="Choose a supported difficulty."), 400
            try:
                selection = [make_practice_challenge(
                    game_type, difficulty, challenge_bank=load_challenge_bank(g.db)
                )]
            except ValueError as error:
                return jsonify(error=str(error)), 400
            return create_game(mode, selection, None)
        today = utc_date()
        if mode == "daily":
            existing = g.db.execute(
                "SELECT * FROM games WHERE player_id = ? AND mode = 'daily' AND game_date = ?",
                (g.player_id, today),
            ).fetchone()
            if existing:
                return jsonify(current_game_payload(existing))
        challenge = g.db.execute(
            "SELECT questions_json FROM daily_challenges WHERE game_date = ?", (today,)
        ).fetchone()
        if challenge:
            stored_selection = json.loads(challenge["questions_json"])
            if stored_selection and "game_type" not in stored_selection[0]:
                existing_games = g.db.execute(
                    "SELECT 1 FROM games WHERE mode = 'daily' AND game_date = ? LIMIT 1", (today,)
                ).fetchone()
                if existing_games:
                    return create_game(mode, stored_selection, today)
                challenge = None
        if challenge is None:
            previous = g.db.execute(
                "SELECT questions_json FROM daily_challenges WHERE game_date < ? "
                "ORDER BY game_date DESC LIMIT 10",
                (today,),
            ).fetchall()
            used_ids = {
                round_data["id"]
                for row in previous
                for round_data in json.loads(row["questions_json"])
                if isinstance(round_data, dict) and "game_type" in round_data
            }
            selection = make_daily_challenge(
                today, used_ids, challenge_bank=load_challenge_bank(g.db)
            )
            g.db.execute(
                "INSERT INTO daily_challenges (game_date, questions_json) VALUES (?, ?) "
                "ON CONFLICT(game_date) DO UPDATE SET questions_json = excluded.questions_json",
                (today, json.dumps(selection, ensure_ascii=False)),
            )
            g.db.commit()
        else:
            selection = stored_selection
        return create_game(mode, selection, today)

    def create_game(mode, selection, game_date):
        game_id = uuid.uuid4().hex
        now = time.time()
        try:
            g.db.execute(
                "INSERT INTO games (id, player_id, mode, game_date, status, question_ids_json, "
                "questions_json, answers_json, started_at, question_started_at) "
                "VALUES (?, ?, ?, ?, 'in_progress', ?, ?, '[]', ?, ?)",
                (
                    game_id, g.player_id, mode, game_date,
                    json.dumps([question["id"] for question in selection]),
                    json.dumps(selection, ensure_ascii=False), now, now,
                ),
            )
            g.db.commit()
        except sqlite3.IntegrityError:
            if mode != "daily":
                raise
            existing = g.db.execute(
                "SELECT * FROM games WHERE player_id = ? AND mode = 'daily' AND game_date = ?",
                (g.player_id, game_date),
            ).fetchone()
            return jsonify(current_game_payload(existing))
        return jsonify(current_game_payload(game_by_id(game_id))), 201

    @app.get("/api/games/<game_id>")
    def resume_game(game_id):
        game = game_by_id(game_id)
        if game is None:
            return jsonify(error="Game not found."), 404
        return jsonify(current_game_payload(game))

    @app.get("/api/games/<game_id>/map")
    def game_map(game_id):
        game = game_by_id(game_id)
        if game is None:
            return jsonify(error="Game not found."), 404
        questions = questions_for_game(game)
        index = len(json.loads(game["answers_json"]))
        if index >= len(questions) or questions[index]["game_type"] != "border_battle":
            return jsonify(error="This round does not include an interactive map."), 400
        return jsonify({"type": "FeatureCollection", "features": natural_earth_features()})

    @app.post("/api/games/<game_id>/answer")
    def answer_game(game_id):
        g.db.execute("BEGIN IMMEDIATE")
        game = game_by_id(game_id)
        if game is None:
            return jsonify(error="Game not found."), 404
        if game["status"] != "in_progress":
            return jsonify(error="This game is already complete."), 409
        body = json_body()
        answers = json.loads(game["answers_json"])
        game_questions = questions_for_game(game)
        question_ids = json.loads(game["question_ids_json"])
        if (
            body is None
            or type(body.get("question_index")) is not int
            or body["question_index"] != len(answers)
            or "answer" not in body
        ):
            return jsonify(error="Submit an answer for the current question."), 400
        if game_questions and "game_type" in game_questions[0]:
            challenge = game_questions[len(answers)]
            round_states = json.loads(game["round_state_json"] or "{}")
            round_state = round_states.get(str(len(answers)), {})
            submitted_answer = body["answer"]
            game_type = challenge["game_type"]
            if game_type in {"flag_connections", "border_battle"}:
                options = challenge["payload"].get(
                    "flags", challenge["payload"].get("countries", [])
                )
                allowed = {item["name"] for item in options} if options and isinstance(options[0], dict) else set(options)
                if (
                    not isinstance(submitted_answer, list)
                    or len(submitted_answer) > len(allowed)
                    or any(not isinstance(item, str) or item not in allowed for item in submitted_answer)
                    or len(set(submitted_answer)) != len(submitted_answer)
                ):
                    return jsonify(error="Choose only the countries shown in this round."), 400
            elif game_type == "closest_wins":
                if (
                    isinstance(submitted_answer, bool)
                    or not isinstance(submitted_answer, (int, float))
                    or not challenge["payload"]["min_value"] <= submitted_answer <= challenge["payload"]["max_value"]
                ):
                    return jsonify(error="Enter a number within the displayed range."), 400
            elif not isinstance(submitted_answer, str) or not submitted_answer.strip() or len(submitted_answer) > 160:
                return jsonify(error="Enter a valid answer of 160 characters or fewer."), 400
            attempts = round_state.get("attempts", 0)
            revealed_hints = round_state.get(
                "revealed_hints", 1 if challenge["game_type"] == "mystery_country" else 0
            )
            elapsed = max(0, time.time() - game["question_started_at"])
            graded = grade_challenge(challenge, submitted_answer, elapsed, revealed_hints)
            if challenge["game_type"] == "mystery_country":
                attempts += 1
                round_state["attempts"] = attempts
                if not graded["correct"] and attempts < 5:
                    graded.pop("correct_answer", None)
                    graded.pop("correct_answer_display", None)
                    round_state["revealed_hints"] = min(
                        len(challenge["payload"]["clues"]), revealed_hints + 1
                    )
                    round_states[str(len(answers))] = round_state
                    g.db.execute(
                        "UPDATE games SET round_state_json = ? WHERE id = ?",
                        (json.dumps(round_states), game_id),
                    )
                    g.db.commit()
                    return jsonify({
                        "round_complete": False,
                        "feedback": graded,
                        "score": game["score"],
                        "round": public_round(challenge, round_state),
                        "attempts": attempts,
                    })
                if not graded["correct"]:
                    graded["round_failed"] = True
                    graded["correct_answer_display"] = challenge["correct_answer"]
            graded["question"] = challenge["prompt"]
            graded["game_type"] = challenge["game_type"]
            graded["difficulty"] = challenge["difficulty"]
            graded["answer"] = submitted_answer
            if challenge["game_type"] == "where_in_world":
                graded["photo_source"] = challenge["payload"]["photo_source"]
                graded["photo_credit"] = challenge["payload"]["photo_credit"]
            graded["is_correct"] = graded["correct"]
            combo = 1
            for previous in reversed(answers):
                if not previous.get("is_correct", False):
                    break
                combo += 1
            graded["combo_bonus"] = min(100, max(0, combo - 1) * 50) if graded["correct"] else 0
            graded["points"] += graded["combo_bonus"]
            answers.append(graded)
            new_score = game["score"] + graded["points"]
            complete = len(answers) == len(question_ids)
            now = time.time()
            g.db.execute(
                "UPDATE games SET answers_json = ?, score = ?, round_state_json = '{}', "
                "question_started_at = ?, status = ?, completed_at = ? WHERE id = ? AND player_id = ?",
                (
                    json.dumps(answers, ensure_ascii=False), new_score, now,
                    "complete" if complete else "in_progress",
                    utc_now().isoformat() if complete else None, game_id, g.player_id,
                ),
            )
            g.db.commit()
            refreshed = game_by_id(game_id)
            response = {
                "feedback": graded,
                "question_index": len(answers),
                "question_count": len(question_ids),
                "score": new_score,
                "complete": complete,
                "round_complete": True,
            }
            if complete:
                response["result"] = result_for(refreshed)
            else:
                response["round"] = public_round(game_questions[len(answers)])
            return jsonify(response)

        question = game_questions[len(answers)]
        if question.get("answer_type") == "number":
            submitted = body["answer"]
            if (
                isinstance(submitted, bool)
                or not isinstance(submitted, (int, float))
            ):
                return jsonify(error="Enter a valid numerical estimate."), 400
            if not question["min_value"] <= submitted <= question["max_value"]:
                return jsonify(error="Keep your estimate within the displayed range."), 400
            answer_value = float(submitted)
            is_correct = abs(answer_value - question["correct_answer"]) <= question["tolerance"]
            answer_display = f"{answer_value:,.0f} {question['unit']}"
            correct_answer_display = question["correct_answer_display"]
        else:
            if not isinstance(body["answer"], str) or body["answer"] not in question["options"]:
                return jsonify(error="Select one of the available answers."), 400
            answer_value = body["answer"]
            is_correct = answer_value == question["correct_answer"]
            answer_display = answer_value
            correct_answer_display = question.get("correct_answer_display", str(question["correct_answer"]))
        elapsed = max(0, time.time() - game["question_started_at"])
        base, speed_bonus = score_answer(is_correct, elapsed)
        scored = {
            "question_id": question["id"],
            "question": question["question"],
            "category": question["category"],
            "answer": answer_value,
            "answer_display": answer_display,
            "correct_answer": question["correct_answer"],
            "correct_answer_display": correct_answer_display,
            "is_correct": is_correct,
            "points": base + speed_bonus,
            "base_points": base,
            "speed_bonus": speed_bonus,
            "elapsed_seconds": round(elapsed, 2),
            "explanation": question["explanation"],
        }
        answers.append(scored)
        new_score = game["score"] + scored["points"]
        complete = len(answers) == len(question_ids)
        now = time.time()
        g.db.execute(
            "UPDATE games SET answers_json = ?, score = ?, question_started_at = ?, "
            "status = ?, completed_at = ? WHERE id = ? AND player_id = ?",
            (
                json.dumps(answers, ensure_ascii=False), new_score, now,
                "complete" if complete else "in_progress",
                utc_now().isoformat() if complete else None, game_id, g.player_id,
            ),
        )
        g.db.commit()
        refreshed = game_by_id(game_id)
        response = {
            "feedback": scored,
            "question_index": len(answers),
            "question_count": len(question_ids),
            "score": new_score,
            "complete": complete,
        }
        if complete:
            response["result"] = result_for(refreshed)
        else:
            response["question"] = public_question(game_questions[len(answers)])
        return jsonify(response)

    @app.post("/api/games/<game_id>/hint")
    def reveal_hint(game_id):
        game = game_by_id(game_id)
        if game is None:
            return jsonify(error="Game not found."), 404
        if game["status"] != "in_progress":
            return jsonify(error="This game is already complete."), 409
        questions = questions_for_game(game)
        answers = json.loads(game["answers_json"])
        if not questions or "game_type" not in questions[0]:
            return jsonify(error="This game does not use revealable hints."), 400
        challenge = questions[len(answers)]
        if challenge["game_type"] not in {"mystery_country", "where_in_world"}:
            return jsonify(error="This mini-game does not have hints."), 400
        states = json.loads(game["round_state_json"] or "{}")
        key = str(len(answers))
        current = states.get(key, {})
        current_hints = current.get(
            "revealed_hints", 1 if challenge["game_type"] == "mystery_country" else 0
        )
        max_hints = len(challenge["payload"]["clues"]) if challenge["game_type"] == "mystery_country" else len(challenge["payload"]["hints"])
        current["revealed_hints"] = min(max_hints, current_hints + 1)
        states[key] = current
        g.db.execute(
            "UPDATE games SET round_state_json = ? WHERE id = ?",
            (json.dumps(states), game["id"]),
        )
        g.db.commit()
        return jsonify({
            "round": public_round(challenge, current),
            "hints_remaining": max(0, max_hints - current["revealed_hints"]),
        })

    @app.post("/api/reports")
    def report_question():
        body = json_body()
        if (
            body is None
            or not isinstance(body.get("question_id"), str)
            or not isinstance(body.get("message"), str)
            or not 5 <= len(body["message"].strip()) <= 500
        ):
            return jsonify(error="Include a question ID and a report between 5 and 500 characters."), 400
        is_mini_game = g.db.execute(
            "SELECT 1 FROM mini_game_challenges WHERE id = ?", (body["question_id"],)
        ).fetchone()
        if is_mini_game:
            g.db.execute(
                "INSERT INTO mini_game_reports (player_id, challenge_id, message, created_at) "
                "VALUES (?, ?, ?, ?)",
                (g.player_id, body["question_id"], body["message"].strip(), utc_now().isoformat()),
            )
            g.db.commit()
            return jsonify(message="Thanks — your mini-game report has been recorded."), 201
        if g.db.execute("SELECT 1 FROM questions WHERE id = ?", (body["question_id"],)).fetchone() is None:
            return jsonify(error="Question not found."), 404
        g.db.execute(
            "INSERT INTO question_reports (player_id, question_id, message, created_at) VALUES (?, ?, ?, ?)",
            (g.player_id, body["question_id"], body["message"].strip(), utc_now().isoformat()),
        )
        g.db.commit()
        return jsonify(message="Thanks — your report has been recorded."), 201

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unhandled server error")
        return jsonify(error="Something went wrong. Please try again."), 500

    return app
