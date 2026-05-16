import html
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


DATE_PATTERN = re.compile(
    r'\{"id":"(?P<date_id>id\d+)","iso":"(?P<iso>[^"]+)",'
    r'"dateText":"(?P<date_text>[^"]+)","matchWindowEndDate":"(?P<match_window_end_date>[^"]+)"\}'
)
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


def http_get_text(url: str, accept: str = "text/html,application/xhtml+xml") -> str:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_ranking_dates(page_html: str, start_year: int | None = None) -> list[dict[str, str]]:
    decoded = html.unescape(page_html)
    seen: set[str] = set()
    dates: list[dict[str, str]] = []

    next_data_match = NEXT_DATA_PATTERN.search(page_html)
    if next_data_match:
        payload = json.loads(html.unescape(next_data_match.group(1)))
        ranking = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("pageData", {})
            .get("ranking", {})
        )
        for item in ranking.get("allAvailableDates", []):
            date_id = item.get("id")
            ranking_date = item.get("date") or item.get("matchWindowEndDate")
            if not date_id or not ranking_date or date_id in seen:
                continue
            year = int(ranking_date[:4])
            if start_year is not None and year < start_year:
                continue
            seen.add(date_id)
            dates.append(
                {
                    "date_id": date_id,
                    "iso": f"{ranking_date}T00:00:00.000Z",
                    "date_text": ranking_date,
                    "match_window_end_date": item.get("matchWindowEndDate") or ranking_date,
                }
            )

    for match in DATE_PATTERN.finditer(decoded):
        item = match.groupdict()
        if item["date_id"] in seen:
            continue
        year = int(item["iso"][:4])
        if start_year is not None and year < start_year:
            continue
        seen.add(item["date_id"])
        dates.append(item)
    return sorted(dates, key=lambda item: item["iso"])


def fetch_ranking_snapshot(
    api_url: str,
    date_id: str,
    gender: str = "men",
    locale: str = "en",
) -> dict[str, Any]:
    if date_id.startswith("FRS_"):
        query = urlencode({"rankingScheduleId": date_id, "language": locale})
        url = f"https://api.fifa.com/api/v3/fifarankings/rankings/rankingsbyschedule?{query}"
        text = http_get_text(url, accept="application/json,text/plain,*/*")
        return json.loads(text)

    query = urlencode({"locale": locale, "dateId": date_id, "gender": gender})
    url = f"{api_url}?{query}"
    text = http_get_text(url, accept="application/json,text/plain,*/*")
    return json.loads(text)


def ranking_payload_to_rows(payload: dict[str, Any], date_meta: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if "Results" in payload:
        for item in payload.get("Results", []):
            team_names = item.get("TeamName") or []
            team_name = next(
                (
                    name.get("Description")
                    for name in team_names
                    if str(name.get("Locale", "")).lower().startswith("en")
                ),
                team_names[0].get("Description") if team_names else None,
            )
            rows.append(
                {
                    "date_id": date_meta["date_id"],
                    "ranking_date": date_meta["iso"][:10],
                    "match_window_end_date": date_meta["match_window_end_date"],
                    "rank": item.get("Rank"),
                    "previous_rank": item.get("PrevRank"),
                    "team": team_name,
                    "country_code": item.get("IdCountry"),
                    "fifa_team_id": item.get("IdTeam"),
                    "total_points": item.get("TotalPoints"),
                    "previous_points": item.get("PrevPoints"),
                    "confederation": item.get("ConfederationName"),
                    "last_update_date": date_meta["iso"],
                }
            )
        return rows

    for item in payload.get("rankings", []):
        ranking_item = item.get("rankingItem") or {}
        tag = item.get("tag") or {}
        rows.append(
            {
                "date_id": date_meta["date_id"],
                "ranking_date": date_meta["iso"][:10],
                "match_window_end_date": date_meta["match_window_end_date"],
                "rank": ranking_item.get("rank"),
                "previous_rank": ranking_item.get("previousRank"),
                "team": ranking_item.get("name"),
                "country_code": ranking_item.get("countryCode"),
                "fifa_team_id": ranking_item.get("idTeam"),
                "total_points": ranking_item.get("totalPoints"),
                "previous_points": item.get("previousPoints"),
                "confederation": tag.get("id"),
                "last_update_date": item.get("lastUpdateDate"),
            }
        )
    return rows


def polite_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
