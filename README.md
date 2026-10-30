# Atlas

Atlas is a responsive daily geography puzzle game. Each UTC day, every player
gets the same seven-round challenge, assembled from a rotating set of eight
mini-games: Mystery Country, Higher or Lower, Country Outline, Closest Wins,
Flag Connections, Where in the World, Border Battle, and Geography
Connections. Daily rounds vary in country, mechanic, and difficulty. Practice
lets players select an individual game and difficulty without changing daily
statistics or streaks.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open http://127.0.0.1:5000. The SQLite database is created at
`instance/atlas.sqlite3` on first launch. A long-lived, HTTP-only browser cookie
identifies each anonymous player; clearing that cookie starts a new player.
Set `COOKIE_SECURE=True` in the Flask app configuration when serving over HTTPS.

Run the automated checks with:

```powershell
python -m unittest discover -v
```

## Project layout

- `main.py` starts the Flask application.
- `geogame/app.py` contains page and JSON API routes, daily persistence, and
  anonymous player statistics.
- `geogame/database.py` creates and migrates the SQLite schema, seeds the
  question bank, and stores mini-game challenge records and reports.
- `geogame/minigames.py` defines challenge content, deterministic daily
  rotation, answer validation, and scoring for all eight mechanics.
- `geogame/question_bank.py` maintains the original multiple-choice question
  bank for existing records and future use.
- `geogame/scoring.py` owns legacy scoring and UTC-calendar streak logic.
- `geogame/data/countries.geojson` contains Natural Earth 1:50m country
  boundaries, served through game-scoped API responses rather than as a public
  static file.
- `static/photos/` contains the locally served, attributed landmark images.
- `templates/index.html` and `static/` provide the responsive interface.
- `tests/test_game.py` covers the question bank, challenge rotation, scoring,
  all mini-game APIs, streaks, persistence, and practice isolation.

## Gameplay and persistence

The initial question bank contains more than 500 questions across capitals,
country identification, flags, currencies, continents, languages, population,
borders, landmarks, physical geography, and world records. The mini-game
registry stores structured challenge data, difficulty, accepted answers,
explanations, source references, and scoring rules in SQLite. Add or edit
challenge templates in `geogame/minigames.py`; the registry is upserted when
the application starts.

Daily challenge selection is generated from a SHA-256 seed based on the UTC
date, then saved as an immutable snapshot shared by all players. Each daily
sequence includes seven distinct mini-game types; the omitted type rotates by
date. Recently used content is avoided when alternatives are available.
Answer keys and unrevealed clues stay on the server. In-progress rounds,
mistakes, revealed hints, and completed results survive refreshes. Daily
attempts cannot be replayed after completion, while practice games do not
change daily statistics.

Mini-game rounds are worth up to 1,000 base points, with up to 100 speed
points where appropriate, partial credit for selection games and estimates,
and combo bonuses for consecutive correct rounds. Combo bonuses build to 100
points; a perfect seven-round run can earn up to 8,250 points. Streaks use
completed UTC calendar dates, not session counts. The anonymous
installation-wide daily leaderboard can later be replaced with authenticated
accounts without changing the saved game model.

## Geographic data and image credits

Country boundaries and outlines use [Natural Earth 1:50m Admin 0
countries](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries/),
a public-domain dataset. Population and GDP comparisons cite World Bank
indicators and reference years in the challenge data. Other curated values
include their source notes and explanations; geographic measurements can vary
by source and method.

Landmark photos are served from local files so the game does not depend on
remote image availability. Their source links and license details are shown
after a round is answered:

| Landmark | Creator | License |
|---|---|---|
| Machu Picchu | Pedro Szekely | CC BY-SA 2.0 |
| Eiffel Tower | Kate | CC BY-SA 3.0 |
| Taj Mahal | Yann | CC BY-SA 4.0 |
| Petra | Charlie Phillips | CC BY 2.0 |
| Sydney Opera House | Diliff | CC BY-SA 3.0 |
| Mount Kilimanjaro | Muhammad Mahdi Karim | GFDL 1.2 |
| Golden Gate Bridge | Frank Schulenburg | CC BY-SA 4.0 |
| Christ the Redeemer | Nico Kaiser | CC BY 2.0 |
| Angkor Wat | Björn Christian Tørrissen | CC BY-SA 4.0 |
| Acropolis of Athens | Jebulon | CC0 |
| Mount Fuji | Subramaniam K V | CC BY 3.0 |
| Pyramids of Giza | Ricardo Liberato | CC BY-SA 2.0 |

Individual file-page links are included with the corresponding challenge.
