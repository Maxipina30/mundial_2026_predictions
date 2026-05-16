import asyncio
import json
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, async_playwright


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class SofaScoreClient:
    def __init__(
        self,
        api_url: str = "https://api.sofascore.com/api/v1",
        referer: str = "https://www.sofascore.com/football",
        locale: str = "en-US",
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.referer = referer
        self.locale = locale
        self.user_agent = user_agent
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "SofaScoreClient":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            locale=self.locale,
            user_agent=self.user_agent,
        )
        page = await self._context.new_page()
        await page.goto(self.referer, wait_until="domcontentloaded", timeout=60_000)
        await page.close()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def api_get(self, path: str) -> dict[str, Any] | None:
        if self._context is None:
            raise RuntimeError("SofaScoreClient must be used as an async context manager")

        url = f"{self.api_url}/{path.lstrip('/')}"
        response = await self._context.request.get(
            url,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Referer": self.referer,
            },
            timeout=60_000,
        )
        text = await response.text()
        if response.status == 404:
            return None
        if response.status != 200:
            print(f"  HTTP {response.status}: {url}")
            return None
        return json.loads(text)

    async def get_seasons(self, unique_tournament_id: int) -> list[dict[str, Any]]:
        payload = await self.api_get(f"unique-tournament/{unique_tournament_id}/seasons")
        if not payload:
            return []
        return payload.get("seasons", [])

    async def get_season_id(
        self,
        unique_tournament_id: int,
        season_year: str,
    ) -> tuple[int, str]:
        seasons = await self.get_seasons(unique_tournament_id)
        for season in seasons:
            if str(season.get("year")) == str(season_year):
                return season["id"], season.get("name") or str(season_year)
        available = ", ".join(str(season.get("year")) for season in seasons[:12])
        raise RuntimeError(
            f"Season {season_year!r} not found for tournament {unique_tournament_id}. "
            f"Available seasons include: {available}"
        )

    async def get_tournament_events(
        self,
        unique_tournament_id: int,
        season_id: int,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for direction in ("last", "next"):
            page = 0
            while True:
                payload = await self.api_get(
                    f"unique-tournament/{unique_tournament_id}/season/{season_id}/events/{direction}/{page}"
                )
                if not payload:
                    break
                page_events = payload.get("events", [])
                if direction == "last":
                    page_events = list(reversed(page_events))
                events.extend(page_events)
                if not payload.get("hasNextPage"):
                    break
                page += 1

        deduped = {event["id"]: event for event in events if event.get("id")}
        return sorted(deduped.values(), key=lambda event: event.get("startTimestamp", 0))

    async def get_event_incidents(self, event_id: int) -> dict[str, Any] | None:
        return await self.api_get(f"event/{event_id}/incidents")

    async def get_event_lineups(self, event_id: int) -> dict[str, Any] | None:
        return await self.api_get(f"event/{event_id}/lineups")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def event_to_match_row(
    event: dict[str, Any],
    tournament_name: str,
    season_year: str,
    season_id: int,
) -> dict[str, Any]:
    tournament = event.get("tournament") or {}
    unique_tournament = tournament.get("uniqueTournament") or {}
    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    home_country = home_team.get("country") or {}
    away_country = away_team.get("country") or {}
    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    status = event.get("status") or {}
    round_info = event.get("roundInfo") or {}
    time = event.get("time") or {}
    venue = event.get("venue") or {}
    venue_city = venue.get("city") or {}
    venue_country = venue.get("country") or {}

    return {
        "event_id": event.get("id"),
        "slug": event.get("slug"),
        "tournament": tournament_name,
        "sub_tournament": tournament.get("name"),
        "sofascore_tournament_id": tournament.get("id"),
        "unique_tournament_id": unique_tournament.get("id"),
        "season_year": season_year,
        "season_id": season_id,
        "start_timestamp": event.get("startTimestamp"),
        "status": status.get("type"),
        "round": round_info.get("round"),
        "round_name": round_info.get("name"),
        "is_group": tournament.get("isGroup"),
        "group_name": tournament.get("groupName"),
        "group_sign": tournament.get("groupSign"),
        "home_team": home_team.get("name"),
        "away_team": away_team.get("name"),
        "home_team_id": home_team.get("id"),
        "away_team_id": away_team.get("id"),
        "home_name_code": home_team.get("nameCode"),
        "away_name_code": away_team.get("nameCode"),
        "home_country_code": home_country.get("alpha3"),
        "away_country_code": away_country.get("alpha3"),
        "home_sofascore_ranking": home_team.get("ranking"),
        "away_sofascore_ranking": away_team.get("ranking"),
        "home_score": home_score.get("normaltime") if home_score.get("normaltime") is not None else home_score.get("current"),
        "away_score": away_score.get("normaltime") if away_score.get("normaltime") is not None else away_score.get("current"),
        "winner_code": event.get("winnerCode"),
        "venue": venue.get("name"),
        "venue_id": venue.get("id"),
        "venue_city": venue_city.get("name"),
        "venue_country": venue_country.get("name"),
        "venue_country_code": venue_country.get("alpha3"),
        "venue_latitude": (venue.get("venueCoordinates") or {}).get("latitude"),
        "venue_longitude": (venue.get("venueCoordinates") or {}).get("longitude"),
        "current_period_start_timestamp": time.get("currentPeriodStartTimestamp"),
    }


async def run_async(coro):
    return await coro


def run(coro):
    return asyncio.run(coro)
