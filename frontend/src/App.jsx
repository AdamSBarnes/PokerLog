import { useEffect, useMemo, useState, useCallback } from "react";
import Plot from "react-plotly.js";
import {
  buildSeasonParam,
  clearToken,
  deleteJson,
  fetchJson,
  fetchJsonAuth,
  isLoggedIn,
  login,
  postJson,
  putJson,
} from "./api.js";

const TABS = [
  { key: "dashboard", label: "Player Summary" },
  { key: "profile", label: "Player Profiles" },
  { key: "odds", label: "Wagering Markets" },
  { key: "streaks", label: "Losing Streaks" },
  { key: "history", label: "Game History" },
  { key: "admin", label: "Admin" },
];

const METRIC_DEFS = [
  ["Played", "Number of games played."],
  ["Costs", "Sum of all entry fees."],
  ["Winnings", "Total won. Settled at end of season(s)."],
  ["Net Position", "Winnings less Costs."],
  ["Wins", "Number of wins across all games."],
  ["Wins Ten", "Number of wins in $10 games."],
  ["Win Rate", "Wins divided by Played."],
  ["Return Rate (ROI)", "Winnings divided by Costs."],
  ["Last Win Date", "Date of the last win."],
  ["Heads Up Conversion Rate", "Rate at which final two results in a win."],
  ["Runner Up Rate", "Rate at which player finishes second."],
  ["First Out Rate", "Rate at which player is knocked out first."],
];

/* ─── Reusable DataTable ───────────────────────────────────── */

function DataTable({ rows }) {
  if (!rows || rows.length === 0) {
    return <p className="muted">No data.</p>;
  }
  const headers = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {headers.map((h) => (
                <td key={h} className={typeof row[h] === "number" && row[h] < 0 ? "negative" : ""}>
                  {row[h]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Tab panels ────────────────────────────────────────────── */

function DashboardTab({ summary, roiPlotData }) {
  return (
    <div className="dashboard-container">
      {/* ── Hero header ───────────────── */}
      <div className="dashboard-header-card">
        <span className="dashboard-event-badge">📊 LEAGUE OVERVIEW</span>
        <h2 className="dashboard-title">Player Summary</h2>
        <p className="dashboard-subtitle">
          Season-by-season performance breakdown for all players.
          Use the sidebar to filter by season.
        </p>
      </div>

      {/* ── Performance table ──────────── */}
      <div className="dashboard-section">
        <h3 className="dashboard-section-title">🏆 Performance Table</h3>
        <DataTable rows={summary} />
      </div>

      {/* ── ROI chart ─────────────────── */}
      <div className="dashboard-section">
        <h3 className="dashboard-section-title">📈 Return on Investment</h3>
        <Plot
          data={roiPlotData}
          layout={{
            height: 560,
            margin: { l: 50, r: 20, t: 20, b: 60 },
            legend: { orientation: "h", y: -0.12, xanchor: "center", x: 0.5, font: { size: 15 } },
            paper_bgcolor: "transparent",
            plot_bgcolor: "#f8fafd",
            font: { color: "#013356" },
            xaxis: { title: "Game Number", gridcolor: "#d0d8e4", color: "#013356" },
            yaxis: { title: "Return per $$ spent", gridcolor: "#d0d8e4", color: "#013356" },
          }}
          style={{ width: "100%" }}
          config={{ displayModeBar: false }}
        />
      </div>

      {/* ── Metric definitions ─────────── */}
      <div className="dashboard-section dashboard-metrics">
        <h3 className="dashboard-section-title">📖 Metric Definitions</h3>
        <div className="dashboard-metric-grid">
          {METRIC_DEFS.map(([term, def]) => (
            <div key={term} className="dashboard-metric-item">
              <dt>{term}</dt>
              <dd>{def}</dd>
            </div>
          ))}
        </div>
        <p className="muted note">
          Places only tracked since game 94 (early season 2). Stats filtered by
          season. Overall winner determined by Return Rate within a season.
        </p>
      </div>
    </div>
  );
}

function streakMedal(rank) {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return `#${rank}`;
}

function StreaksTab({ streaks, currentStreaks }) {
  const maxLen = Math.max(1, ...streaks.map((s) => s.streak_length));
  const worst = streaks.length ? streaks[0] : null;

  return (
    <div className="streaks-container">
      {/* ── Hero header ───────────────── */}
      <div className="streaks-header-card">
        <span className="streaks-event-badge">🔥 WALL OF SHAME</span>
        <h2 className="streaks-title">Losing Streaks</h2>
        <p className="streaks-subtitle">
          The longest droughts in league history. How long can you go without a
          win before luck — or skill — finally turns?
        </p>
      </div>

      {/* ── Worst-ever spotlight ───────── */}
      {worst && (
        <div className="streaks-spotlight">
          <span className="streaks-spot-label">LONGEST DROUGHT</span>
          <span className="streaks-spot-name">{worst.player}</span>
          <span className="streaks-spot-stat">
            {worst.streak_length} <small>games</small>
          </span>
          <span className="streaks-spot-detail">
            Games {worst.streak_start_game}–{worst.streak_end_game}
            &nbsp;·&nbsp;Lost {worst.streak_loss}
            {worst.is_active === 1 && (
              <span className="streak-live-badge">ACTIVE</span>
            )}
          </span>
        </div>
      )}

      {/* ── Current active streaks ────── */}
      {currentStreaks.length > 0 && (
        <>
          <h3 className="streaks-section-title">
            <span className="streak-live-dot" /> Currently Active
          </h3>
          <div className="streaks-grid">
            {currentStreaks.map((s) => {
              const pct = Math.round((s.streak_length / maxLen) * 100);
              return (
                <div className="streak-card streak-card--active" key={s.player + s.streak_start_game}>
                  <div className="streak-card-rank">{streakMedal(s.streak_rank)}</div>
                  <span className="streak-live-badge">LIVE</span>
                  <div className="streak-card-player">{s.player}</div>
                  <div className="streak-card-length">
                    {s.streak_length} <small>games</small>
                  </div>
                  <div className="streak-bar-track">
                    <div
                      className="streak-bar-fill streak-bar--active"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="streak-card-stats">
                    <div className="streak-stat">
                      <span className="streak-stat-label">From game</span>
                      <span className="streak-stat-value">{s.streak_start_game}</span>
                    </div>
                    <div className="streak-stat">
                      <span className="streak-stat-label">Lost</span>
                      <span className="streak-stat-value">{s.streak_loss}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ── All-time leaderboard ──────── */}
      <h3 className="streaks-section-title">🏆 All-Time Top 10</h3>
      <div className="streaks-grid">
        {streaks.map((s) => {
          const pct = Math.round((s.streak_length / maxLen) * 100);
          return (
            <div className="streak-card" key={s.player + s.streak_start_game}>
              <div className="streak-card-rank">{streakMedal(s.streak_rank)}</div>
              {s.is_active === 1 && <span className="streak-live-badge">ACTIVE</span>}
              <div className="streak-card-player">{s.player}</div>
              <div className="streak-card-length">
                {s.streak_length} <small>games</small>
              </div>
              <div className="streak-bar-track">
                <div
                  className="streak-bar-fill"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="streak-card-stats">
                <div className="streak-stat">
                  <span className="streak-stat-label">Games</span>
                  <span className="streak-stat-value">
                    {s.streak_start_game}–{s.streak_end_game}
                  </span>
                </div>
                <div className="streak-stat">
                  <span className="streak-stat-label">Lost</span>
                  <span className="streak-stat-value">{s.streak_loss}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}

function HistoryTab({ games }) {
  const totalGames = games?.length ?? 0;
  const latestGame = totalGames > 0 ? games[games.length - 1] : null;

  return (
    <div className="history-container">
      {/* ── Hero header ───────────────── */}
      <div className="history-header-card">
        <span className="history-event-badge">📜 THE RECORD BOOKS</span>
        <h2 className="history-title">Game History</h2>
        <p className="history-subtitle">
          Every hand, every game, every result — the complete archive.
        </p>
      </div>

      {/* ── Quick stats spotlight ──────── */}
      {latestGame && (
        <div className="history-spotlight">
          <span className="history-spot-label">LATEST RESULT</span>
          <span className="history-spot-name">Game #{latestGame.game_overall}</span>
          <span className="history-spot-stat">{latestGame.winner || "—"}</span>
          <span className="history-spot-detail">
            {latestGame.game_date}&nbsp;·&nbsp;${latestGame.stake}&nbsp;·&nbsp;{totalGames} games total
          </span>
        </div>
      )}

      {/* ── Table ─────────────────────── */}
      <div className="history-section">
        <h3 className="history-section-title">📋 All Games</h3>
        <DataTable rows={games} />
      </div>
    </div>
  );
}

/* ─── Odds / Predictions Tab ────────────────────────────────── */

function formatPct(val) {
  return `${(val * 100).toFixed(1)}%`;
}

function oddsClass(odds) {
  if (odds <= 3.0) return "odds-fav";
  if (odds <= 6.0) return "odds-mid";
  return "odds-long";
}

function OddsTab() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchJson("/api/predictions")
      .then((data) => {
        setPredictions(data);
        setErr("");
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading predictions…</p>;
  if (err) return <div className="error">{err}</div>;
  if (!predictions.length) return <p className="muted">Not enough data to generate odds.</p>;

  const favourite = predictions[0];

  // Bottom players = the long shots (at least 3)
  const longshotStart = Math.max(0, predictions.length - Math.max(3, Math.ceil(predictions.length / 2)));
  const longShots = predictions.slice(longshotStart);

  return (
    <div className="odds-container">
      <div className="odds-header-card">
        <div className="odds-event-badge">NEXT GAME</div>
        <h2 className="odds-title">Winner Market</h2>
        <p className="odds-subtitle">
          Odds derived from historical performance, recent form &amp; head-to-head stats.
          <br />
        </p>
      </div>

      {/* Favourite callout */}
      <div className="odds-favourite-card">
        <span className="odds-fav-label">★ FAVOURITE</span>
        <span className="odds-fav-name">{favourite.player}</span>
        <span className="odds-fav-odds">${favourite.decimal_odds.toFixed(2)}</span>
      </div>

      {/* Odds grid */}
      <div className="odds-grid">
        {predictions.map((p, i) => (
          <div key={p.player} className="odds-card">
            <div className="odds-card-rank">#{i + 1}</div>
            <div className="odds-card-player">{p.player}</div>
            <div className={`odds-card-price ${oddsClass(p.decimal_odds)}`}>
              ${p.decimal_odds.toFixed(2)}
            </div>
            <div className="odds-card-prob">{formatPct(p.probability)} chance of winning</div>

            <div className="odds-card-stats">
              <div className="odds-stat">
                <span className="odds-stat-label">Win Rate</span>
                <span className="odds-stat-value">{formatPct(p.overall_win_rate)}</span>
              </div>
              <div className="odds-stat">
                <span className="odds-stat-label">Form (EWMA)</span>
                <span className="odds-stat-value">{formatPct(p.ewma_win_rate)}</span>
              </div>
              <div className="odds-stat">
                <span className="odds-stat-label">Last {10}</span>
                <span className="odds-stat-value">{formatPct(p.recent_form)}</span>
              </div>
              <div className="odds-stat">
                <span className="odds-stat-label">Games</span>
                <span className="odds-stat-value">{p.games_played}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Long Shots Lounge */}
      {longShots.length > 0 && (
        <>
          <div className="longshot-header-card">
            <span className="longshot-event-badge">🐌 REALITY CHECK</span>
            <h2 className="longshot-title">Long Shots Lounge</h2>
            <p className="longshot-subtitle">
              For those whose best strategy might be hoping everyone else forgets to show up.
            </p>
          </div>

          <div className="longshot-grid">
            {longShots.map((p) => {
              const gamesUntil = Math.round(p.expected_games_to_win);
              const mockLines = [];

              // "One win in next 10" — the headline stat
              mockLines.push({
                icon: "🎰",
                label: "Win at least once in next 10",
                value: formatPct(p.win_one_in_ten),
              });

              // Top-2 finish in next 5
              mockLines.push({
                icon: "🥈",
                label: "Finish top 2 at least once in next 5",
                value: formatPct(p.top_two_one_in_five),
              });

              // Expected games until win
              mockLines.push({
                icon: "📅",
                label: "Expected games until next win",
                value: `${gamesUntil} game${gamesUntil !== 1 ? "s" : ""}`,
              });

              // First-out rate roast
              if (p.first_out_rate >= 0.2) {
                mockLines.push({
                  icon: "💀",
                  label: "Chance of being first out",
                  value: formatPct(p.first_out_rate),
                });
              }

              // Especially savage if win prob is very low
              if (p.probability < 0.08) {
                const coinFlipGames = Math.ceil(Math.log(0.5) / Math.log(1 - p.probability));
                mockLines.push({
                  icon: "🪙",
                  label: "Games needed for a coin-flip chance of winning",
                  value: `${coinFlipGames}`,
                });
              }

              return (
                <div key={p.player} className="longshot-card">
                  <div className="longshot-card-header">
                    <span className="longshot-card-player">{p.player}</span>
                    <span className={`longshot-card-odds ${oddsClass(p.decimal_odds)}`}>
                      ${p.decimal_odds.toFixed(2)}
                    </span>
                  </div>
                  <div className="longshot-card-prob">
                    {formatPct(p.probability)} chance of winning next game
                  </div>
                  <div className="longshot-stats">
                    {mockLines.map((m, i) => (
                      <div key={i} className="longshot-stat-row">
                        <span className="longshot-stat-icon">{m.icon}</span>
                        <span className="longshot-stat-label">{m.label}</span>
                        <span className="longshot-stat-value">{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Login form ────────────────────────────────────────────── */

/* ─── Player Profile Tab ────────────────────────────────────── */

function ProfileStatCard({ label, value, sub, negative }) {
  return (
    <div className="profile-stat-card">
      <span className="profile-stat-label">{label}</span>
      <span className={`profile-stat-value${negative ? " negative" : ""}`}>{value}</span>
      {sub && <span className="profile-stat-sub">{sub}</span>}
    </div>
  );
}

function PlayerProfileTab({ players }) {
  const [selectedPlayer, setSelectedPlayer] = useState("");
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const loadProfile = useCallback((name) => {
    if (!name) { setProfile(null); return; }
    setLoading(true);
    setErr("");
    fetchJson(`/api/player-profile/${encodeURIComponent(name)}`)
      .then((data) => { setProfile(data); setErr(""); })
      .catch((e) => { setErr(e.message); setProfile(null); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedPlayer) loadProfile(selectedPlayer);
  }, [selectedPlayer, loadProfile]);

  const activePlayers = (players || []).filter((p) => p.active);

  // Build personal ROI plot data
  const roiPlotData = useMemo(() => {
    if (!profile?.personal_roi?.length) return [];
    return [{
      type: "scatter",
      mode: "lines+markers",
      name: profile.player,
      x: profile.personal_roi.map((r) => r.game_overall),
      y: profile.personal_roi.map((r) => r.roi),
      line: { color: "#013356", width: 2.5 },
      marker: { size: 4, color: "#013356" },
      fill: "tozeroy",
      fillcolor: "rgba(1,51,86,0.08)",
    }, {
      type: "scatter",
      mode: "lines",
      name: "Break-even",
      x: profile.personal_roi.map((r) => r.game_overall),
      y: profile.personal_roi.map(() => 1.0),
      line: { color: "#e74c3c", width: 1.5, dash: "dash" },
      hoverinfo: "skip",
    }];
  }, [profile]);

  if (!activePlayers.length) return <p className="muted">Loading players…</p>;

  return (
    <div className="profile-container">
      {/* Player selector */}
      <div className="profile-selector-card">
        <h2 className="profile-selector-title">🔍 Player Deep Dive</h2>
        <p className="profile-selector-sub">Select a player to explore their complete profile, strengths, weaknesses, and head-to-head records.</p>
        <div className="profile-chip-row">
          {activePlayers.map((p) => (
            <button
              key={p.name}
              className={`profile-chip${selectedPlayer === p.name ? " active" : ""}`}
              onClick={() => setSelectedPlayer(p.name)}
            >
              {p.display_name || p.name}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="muted">Loading profile…</p>}
      {err && <div className="error">{err}</div>}

      {profile && !loading && (
        <>
          {/* ── Header ── */}
          <div className="profile-header-card">
            <div className="profile-header-left">
              <h1 className="profile-player-name">{profile.player}</h1>
              <div className="profile-tagline">
                {profile.key_stats.net_position >= 0 ? "📈" : "📉"}{" "}
                Career: {profile.key_stats.played} games · {profile.key_stats.wins} wins ·{" "}
                <span className={profile.key_stats.net_position >= 0 ? "positive" : "negative"}>
                  ${profile.key_stats.net_position.toLocaleString()}
                </span>
              </div>
            </div>
            <div className="profile-header-right">
              <div className="profile-big-stat">
                <span className="profile-big-stat-val">${profile.key_stats.return_rate.toFixed(2)}</span>
                <span className="profile-big-stat-label">ROI</span>
              </div>
              <div className="profile-big-stat">
                <span className="profile-big-stat-val">{(profile.key_stats.win_rate * 100).toFixed(0)}%</span>
                <span className="profile-big-stat-label">Win Rate</span>
              </div>
            </div>
          </div>

          {/* ── Key Stats Grid ── */}
          <div className="profile-section">
            <h3 className="profile-section-title">📊 Key Statistics</h3>
            <div className="profile-stats-grid">
              <ProfileStatCard label="Games Played" value={profile.key_stats.played} />
              <ProfileStatCard label="Wins" value={profile.key_stats.wins} sub={`${profile.key_stats.wins_ten} in $10 games`} />
              <ProfileStatCard label="Total Costs" value={`$${profile.key_stats.costs.toLocaleString()}`} />
              <ProfileStatCard label="Winnings" value={`$${profile.key_stats.winnings.toLocaleString()}`} />
              <ProfileStatCard label="Net Position" value={`$${profile.key_stats.net_position.toLocaleString()}`} negative={profile.key_stats.net_position < 0} />
              <ProfileStatCard label="Avg Finish" value={profile.key_stats.avg_finish} />
              <ProfileStatCard label="HU Conversion" value={`${(profile.key_stats.heads_up_conversion * 100).toFixed(0)}%`} sub={`${profile.key_stats.heads_up_wins}/${profile.key_stats.heads_up_appearances}`} />
              <ProfileStatCard label="Runner-Up Rate" value={`${(profile.key_stats.runner_up_rate * 100).toFixed(0)}%`} sub={`${profile.key_stats.runner_up_count} times`} />
              <ProfileStatCard label="First Out Rate" value={`${(profile.key_stats.first_out_rate * 100).toFixed(0)}%`} sub={`${profile.key_stats.first_out_count} times`} />
              <ProfileStatCard label="Last Win" value={profile.key_stats.last_win_date || "Never"} />
            </div>
          </div>

          {/* ── Recent Form ── */}
          <div className="profile-section">
            <h3 className="profile-section-title">🔥 Recent Form (Last {profile.recent_form.length})</h3>
            <div className="profile-form-row">
              {profile.recent_form.map((g) => (
                <div
                  key={g.game_overall}
                  className={`profile-form-pip${g.won ? " win" : " loss"}`}
                  title={`Game #${g.game_overall} — ${g.game_date}\nFinished ${g.finish_position}/${g.players_in_game} ($${g.stake})`}
                >
                  <span className="profile-form-letter">{g.won ? "W" : "L"}</span>
                  <span className="profile-form-pos">{g.finish_position}/{g.players_in_game}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Strengths & Weaknesses ── */}
          {(profile.strengths.length > 0 || profile.weaknesses.length > 0) && (
            <div className="profile-sw-grid">
              {profile.strengths.length > 0 && (
                <div className="profile-sw-card strengths">
                  <h3>💪 Strengths</h3>
                  <ul>
                    {profile.strengths.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
              {profile.weaknesses.length > 0 && (
                <div className="profile-sw-card weaknesses">
                  <h3>⚠️ Weaknesses</h3>
                  <ul>
                    {profile.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* ── Badges ── */}
          {profile.badges.length > 0 && (
            <div className="profile-section">
              <h3 className="profile-section-title">🏅 Achievements</h3>
              <div className="profile-badges-grid">
                {profile.badges.map((b, i) => (
                  <div key={i} className="profile-badge">
                    <span className="profile-badge-icon">{b.icon}</span>
                    <div className="profile-badge-info">
                      <span className="profile-badge-title">{b.title}</span>
                      <span className="profile-badge-desc">{b.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Personal ROI Chart ── */}
          {profile.personal_roi.length > 0 && (
            <div className="card full-width">
              <h3 className="profile-section-title" style={{ marginBottom: 12 }}>📈 ROI Over Time</h3>
              <Plot
                data={roiPlotData}
                layout={{
                  height: 400,
                  margin: { l: 50, r: 20, t: 10, b: 50 },
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "#f8fafd",
                  font: { color: "#013356" },
                  xaxis: { title: "Game Number", gridcolor: "#d0d8e4", color: "#013356" },
                  yaxis: { title: "Cumulative ROI", gridcolor: "#d0d8e4", color: "#013356" },
                  showlegend: false,
                }}
                style={{ width: "100%" }}
                config={{ displayModeBar: false }}
              />
            </div>
          )}

          {/* ── Season Breakdown ── */}
          <div className="profile-section">
            <h3 className="profile-section-title">📅 Season Breakdown</h3>
            <div className="profile-season-grid">
              {profile.best_season && (
                <div className="profile-season-highlight best">
                  <span className="profile-season-hl-badge">🏆 Best Season</span>
                  <span className="profile-season-hl-num">Season {profile.best_season.season}</span>
                  <span className="profile-season-hl-stat">${profile.best_season.roi.toFixed(2)} ROI · {profile.best_season.wins}W · ${profile.best_season.net.toLocaleString()}</span>
                </div>
              )}
              {profile.worst_season && profile.worst_season.season !== profile.best_season?.season && (
                <div className="profile-season-highlight worst">
                  <span className="profile-season-hl-badge">💔 Worst Season</span>
                  <span className="profile-season-hl-num">Season {profile.worst_season.season}</span>
                  <span className="profile-season-hl-stat">${profile.worst_season.roi.toFixed(2)} ROI · {profile.worst_season.wins}W · ${profile.worst_season.net.toLocaleString()}</span>
                </div>
              )}
            </div>
            <div className="table-wrap" style={{ marginTop: 12 }}>
              <table>
                <thead>
                  <tr>
                    <th>Season</th><th>Played</th><th>Wins</th><th>Win Rate</th>
                    <th>Costs</th><th>Winnings</th><th>Net</th><th>ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.season_breakdown.map((s) => (
                    <tr key={s.season}>
                      <td><strong>S{s.season}</strong></td>
                      <td>{s.played}</td>
                      <td>{s.wins}</td>
                      <td>{(s.win_rate * 100).toFixed(0)}%</td>
                      <td>${s.costs.toLocaleString()}</td>
                      <td>${s.winnings.toLocaleString()}</td>
                      <td className={s.net < 0 ? "negative" : ""}>${s.net.toLocaleString()}</td>
                      <td className={s.roi < 1 ? "negative" : ""}>${s.roi.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Head-to-Head ── */}
          <div className="profile-section">
            <h3 className="profile-section-title">⚔️ Head-to-Head Records</h3>
            <div className="profile-h2h-grid">
              {profile.head_to_head.map((h) => {
                const total = h.my_wins + h.opp_wins;
                const myPct = total > 0 ? Math.round((h.my_wins / total) * 100) : 50;
                const oppPct = 100 - myPct;
                const dominant = h.dominance >= 0.5;
                return (
                  <div key={h.opponent} className={`profile-h2h-card${dominant ? " dominant" : " underdog"}`}>
                    <div className="profile-h2h-header">
                      <span className="profile-h2h-vs">vs</span>
                      <span className="profile-h2h-opponent">{h.opponent}</span>
                      <span className="profile-h2h-games">{h.games_together} games</span>
                    </div>
                    <div className="profile-h2h-bar-row">
                      <span className="profile-h2h-count my">{h.my_wins}W</span>
                      <div className="profile-h2h-bar-track">
                        <div className="profile-h2h-bar-fill my" style={{ width: `${myPct}%` }} />
                        <div className="profile-h2h-bar-fill opp" style={{ width: `${oppPct}%` }} />
                      </div>
                      <span className="profile-h2h-count opp">{h.opp_wins}W</span>
                    </div>
                    <div className="profile-h2h-dominance">
                      {dominant ? "👆" : "👇"} {(h.dominance * 100).toFixed(0)}% dominance
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Login form (original) ────────────────────────────────── */

function LoginForm({ onLogin }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      await login(pw);
      onLogin();
    } catch (ex) {
      setErr(ex.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: 400 }}>
      <h2>Admin Login</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <label>Password
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} required />
        </label>
        {err && <p className="form-error">{err}</p>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Logging in…" : "Log In"}
        </button>
      </form>
    </div>
  );
}

/* ─── Player Management ─────────────────────────────────────── */

function PlayerManager({ players, onRefresh }) {
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [err, setErr] = useState("");

  const addPlayer = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await postJson("/api/players", { name, display_name: displayName || name });
      setName("");
      setDisplayName("");
      onRefresh();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  const toggleActive = async (p) => {
    try {
      await putJson(`/api/players/${p.player_id}`, { active: p.active ? 0 : 1 });
      onRefresh();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <div className="card">
      <h2>Player Management</h2>
      <form onSubmit={addPlayer} className="admin-form inline-form">
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Display Name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        <button type="submit" className="btn-primary">Add Player</button>
      </form>
      {err && <p className="form-error">{err}</p>}
      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table>
          <thead>
            <tr><th>ID</th><th>Name</th><th>Display</th><th>Active</th><th></th></tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.player_id}>
                <td>{p.player_id}</td>
                <td>{p.name}</td>
                <td>{p.display_name}</td>
                <td>{p.active ? "✓" : "✗"}</td>
                <td>
                  <button className="btn-sm" onClick={() => toggleActive(p)}>
                    {p.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Game Form (create / edit) ─────────────────────────────── */

function brisbaneToday() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Australia/Brisbane" });
}

function GameForm({ players, onSaved, editGame, onCancelEdit, metadata }) {
  const activePlayers = players.filter((p) => p.active);
  const defaultSeason = metadata?.latest_season ?? "";
  const defaultGameOverall = metadata?.next_game_overall ?? "";

  const [season, setSeason] = useState(editGame?.season ?? defaultSeason);
  const [gameDate, setGameDate] = useState(editGame?.game_date ?? brisbaneToday());
  const [gameNumber, setGameNumber] = useState(editGame?.game_number ?? 1);
  const [gameOverall, setGameOverall] = useState(editGame?.game_overall ?? defaultGameOverall);
  const [stake, setStake] = useState(editGame?.stake ?? 10);
  const [selectedPlayerIds, setSelectedPlayerIds] = useState(() => {
    if (editGame?.results) return editGame.results.map((r) => r.player_id);
    return [];
  });
  const [finishOrder, setFinishOrder] = useState(() => {
    if (editGame?.results) {
      const m = {};
      editGame.results.forEach((r) => { m[r.player_id] = r.finish_position; });
      return m;
    }
    return {};
  });
  const [err, setErr] = useState("");

  // Keep defaults in sync when metadata updates (e.g. after adding a game)
  useEffect(() => {
    if (!editGame) {
      setSeason(metadata?.latest_season ?? "");
      setGameOverall(metadata?.next_game_overall ?? "");
      setGameDate(brisbaneToday());
    }
  }, [metadata?.latest_season, metadata?.next_game_overall, editGame]);

  const togglePlayer = (pid) => {
    setSelectedPlayerIds((prev) => {
      if (prev.includes(pid)) {
        const next = prev.filter((id) => id !== pid);
        setFinishOrder((fo) => { const c = { ...fo }; delete c[pid]; return c; });
        return next;
      }
      return [...prev, pid];
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr("");

    const results = selectedPlayerIds.map((pid) => ({
      player_id: pid,
      finish_position: parseInt(finishOrder[pid]) || 0,
    }));

    // Derive winner from finish_position === 1
    const winnerResult = results.find((r) => r.finish_position === 1);
    const winnerPlayer = winnerResult ? players.find((p) => p.player_id === winnerResult.player_id) : null;

    const body = {
      season: parseInt(season),
      game_date: gameDate,
      game_number: parseInt(gameNumber),
      stake: parseInt(stake),
      winner: winnerPlayer?.name || null,
      is_placings: 1,
      results,
    };

    try {
      if (editGame) {
        await putJson(`/api/games/${editGame.game_overall}`, body);
      } else {
        await postJson("/api/games", body);
      }
      onSaved();
      if (!editGame) {
        // Reset form but keep season/date, game overall & game # will auto-update via metadata refresh
        setSelectedPlayerIds([]);
        setFinishOrder({});
        setGameNumber(1);
      }
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <div className="card">
      <h2>{editGame ? `Edit Game #${editGame.game_overall}` : "Add Game Result"}</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <div className="form-grid">
          <label>Game Overall
            <input type="number" value={gameOverall} readOnly={!editGame} onChange={(e) => setGameOverall(e.target.value)} required />
          </label>
          <label>Season
            <input type="number" value={season} onChange={(e) => setSeason(e.target.value)} required />
          </label>
          <label>Date
            <input type="date" value={gameDate} onChange={(e) => setGameDate(e.target.value)} required />
          </label>
          <label>Game #
            <input type="number" value={gameNumber} onChange={(e) => setGameNumber(e.target.value)} min={1} required />
          </label>
          <label>Stake ($)
            <input type="number" value={stake} onChange={(e) => setStake(e.target.value)} required />
          </label>
        </div>

        <fieldset className="player-select-fieldset">
          <legend>Select Players &amp; Finish Order</legend>
          <div className="player-chips">
            {activePlayers.map((p) => {
              const selected = selectedPlayerIds.includes(p.player_id);
              return (
                <button
                  key={p.player_id}
                  type="button"
                  className={`player-chip${selected ? " selected" : ""}`}
                  onClick={() => togglePlayer(p.player_id)}
                >
                  {p.display_name}
                </button>
              );
            })}
          </div>
          {selectedPlayerIds.length > 0 && (
            <div className="finish-order-list">
              {selectedPlayerIds.map((pid) => {
                const p = players.find((x) => x.player_id === pid);
                return (
                  <div key={pid} className="finish-order-row">
                    <span>{p?.display_name}</span>
                    <input
                      type="number"
                      min={1}
                      placeholder="Position"
                      value={finishOrder[pid] || ""}
                      onChange={(e) => setFinishOrder((fo) => ({ ...fo, [pid]: e.target.value }))}
                      required
                    />
                  </div>
                );
              })}
            </div>
          )}
        </fieldset>

        {err && <p className="form-error">{err}</p>}
        <div className="form-actions">
          <button type="submit" className="btn-primary">
            {editGame ? "Update Game" : "Add Game"}
          </button>
          {editGame && (
            <button type="button" className="btn-secondary" onClick={onCancelEdit}>Cancel</button>
          )}
        </div>
      </form>
    </div>
  );
}

/* ─── Game list with edit/delete ────────────────────────────── */

function GameList({ games, onEdit, onDeleted }) {
  const [err, setErr] = useState("");

  const handleDelete = async (id) => {
    if (!window.confirm(`Delete game #${id}?`)) return;
    try {
      await deleteJson(`/api/games/${id}`);
      onDeleted();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  if (!games || games.length === 0) return <p className="muted">No games.</p>;

  return (
    <div className="card">
      <h2>Manage Games</h2>
      {err && <p className="form-error">{err}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Season</th><th>Date</th><th>Game</th><th>Stake</th><th>Winner</th><th></th>
            </tr>
          </thead>
          <tbody>
            {[...games].reverse().map((g) => (
              <tr key={g.game_overall}>
                <td>{g.game_overall}</td>
                <td>{g.season}</td>
                <td>{g.game_date}</td>
                <td>{g.game_number}</td>
                <td>${g.stake}</td>
                <td>{g.winner}</td>
                <td className="action-cell">
                  <button className="btn-sm" onClick={() => onEdit(g)}>Edit</button>
                  <button className="btn-sm btn-danger" onClick={() => handleDelete(g.game_overall)}>Del</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Admin Tab ─────────────────────────────────────────────── */

function AdminTab({ games, refreshData, metadata }) {
  const [authed, setAuthed] = useState(isLoggedIn());
  const [players, setPlayers] = useState([]);
  const [editGame, setEditGame] = useState(null);

  const loadPlayers = useCallback(() => {
    fetchJson("/api/players").then(setPlayers).catch(() => {});
  }, []);

  useEffect(() => {
    if (authed) loadPlayers();
  }, [authed, loadPlayers]);

  const handleLogout = () => {
    clearToken();
    setAuthed(false);
  };

  if (!authed) {
    return <LoginForm onLogin={() => setAuthed(true)} />;
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <span>Logged in as admin</span>
        <button className="btn-sm btn-secondary" onClick={handleLogout}>Logout</button>
      </div>
      <div className="dash-grid">
        <GameForm
          players={players}
          editGame={editGame}
          onSaved={() => { refreshData(); setEditGame(null); }}
          onCancelEdit={() => setEditGame(null)}
          metadata={metadata}
        />
        <PlayerManager players={players} onRefresh={loadPlayers} />
      </div>
      <GameList
        games={games}
        onEdit={(g) => setEditGame(g)}
        onDeleted={refreshData}
      />
    </div>
  );
}

/* ─── Main app ──────────────────────────────────────────────── */

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [metadata, setMetadata] = useState({ players: [], seasons: [], playerList: [] });
  const [selectedSeasons, setSelectedSeasons] = useState([]);
  const [summary, setSummary] = useState([]);
  const [streaks, setStreaks] = useState([]);
  const [currentStreaks, setCurrentStreaks] = useState([]);
  const [roiSeries, setRoiSeries] = useState([]);
  const [games, setGames] = useState([]);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    Promise.all([
      fetchJson("/api/metadata"),
      fetchJson("/api/players"),
    ])
      .then(([meta, playerList]) => {
        setMetadata({ ...meta, playerList });
        setSelectedSeasons(meta.seasons || []);
      })
      .catch((err) => setError(err.message));
  }, [refreshKey]);

  const seasonParam = useMemo(
    () => buildSeasonParam(selectedSeasons),
    [selectedSeasons]
  );

  useEffect(() => {
    if (selectedSeasons.length === 0) return;
    const longestParam = seasonParam ? `${seasonParam}&n=10` : "?n=10";
    const currentParam = seasonParam
      ? `${seasonParam}&n=999999&active=true`
      : "?n=999999&active=true";

    Promise.all([
      fetchJson(`/api/player-summary${seasonParam}`),
      fetchJson(`/api/losing-streaks${longestParam}`),
      fetchJson(`/api/losing-streaks${currentParam}`),
      fetchJson(`/api/roi-series${seasonParam}`),
      fetchJson(`/api/games${seasonParam}`),
    ])
      .then(([summaryData, streakData, currentData, roiData, gamesData]) => {
        setSummary(summaryData);
        setStreaks(streakData);
        setCurrentStreaks(currentData);
        setRoiSeries(roiData);
        setGames(gamesData);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, [seasonParam, selectedSeasons.length, refreshKey]);

  const refreshData = useCallback(() => setRefreshKey((k) => k + 1), []);

  /* ── derived plot data ────────────────── */

  const roiPlotData = useMemo(() => {
    const grouped = {};
    roiSeries.forEach((r) => {
      if (!grouped[r.player]) grouped[r.player] = { x: [], y: [] };
      grouped[r.player].x.push(r.game_overall);
      grouped[r.player].y.push(r.all_time_return);
    });
    return Object.entries(grouped).map(([player, s]) => ({
      type: "scatter",
      mode: "lines+markers",
      name: player,
      x: s.x,
      y: s.y,
    }));
  }, [roiSeries]);


  /* ── render ───────────────────────────── */

  return (
    <div className="layout">
      {/* ── Sidebar ─────────────────────── */}
      <aside className="sidebar">
        <img src="/logo2.jpeg" alt="PokerLog" className="sidebar-logo" />

        <label htmlFor="season-select" className="sidebar-label">
          Season
        </label>
        <select
          id="season-select"
          multiple
          value={selectedSeasons.map(String)}
          onChange={(e) => {
            const vals = Array.from(e.target.selectedOptions).map((o) =>
              Number(o.value)
            );
            setSelectedSeasons(vals);
          }}
        >
          {metadata.seasons.map((s) => (
            <option key={s} value={s}>
              Season {s}
            </option>
          ))}
        </select>
      </aside>

      {/* ── Main content ────────────────── */}
      <main className="main">
        <nav className="tab-bar">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`tab-btn${tab === t.key ? " active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {error && <div className="error">{error}</div>}

        <div className="tab-content">
          {tab === "dashboard" && (
            <DashboardTab summary={summary} roiPlotData={roiPlotData} />
          )}
          {tab === "profile" && (
            <PlayerProfileTab players={metadata.playerList || []} />
          )}
          {tab === "odds" && <OddsTab />}
          {tab === "streaks" && (
            <StreaksTab
              streaks={streaks}
              currentStreaks={currentStreaks}
            />
          )}
          {tab === "history" && <HistoryTab games={games} />}
          {tab === "admin" && <AdminTab games={games} refreshData={refreshData} metadata={metadata} />}
        </div>
      </main>
    </div>
  );
}
