from datetime import date, datetime, timezone

from app.sports.nba.engine.odds import names_match
from app.sports.nba.ingest.injuries import candidate_times, parse_pages, report_name, report_urls


def w(x0, top, text):
    return {"x0": x0, "top": top, "text": text}


HEADER = [
    w(289, 45, "Injury"), w(355, 45, "Report:"), w(438, 45, "03/10/26"),
    w(23, 107.7, "Game"), w(53, 107.7, "Date"), w(119.6, 107.7, "Game"), w(149, 107.7, "Time"),
    w(200, 107.7, "Matchup"), w(264, 107.7, "Team"), w(425, 107.7, "Player"), w(457, 107.7, "Name"),
    w(585.7, 107.7, "Current"), w(624, 107.7, "Status"), w(666, 107.7, "Reason"),
]

# Coordenadas reales del reporte del 10 de marzo de 2026 (página 1, primeras filas).
PAGE_1 = HEADER + [
    w(667, 128.9, "Injury/Illness"), w(721.8, 128.9, "-"), w(727, 128.9, "Right"), w(750, 128.9, "Knee;"), w(775, 128.9, "Injury"),
    w(24, 136, "03/10/2026"), w(120.6, 136, "07:00"), w(145.8, 136, "(ET)"), w(201, 136, "MEM@PHI"),
    w(265, 136, "Memphis"), w(305.7, 136, "Grizzlies"), w(426, 136, "Aldama,"), w(461.6, 136, "Santi"), w(586.7, 136, "Out"),
    w(667, 143, "Management"),
    w(426, 223.1, "Clayton"), w(459, 223.1, "Jr.,"), w(473, 223.1, "Walter"), w(586.7, 223.1, "Questionable"),
    w(667, 223.1, "Injury/Illness"), w(721.8, 223.1, "-"), w(727, 223.1, "Right"), w(750, 223.1, "Ankle;"), w(778, 223.1, "Sprain"),
    w(265, 260, "Philadelphia"), w(320, 260, "76ers"), w(426, 260, "Embiid,"), w(460, 260, "Joel"), w(586.7, 260, "Out"),
    w(667, 260, "Injury/Illness"), w(721.8, 260, "-"), w(727, 260, "Right"), w(750, 260, "Oblique;"),
    w(300, 560, "Page"), w(325, 560, "1"), w(335, 560, "of"), w(350, 560, "2"),
]
TITLE = [w(289, 45, "Injury"), w(355, 45, "Report:"), w(438, 45, "03/10/26"), w(539, 45, "05:30"), w(602, 45, "PM")]
# La página 2 no repite el encabezado (sólo el título), continúa el mismo partido y luego
# aparece un equipo sin entregar su lista.
PAGE_2 = TITLE + [
    w(426, 130, "Oubre"), w(455, 130, "Jr.,"), w(470, 130, "Kelly"), w(586.7, 130, "Available"),
    w(120.6, 160, "10:30"), w(145.8, 160, "(ET)"), w(201, 160, "MIN@LAC"), w(265, 160, "LA"), w(280, 160, "Clippers"),
    w(426, 160, "NOT"), w(445, 160, "YET"), w(465, 160, "SUBMITTED"),
]


def test_parse_rows_columns_and_multiline_reasons():
    report = parse_pages([PAGE_1, PAGE_2])
    rows = {r.player: r for r in report.rows}
    assert set(rows) == {"Aldama, Santi", "Clayton Jr., Walter", "Embiid, Joel", "Oubre Jr., Kelly"}
    aldama = rows["Aldama, Santi"]
    assert (aldama.game_date, aldama.team, aldama.status) == (date(2026, 3, 10), "Memphis Grizzlies", "out")
    assert aldama.reason == "Injury/Illness - Right Knee; Injury Management"  # línea de arriba + de abajo, en orden
    assert rows["Clayton Jr., Walter"].status == "questionable"
    assert rows["Clayton Jr., Walter"].team == "Memphis Grizzlies"  # se arrastra el equipo
    assert rows["Embiid, Joel"].team == "Philadelphia 76ers"
    assert rows["Oubre Jr., Kelly"].team == "Philadelphia 76ers"  # continúa en la página 2


def test_teams_not_yet_submitted():
    report = parse_pages([PAGE_1, PAGE_2])
    teams = {t: submitted for _, t, submitted in report.teams}
    assert teams == {"Memphis Grizzlies": True, "Philadelphia 76ers": True, "LA Clippers": False}


def test_report_urls_both_formats():
    t = datetime(2026, 3, 10, 21, 30, tzinfo=timezone.utc)  # 17:30 ET
    assert report_urls(t) == ["https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-03-10_05_30PM.pdf"]
    t = datetime(2025, 12, 15, 22, 0, tzinfo=timezone.utc)  # 17:00 ET
    assert report_urls(t)[1].endswith("Injury-Report_2025-12-15_05PM.pdf")


def test_candidate_times_go_back_in_15_minute_steps():
    now = datetime(2026, 3, 10, 21, 37, tzinfo=timezone.utc)  # 17:37 ET
    times = list(candidate_times(now))
    assert times[0].strftime("%H:%M") == "17:30"
    assert times[1].strftime("%H:%M") == "17:15"
    assert len(times) == 40  # de 17:30 a 07:45 (10 horas)


def test_report_names_match_stats_formats():
    assert report_name("Sharpe, Day'Ron") == "Day'Ron Sharpe"
    assert names_match(report_name("Sharpe, Day'Ron"), "D. Sharpe")
    assert names_match(report_name("Sharpe, Day'Ron"), "Sharpe Day&apos;Ron")
    assert names_match(report_name("Clayton Jr., Walter"), "Clayton Walter")
    assert names_match(report_name("Embiid, Joel"), "Embiid Joel")


PAGE_3 = TITLE + [
    w(667, 70, "recovery"), w(705, 70, "-"), w(710, 70, "Brace"),
    w(201, 83.6, "WAS@MIA"), w(265, 83.6, "Washington"), w(316, 83.6, "Wizards"),
    w(426, 83.6, "Davis,"), w(452, 83.6, "Anthony"), w(587, 83.6, "Out"),
    w(426, 105.6, "George,"), w(460, 105.6, "Kyshawn"), w(587, 105.6, "Out"),
    w(667, 105.6, "Personal"), w(700, 105.6, "Reasons;"), w(740, 105.6, "Not"), w(755, 105.6, "With"), w(775, 105.6, "Team"),
    w(426, 228.9, "Young,"), w(456, 228.9, "Trae"), w(587, 228.9, "Out"),
]


def test_page_without_header_and_team_word_in_reason():
    report = parse_pages([PAGE_1, PAGE_2, PAGE_3])
    rows = {r.player: r for r in report.rows}
    assert rows["Davis, Anthony"].team == "Washington Wizards"
    assert rows["Young, Trae"].team == "Washington Wizards"
    assert rows["George, Kyshawn"].reason == "Personal Reasons; Not With Team"
    # El motivo partido entre páginas se pega al último jugador de la página anterior.
    assert rows["Oubre Jr., Kelly"].reason.endswith("recovery - Brace")
    assert rows["Davis, Anthony"].reason == ""
