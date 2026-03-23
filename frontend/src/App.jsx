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
  { key: "odds", label: "Next Game Odds" },
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
    <>
      <div className="dash-grid">
        <div className="card">
          <h2>Performance Summary</h2>
          <DataTable rows={summary} />
        </div>
        <div className="card metric-card">
          <h2>Metric Definitions</h2>
          <dl className="metric-list">
            {METRIC_DEFS.map(([term, def]) => (
              <div key={term} className="metric-item">
                <dt>{term}</dt>
                <dd>{def}</dd>
              </div>
            ))}
          </dl>
          <p className="muted note">
            Places only tracked since game 94 (early season 2). Stats filtered by
            season. Overall winner determined by Return Rate within a season.
          </p>
        </div>
      </div>
      <div className="card full-width">
        <h2>Return on Investment</h2>
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
    </>
  );
}

function StreaksTab({ streakPlotData, currentStreakPlotData }) {
  return (
    <div className="dash-grid">
      <div className="card">
        <h2>Longest Losing Streaks</h2>
        <Plot
          data={streakPlotData}
          layout={{
            height: 380,
            margin: { l: 50, r: 20, t: 20, b: 50 },
            xaxis: { title: "Consecutive Losing Games", gridcolor: "#d0d8e4", color: "#013356" },
            yaxis: { autorange: "reversed", showticklabels: false },
            paper_bgcolor: "transparent",
            plot_bgcolor: "#f8fafd",
            font: { color: "#013356" },
          }}
          style={{ width: "100%" }}
          config={{ displayModeBar: false }}
        />
      </div>
      <div className="card">
        <h2>Current Losing Streaks</h2>
        <Plot
          data={currentStreakPlotData}
          layout={{
            height: 380,
            margin: { l: 50, r: 20, t: 20, b: 50 },
            xaxis: { title: "Consecutive Losing Games", gridcolor: "#d0d8e4", color: "#013356" },
            yaxis: { autorange: "reversed", showticklabels: false },
            paper_bgcolor: "transparent",
            plot_bgcolor: "#f8fafd",
            font: { color: "#013356" },
          }}
          style={{ width: "100%" }}
          config={{ displayModeBar: false }}
        />
      </div>
    </div>
  );
}

function HistoryTab({ games }) {
  return (
    <div className="card full-width">
      <h2>Game History</h2>
      <DataTable rows={games} />
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
    </div>
  );
}

/* ─── Login form ────────────────────────────────────────────── */

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
  const [metadata, setMetadata] = useState({ players: [], seasons: [] });
  const [selectedSeasons, setSelectedSeasons] = useState([]);
  const [summary, setSummary] = useState([]);
  const [streaks, setStreaks] = useState([]);
  const [currentStreaks, setCurrentStreaks] = useState([]);
  const [roiSeries, setRoiSeries] = useState([]);
  const [games, setGames] = useState([]);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    fetchJson("/api/metadata")
      .then((data) => {
        setMetadata(data);
        setSelectedSeasons(data.seasons || []);
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

  const streakPlotData = useMemo(
    () => [
      {
        type: "bar",
        orientation: "h",
        x: streaks.map((r) => r.streak_length),
        y: streaks.map((r) => r.streak_rank),
        text: streaks.map((r) => r.streak_name),
        hovertext: streaks.map((r) => r.streak_name),
        hoverinfo: "text",
        marker: { color: "#e74c3c" },
      },
    ],
    [streaks]
  );

  const currentStreakPlotData = useMemo(
    () => [
      {
        type: "bar",
        orientation: "h",
        x: currentStreaks.map((r) => r.streak_length),
        y: currentStreaks.map((r) => r.streak_rank),
        text: currentStreaks.map((r) => r.streak_name),
        hovertext: currentStreaks.map((r) => r.streak_name),
        hoverinfo: "text",
        marker: { color: "#e67e22" },
      },
    ],
    [currentStreaks]
  );

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
          {tab === "odds" && <OddsTab />}
          {tab === "streaks" && (
            <StreaksTab
              streakPlotData={streakPlotData}
              currentStreakPlotData={currentStreakPlotData}
            />
          )}
          {tab === "history" && <HistoryTab games={games} />}
          {tab === "admin" && <AdminTab games={games} refreshData={refreshData} metadata={metadata} />}
        </div>
      </main>
    </div>
  );
}
