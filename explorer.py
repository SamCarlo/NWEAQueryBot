#!/usr/bin/env python3
"""NWEA anon.db explorer — RIT scores with sub-goals and Fall-to-Winter growth."""

import sqlite3
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static
from textual.containers import Horizontal, Vertical
from textual import on
from rich.text import Text

DB_PATH = "anon.db"
GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
ALL_TEACHERS = "All Teachers"

SUBJECT_COLORS = {
    "Mathematics":   "cyan",
    "Language Arts": "green",
    "Science":       "yellow",
}
GOAL_COLORS = {
    "Mathematics":   "dark_cyan",
    "Language Arts": "dark_green",
    "Science":       "dark_goldenrod",
}

RIT_MIN    = 130
RIT_MAX    = 240
RIT_BAR    = 34

GROWTH_MAX = 14
GROWTH_BAR = 24


# ── Queries ───────────────────────────────────────────────────────────────────

def get_teachers_for_grade(grade: str) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT DISTINCT t.TeacherName
        FROM teachers t
        JOIN students s ON t.StudentID = s.StudentID
        WHERE s.NWEAStandard_Grade = ?
          AND t.TeacherName IS NOT NULL
        ORDER BY t.TeacherName
        """,
        (grade,),
    )
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names


def _teacher_filter(teacher: str) -> tuple[str, list]:
    """Return an extra WHERE clause and params for teacher filtering."""
    if teacher == ALL_TEACHERS:
        return "", []
    return (
        "AND r.StudentID IN (SELECT StudentID FROM teachers WHERE TeacherName = ?)",
        [teacher],
    )


def get_rit_with_goals(grade: str, teacher: str = ALL_TEACHERS):
    clause, params = _teacher_filter(teacher)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        f"""
        SELECT
            r.Subject,
            ROUND(AVG(r.TestRITScore), 1),
            COUNT(DISTINCT r.StudentID),
            MAX(r.Goal1Name), ROUND(AVG(r.Goal1RitScore), 1),
            MAX(r.Goal2Name), ROUND(AVG(r.Goal2RitScore), 1),
            MAX(r.Goal3Name), ROUND(AVG(r.Goal3RitScore), 1),
            MAX(r.Goal4Name), ROUND(AVG(r.Goal4RitScore), 1)
        FROM results r
        JOIN students s ON r.StudentID = s.StudentID
        WHERE s.NWEAStandard_Grade = ? {clause}
        GROUP BY r.Subject
        ORDER BY r.Subject
        """,
        [grade] + params,
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_growth(grade: str, teacher: str = ALL_TEACHERS):
    clause, params = _teacher_filter(teacher)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        f"""
        SELECT
            r.Subject,
            ROUND(AVG(r.FallToWinterObservedGrowth),  2),
            ROUND(AVG(r.FallToWinterProjectedGrowth), 2),
            ROUND(AVG(r.TypicalFallToWinterGrowth),   2)
        FROM results r
        JOIN students s ON r.StudentID = s.StudentID
        WHERE s.NWEAStandard_Grade = ? {clause}
        GROUP BY r.Subject
        ORDER BY r.Subject
        """,
        [grade] + params,
    )
    rows = c.fetchall()
    conn.close()
    return rows


# ── Renderers ─────────────────────────────────────────────────────────────────

def _rit_bar(score: float, width: int) -> int:
    fill = int((score - RIT_MIN) / (RIT_MAX - RIT_MIN) * width)
    return max(1, min(fill, width))


def _growth_bar(value: float, width: int) -> int:
    fill = int(max(0.0, value) / GROWTH_MAX * width)
    return max(0, min(fill, width))


def build_rit_panel(grade: str, teacher: str = ALL_TEACHERS) -> Text:
    rows = get_rit_with_goals(grade, teacher)
    t = Text()

    if not rows:
        t.append("  No data for this selection.", style="dim")
        return t

    title = f"Grade {grade}" + (f"  —  {teacher}" if teacher != ALL_TEACHERS else "")
    t.append(f"\n  {title}  —  RIT Scores\n\n", style="bold white")

    for subject, avg_rit, count, g1n, g1r, g2n, g2r, g3n, g3r, g4n, g4r in rows:
        sc = SUBJECT_COLORS.get(subject, "white")
        gc = GOAL_COLORS.get(subject, "grey50")

        t.append(f"  {subject}\n", style=f"bold {sc}")
        t.append(f"  {'Overall':<23} ", style="white")
        t.append("█" * _rit_bar(avg_rit, RIT_BAR), style=sc)
        t.append(f"  {avg_rit}", style=f"bold {sc}")
        t.append(f"  n={count}\n", style="dim")

        for name, score in [(g1n, g1r), (g2n, g2r), (g3n, g3r), (g4n, g4r)]:
            if not name or score is None:
                continue
            label = (name[:20] + "…") if len(name) > 20 else name
            t.append(f"    {label:<21} ", style="dim white")
            t.append("█" * _rit_bar(score, RIT_BAR), style=gc)
            t.append(f"  {score}\n", style=gc)

        t.append("\n")

    t.append(
        f"  {'':22}  {RIT_MIN}{'─' * (RIT_BAR - 6)}{RIT_MAX}\n",
        style="dim",
    )
    return t


def build_growth_panel(grade: str, teacher: str = ALL_TEACHERS) -> Text:
    rows = get_growth(grade, teacher)
    t = Text()

    if not rows:
        t.append("  No data.", style="dim")
        return t

    title = f"Grade {grade}" + (f"  —  {teacher}" if teacher != ALL_TEACHERS else "")
    t.append(f"\n  {title}  —  Fall → Winter Growth\n\n", style="bold white")

    growth_rows = [
        ("Observed",  "white"),
        ("Projected", "grey70"),
        ("Typical",   "grey50"),
    ]

    for subject, obs, proj, typ in rows:
        sc = SUBJECT_COLORS.get(subject, "white")
        t.append(f"  {subject}\n", style=f"bold {sc}")

        for (label, lc), value in zip(growth_rows, [obs, proj, typ]):
            if value is None:
                t.append(f"    {label:<10} ", style=lc)
                t.append("─ no data\n", style="dim")
                continue
            t.append(f"    {label:<10} ", style=lc)
            t.append("█" * _growth_bar(value, GROWTH_BAR), style=sc)
            t.append(f"  {value:+.1f}\n", style=lc)

        t.append("\n")

    t.append(
        f"  {'':10}  0{'─' * (GROWTH_BAR - 2)}{GROWTH_MAX}+\n",
        style="dim",
    )
    return t


# ── App ───────────────────────────────────────────────────────────────────────

class NWEAExplorer(App):
    CSS = """
    Screen { background: $surface; }

    .selector-pane {
        width: 26;
        border: solid $primary-darken-2;
        padding: 0 1;
    }
    .pane-heading {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1 0;
    }
    ListView { border: none; background: transparent; }
    ListItem  { padding: 0 2; }

    #rit-pane {
        width: 1fr;
        border: solid $primary-darken-2;
        padding: 1 2;
    }
    #growth-pane {
        width: 1fr;
        border: solid $primary-darken-2;
        padding: 1 2;
    }
    """

    TITLE = "NWEA Explorer"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self._grade         = GRADES[0]
        self._teacher       = ALL_TEACHERS
        self._teacher_names = [ALL_TEACHERS]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="selector-pane"):
                yield Label("Grade Level", classes="pane-heading")
                yield ListView(
                    *[ListItem(Label(g), id=f"grade-{g}") for g in GRADES],
                    id="grade-list",
                )
            with Vertical(classes="selector-pane", id="teacher-pane"):
                yield Label("Teacher", classes="pane-heading")
                yield ListView(id="teacher-list")
            with Vertical(id="rit-pane"):
                yield Static(id="rit-chart")
            with Vertical(id="growth-pane"):
                yield Static(id="growth-chart")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#grade-list", ListView).index = 0
        self._repopulate_teachers(GRADES[0])
        self._refresh()

    @on(ListView.Highlighted, "#grade-list")
    def grade_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and event.item.id:
            self._grade   = event.item.id.removeprefix("grade-")
            self._teacher = ALL_TEACHERS
            self._repopulate_teachers(self._grade)
            self._refresh()

    @on(ListView.Highlighted, "#teacher-list")
    def teacher_highlighted(self, event: ListView.Highlighted) -> None:
        idx = self.query_one("#teacher-list", ListView).index
        if idx is not None and 0 <= idx < len(self._teacher_names):
            self._teacher = self._teacher_names[idx]
            self._refresh()

    def _repopulate_teachers(self, grade: str) -> None:
        self._teacher_names = [ALL_TEACHERS] + get_teachers_for_grade(grade)
        teacher_list = self.query_one("#teacher-list", ListView)
        teacher_list.clear()
        for name in self._teacher_names:
            teacher_list.append(ListItem(Label(name)))
        teacher_list.index = 0

    def _refresh(self) -> None:
        self.query_one("#rit-chart",    Static).update(build_rit_panel(self._grade, self._teacher))
        self.query_one("#growth-chart", Static).update(build_growth_panel(self._grade, self._teacher))


if __name__ == "__main__":
    NWEAExplorer().run()
