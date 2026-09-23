from flask import Flask, render_template, request, jsonify
import sqlite3
import time
import csv

from questions import questions

app = Flask(__name__)

DATABASE = "quiz.db"

quiz_state = {
    "started": False,
    "current_question": 1,
    "question_start": 0,
    "duration": 20
}


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT UNIQUE NOT NULL,
            team_code TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            correct INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def import_teams_from_csv():

    conn = get_db()

    with open("teams.csv", "r", encoding="utf-8-sig") as file:

        reader = csv.DictReader(file)

        for row in reader:

            team_name = row["Team name"].strip()
            team_code = row["Team Code"].strip()

            if not team_name or not team_code:
                continue

            try:
                conn.execute(
                    """
                    INSERT INTO teams (team_name, team_code)
                    VALUES (?, ?)
                    """,
                    (team_name, team_code)
                )

            except sqlite3.IntegrityError:
                # Team already exists — don't duplicate it
                pass

    conn.commit()
    conn.close()


@app.route("/")
def team_page():
    return render_template("team.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid request."
        })

    team_name = data.get("team_name", "").strip()
    team_code = data.get("team_code", "").strip().upper()

    if not team_name:
        return jsonify({
            "success": False,
            "message": "Please enter your team name."
        })

    if not team_code:
        return jsonify({
            "success": False,
            "message": "Please enter your team code."
        })

    conn = get_db()

    # Check whether team name exists
    team = conn.execute(
        """
        SELECT id, team_name, team_code
        FROM teams
        WHERE LOWER(team_name) = LOWER(?)
        """,
        (team_name,)
    ).fetchone()

    if not team:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Invalid team name."
        })

    # Check whether the code matches that team
    if team["team_code"].upper() != team_code:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Invalid team code."
        })

    conn.close()

    return jsonify({
        "success": True,
        "team_id": team["id"],
        "team_name": team["team_name"]
    })


@app.route("/state")
def state():

    remaining = 0

    if quiz_state["started"]:

        elapsed = (
            time.time()
            - quiz_state["question_start"]
        )

        remaining = max(
            0,
            quiz_state["duration"]
            - int(elapsed)
        )

    return jsonify({
        "started": quiz_state["started"],
        "current_question": quiz_state["current_question"],
        "remaining": remaining
    })


@app.route("/admin/start", methods=["POST"])
def start_quiz():

    quiz_state["started"] = True
    quiz_state["current_question"] = 1
    quiz_state["question_start"] = time.time()

    return jsonify({
        "success": True
    })


@app.route("/admin/next", methods=["POST"])
def next_question():

    if quiz_state["current_question"] < len(questions):

        quiz_state["current_question"] += 1
        quiz_state["question_start"] = time.time()

        return jsonify({
            "success": True,
            "question": quiz_state["current_question"]
        })

    quiz_state["started"] = False

    return jsonify({
        "success": True,
        "finished": True
    })


@app.route("/admin/clear", methods=["POST"])
def clear_data():

    conn = get_db()

    conn.execute("DELETE FROM answers")
    conn.execute("DELETE FROM teams")

    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name='teams'"
    )

    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name='answers'"
    )

    conn.commit()
    conn.close()

    quiz_state["started"] = False
    quiz_state["current_question"] = 1
    quiz_state["question_start"] = 0

    return jsonify({
        "success": True,
        "message": "All quiz data cleared."
    })


@app.route("/question/<int:question_id>")
def get_question(question_id):

    question = next(
        (
            q for q in questions
            if q["id"] == question_id
        ),
        None
    )

    if not question:

        return jsonify({
            "success": False,
            "message": "Question not found."
        }), 404

    return jsonify({
        "success": True,
        "question": question
    })


@app.route("/answer", methods=["POST"])
def submit_answer():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid request."
        })

    team_id = data.get("team_id")
    question_id = data.get("question_id")
    answer = data.get("answer")

    if not team_id or not question_id or not answer:

        return jsonify({
            "success": False,
            "message": "Missing answer information."
        })

    if not quiz_state["started"]:

        return jsonify({
            "success": False,
            "message": "Quiz has not started."
        })

    if question_id != quiz_state["current_question"]:

        return jsonify({
            "success": False,
            "message": "This question is no longer active."
        })

    elapsed = (
        time.time()
        - quiz_state["question_start"]
    )

    if elapsed > quiz_state["duration"]:

        return jsonify({
            "success": False,
            "message": "Time is up."
        })

    question = next(
        (
            q for q in questions
            if q["id"] == question_id
        ),
        None
    )

    if not question:

        return jsonify({
            "success": False,
            "message": "Invalid question."
        })

    conn = get_db()

    # Make sure the team exists
    team = conn.execute(
        "SELECT id FROM teams WHERE id = ?",
        (team_id,)
    ).fetchone()

    if not team:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Team not found."
        })

    already_answered = conn.execute(
        """
        SELECT id
        FROM answers
        WHERE team_id = ?
        AND question_id = ?
        """,
        (team_id, question_id)
    ).fetchone()

    if already_answered:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Already answered."
        })

    correct = answer == question["answer"]

    points = 10 if correct else 0

    conn.execute(
        """
        INSERT INTO answers
        (team_id, question_id, answer, correct)
        VALUES (?, ?, ?, ?)
        """,
        (
            team_id,
            question_id,
            answer,
            int(correct)
        )
    )

    conn.execute(
        """
        UPDATE teams
        SET score = score + ?
        WHERE id = ?
        """,
        (points, team_id)
    )

    conn.commit()

    team = conn.execute(
        """
        SELECT score
        FROM teams
        WHERE id = ?
        """,
        (team_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "correct": correct,
        "points": points,
        "score": team["score"]
    })


@app.route("/teams")
def teams():

    conn = get_db()

    results = conn.execute(
        """
        SELECT
            id,
            team_name,
            score
        FROM teams
        ORDER BY score DESC, id ASC
        """
    ).fetchall()

    conn.close()

    return jsonify([
        {
            "id": team["id"],
            "team_name": team["team_name"],
            "score": team["score"]
        }
        for team in results
    ])


if __name__ == "__main__":

    init_db()
    import_teams_from_csv()

    print("\n===================================")
    print("       TECHTONIC OFFLINE QUIZ")
    print("===================================")
    print("Team:  http://127.0.0.1:5000")
    print("Admin: http://127.0.0.1:5000/admin")
    print("===================================\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )