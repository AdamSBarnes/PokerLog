import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { buildSeasonParam, fetchJson } from "./api.js";

const TABS = [
  { key: "dashboard", label: "Player Summary" },
  { key: "streaks", label: "Losing Streaks" },
  { key: "history", label: "Game History" },
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

  useEffect(() => {
    fetchJson("/api/metadata")
      .then((data) => {
        setMetadata(data);
        setSelectedSeasons(data.seasons || []);
      })
      .catch((err) => setError(err.message));
  }, []);

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
  }, [seasonParam, selectedSeasons.length]);

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
          {tab === "streaks" && (
            <StreaksTab
              streakPlotData={streakPlotData}
              currentStreakPlotData={currentStreakPlotData}
            />
          )}
          {tab === "history" && <HistoryTab games={games} />}
        </div>
      </main>
    </div>
  );
}
