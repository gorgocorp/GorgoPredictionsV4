from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.scheduler import next_runs, pregame_stages
from app.sports import all_sports

NOW = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)  # 9:00 hora del centro
INTERVAL = timedelta(hours=6)
LEADS = {"nba": timedelta(minutes=60), "futbol": timedelta(minutes=45)}
STAGES = {sport: [("previa", lead)] for sport, lead in LEADS.items()}
CLOSING = timedelta(minutes=15)
WITH_CLOSING = {"nba": [("previa", LEADS["nba"]), ("cierre", CLOSING)], "futbol": STAGES["futbol"]}
LAST = {"nba": NOW, "futbol": NOW}


class FakeConn:
    def __init__(self, starts):
        self.starts = starts  # [(deporte, inicio)]

    def execute(self, _query, params):
        lo, hi, sports = params
        rows = [
            {"sport": sport, "starts_at": start}
            for sport, start in sorted(self.starts, key=lambda s: s[1])
            if lo <= start <= hi and sport in sports
        ]

        class Result:
            def fetchall(self_inner):
                return rows

        return Result()


def test_pregame_run_before_regular_cycle():
    first_game = NOW + timedelta(hours=4)  # 19:00 UTC -> corrida a las 18:00 UTC
    wake, due = next_runs(FakeConn([("nba", first_game)]), NOW, LAST, INTERVAL, STAGES)
    assert wake == first_game - LEADS["nba"]
    assert due == {"nba": "previa"}


def test_regular_cycle_when_games_are_far():
    games = [("nba", NOW + timedelta(hours=10)), ("futbol", NOW + timedelta(hours=10))]
    wake, due = next_runs(FakeConn(games), NOW, LAST, INTERVAL, STAGES)
    assert wake == NOW + INTERVAL
    assert due == {"nba": "regular", "futbol": "regular"}


def test_skips_pregame_too_close_to_last_run():
    # La previa caería 10 min después de la última corrida: se salta a la siguiente.
    games = [("nba", NOW + timedelta(minutes=70)), ("nba", NOW + timedelta(hours=3))]
    wake, due = next_runs(FakeConn(games), NOW, LAST, INTERVAL, STAGES)
    assert wake == games[1][1] - LEADS["nba"]
    assert due == {"nba": "previa"}


def test_ignores_pregame_already_passed():
    # Partido en 30 min: su previa ya pasó.
    wake, due = next_runs(FakeConn([("nba", NOW + timedelta(minutes=30))]), NOW, LAST, INTERVAL, STAGES)
    assert wake == NOW + INTERVAL
    assert due["nba"] == "regular"


def test_each_sport_uses_its_own_lead():
    # Mismo horario en los dos deportes: la previa NBA (60 min) llega 15 min antes que la de fútbol (45 min).
    start = NOW + timedelta(hours=4)
    wake, due = next_runs(FakeConn([("nba", start), ("futbol", start)]), NOW, LAST, INTERVAL, STAGES)
    assert wake == start - LEADS["nba"]
    assert due == {"nba": "previa"}


def test_sports_due_a_few_minutes_apart_run_together():
    nba, futbol = NOW + timedelta(hours=4), NOW + timedelta(hours=3, minutes=48)  # previas 18:00 y 18:03
    wake, due = next_runs(FakeConn([("nba", nba), ("futbol", futbol)]), NOW, LAST, INTERVAL, STAGES)
    assert wake == nba - LEADS["nba"]
    assert due == {"nba": "previa", "futbol": "previa"}


def test_min_gap_counts_only_runs_of_the_same_sport():
    # NBA acaba de correr; fútbol corrió hace 2 h: su previa de dentro de 10 min sí toca.
    last = {"nba": NOW, "futbol": NOW - timedelta(hours=2)}
    game = NOW + timedelta(minutes=55)
    wake, due = next_runs(FakeConn([("futbol", game)]), NOW, last, INTERVAL, STAGES)
    assert wake == game - LEADS["futbol"]
    assert due == {"futbol": "previa"}


def test_a_sport_never_run_is_due_now():
    wake, due = next_runs(FakeConn([]), NOW, {"nba": NOW}, INTERVAL, STAGES)
    assert due == {"futbol": "regular"}
    assert wake < NOW


# ---------------------------------------------------------------- lectura de cierre


def test_closing_read_after_pregame():
    start = NOW + timedelta(hours=4)
    wake, due = next_runs(FakeConn([("nba", start)]), NOW, LAST, INTERVAL, WITH_CLOSING)
    assert (wake, due) == (start - LEADS["nba"], {"nba": "previa"})

    # Ya corrió la previa: lo siguiente es el cierre, 15 min antes del partido.
    after = start - LEADS["nba"] + timedelta(minutes=1)
    last = {"nba": start - LEADS["nba"], "futbol": NOW}
    wake, due = next_runs(FakeConn([("nba", start)]), after, last, INTERVAL, WITH_CLOSING)
    assert (wake, due) == (start - CLOSING, {"nba": "cierre"})


def test_closing_read_is_not_skipped_by_a_pregame_of_another_game():
    # Al llegar el cierre, la última sincronización fue hace 15 min: una previa se saltaría (MIN_GAP es 20),
    # el cierre no (CLOSING_MIN_GAP es 10).
    start = NOW + timedelta(minutes=30)
    wake, due = next_runs(FakeConn([("nba", start)]), NOW, LAST, INTERVAL, WITH_CLOSING)
    assert (wake, due) == (start - CLOSING, {"nba": "cierre"})


def test_closing_read_skipped_right_after_a_sync():
    # El cierre caería 5 min después de una sincronización que ya leyó los momios.
    start = NOW + timedelta(minutes=20)
    wake, due = next_runs(FakeConn([("nba", start)]), NOW, LAST, INTERVAL, WITH_CLOSING)
    assert (wake, due["nba"]) == (NOW + INTERVAL, "regular")


def test_pregame_a_few_minutes_after_a_closing_read_covers_it():
    # Cierre del primero a los 60 min y previa del segundo a los 63: una sola previa a los 60.
    first, second = NOW + timedelta(minutes=75), NOW + timedelta(minutes=123)
    wake, due = next_runs(FakeConn([("nba", first), ("nba", second)]), NOW, LAST, INTERVAL, WITH_CLOSING)
    assert (wake, due) == (first - CLOSING, {"nba": "previa"})


def test_stages_come_from_each_sport():
    nba, futbol = all_sports()["nba"], all_sports()["futbol"]
    nba = replace(nba, pregame_lead=timedelta(minutes=60), closing_lead=CLOSING)
    futbol = replace(futbol, pregame_lead=timedelta(minutes=45), closing_lead=None)
    assert pregame_stages(nba) == [("previa", timedelta(minutes=60)), ("cierre", CLOSING)]
    assert pregame_stages(futbol) == [("previa", timedelta(minutes=45))]
