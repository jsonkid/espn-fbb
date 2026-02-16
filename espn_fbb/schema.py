from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryStat(BaseModel):
    key: str
    you: float
    opp: float
    margin: float
    status: str


class CategorySignal(BaseModel):
    key: str
    pdiff: float


class Mover(BaseModel):
    key: str
    kind: str
    delta_margin: float
    today_margin: float
    yesterday_margin: float


class PlayerCandidate(BaseModel):
    player_id: int
    player_name: str
    lineup_slot_id: int
    lineup_role: str
    impact: float
    reasons: list[str] = Field(default_factory=list)


class CandidateGroup(BaseModel):
    you_good: list[PlayerCandidate] = Field(default_factory=list)
    you_bad: list[PlayerCandidate] = Field(default_factory=list)
    opp_good: list[PlayerCandidate] = Field(default_factory=list)
    opp_bad: list[PlayerCandidate] = Field(default_factory=list)


class CandidateMeta(BaseModel):
    source_scoring_period_id: int
    has_data: bool
    note: str | None = None


class RecapResponse(BaseModel):
    generated_at: str
    league_id: str
    team_id: int
    matchup_period_id: int
    matchup_score: dict[str, int]
    categories: list[CategoryStat]
    movers: list[Mover]
    candidates: CandidateGroup
    candidates_meta: CandidateMeta
    active_players: dict[str, int]


class GamesBreakdown(BaseModel):
    you_total_games: int
    opp_total_games: int
    games_diff: int


class GamesRemainingBreakdown(BaseModel):
    you_remaining_games: int
    opp_remaining_games: int
    games_remaining_diff: int


class LineupAction(BaseModel):
    type: str
    out_player_id: int
    out_player_name: str
    in_player_id: int
    in_player_name: str
    games_delta: float
    category_deltas: dict[str, float]
    score: int


class CategoryProjection(BaseModel):
    projected_you: float
    projected_opp: float
    projected_margin: float
    projected_status: str
    projected_pdiff: float
    projected_signal: str


class CategoryOutlook(BaseModel):
    current_you: float
    current_opp: float
    current_margin: float
    current_status: str
    current_pdiff: float
    current_signal: str
    projected_you: float
    projected_opp: float
    projected_margin: float
    projected_status: str
    projected_pdiff: float
    projected_signal: str


class SummaryHints(BaseModel):
    closest_categories: list[str] = Field(default_factory=list)
    biggest_advantages: list[str] = Field(default_factory=list)
    biggest_disadvantages: list[str] = Field(default_factory=list)
    swing_categories: list[str] = Field(default_factory=list)


class DataQuality(BaseModel):
    projection_basis: str
    projection_used: bool
    season_id: int
    scoring_period_ids: list[int] = Field(default_factory=list)
    your_starters_missing_season_stats: int
    opp_starters_missing_season_stats: int


class PreviewResponse(BaseModel):
    schema_version: str
    command: str
    generated_at: str
    league_id: str
    team_id: int
    matchup_period_id: int
    projected_matchup_score: dict[str, int]
    categories: dict[str, CategoryProjection]
    games: GamesBreakdown
    lineup_actions: list[LineupAction]
    summary_hints: SummaryHints
    data_quality: DataQuality
    outlook: dict[str, str]


class OutlookResponse(BaseModel):
    schema_version: str
    command: str
    generated_at: str
    league_id: str
    team_id: int
    matchup_period_id: int
    current_matchup_score: dict[str, int]
    projected_matchup_score: dict[str, int]
    categories: dict[str, CategoryOutlook]
    games_remaining: GamesRemainingBreakdown
    summary_hints: SummaryHints
    data_quality: DataQuality
    outlook: dict[str, str]
