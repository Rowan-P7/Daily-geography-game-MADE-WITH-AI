from datetime import date, timedelta


BASE_POINTS = 1000
MAX_SPEED_BONUS = 250
SPEED_WINDOW_SECONDS = 30


def score_answer(is_correct, elapsed_seconds):
    if not is_correct:
        return 0, 0
    bonus = max(0, round(MAX_SPEED_BONUS * (1 - max(0, elapsed_seconds) / SPEED_WINDOW_SECONDS)))
    return BASE_POINTS, bonus


def calculate_streak(completed_dates, today):
    dates = set(completed_dates)
    current = 0
    cursor_date = date.fromisoformat(today)
    if cursor_date.isoformat() not in dates:
        cursor_date -= timedelta(days=1)

    while cursor_date.isoformat() in dates:
        current += 1
        cursor_date -= timedelta(days=1)

    longest = 0
    run = 0
    previous = None
    for completed_date in sorted(dates):
        parsed = date.fromisoformat(completed_date)
        if previous is not None and parsed == previous + timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        previous = parsed
    return current, longest
