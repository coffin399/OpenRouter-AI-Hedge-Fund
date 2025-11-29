import React, { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

type TabKey = "monitor" | "voting" | "history" | "performance";

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("monitor");
  const [health, setHealth] = useState<string>("unknown");
  const [symbol, setSymbol] = useState<string>("AAPL");
  const [analyzeResult, setAnalyzeResult] = useState<any | null>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [mode, setMode] = useState<string>("virtual");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status ?? "ok"))
      .catch(() => setHealth("error"));
    fetch(`${API_URL}/config/trading_mode`)
      .then((r) => r.json())
      .then((d) => setMode(d.mode ?? "virtual"))
      .catch(() => undefined);
  }, []);

  const handleAnalyze = async () => {
    const res = await fetch(`${API_URL}/analyze/${encodeURIComponent(symbol)}`, {
      method: "POST"
    });
    const data = await res.json();
    setAnalyzeResult(data);
  };

  const handleTrade = async () => {
    const res = await fetch(`${API_URL}/trade/${encodeURIComponent(symbol)}`, {
      method: "POST"
    });
    const data = await res.json();
    setAnalyzeResult(data.decision ?? null);
    await loadTrades();
  };

  const loadTrades = async () => {
    const res = await fetch(`${API_URL}/trades/recent`);
    const data = await res.json();
    setTrades(data);
  };

  const handleModeChange = async (newMode: string) => {
    setMode(newMode);
    try {
      await fetch(`${API_URL}/config/trading_mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode })
      });
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (activeTab === "history") {
      loadTrades();
    }
  }, [activeTab]);

  const renderDecisionSummary = () => {
    if (!analyzeResult) return <p>No decision yet.</p>;
    const d = analyzeResult;
    return (
      <div>
        <p>Final decision: {d.final_decision}</p>
        <p>Aggregate confidence: {d.aggregate_confidence}</p>
        <p>Target price: {d.target_price ?? "-"}</p>
        <p>Stop loss: {d.stop_loss ?? "-"}</p>
      </div>
    );
  };

  const renderVotes = () => {
    if (!analyzeResult) return <p>No votes yet.</p>;
    const nodes = analyzeResult.node_results ?? [];
    return (
      <div style={{ display: "grid", gap: 12 }}>
        {nodes.map((n: any) => (
          <div
            key={n.node_id}
            style={{ border: "1px solid #ccc", borderRadius: 8, padding: 12 }}
          >
            <strong>{n.node_id}</strong>
            <p>Model: {n.model}</p>
            <p>Recommendation: {n.recommendation}</p>
            <p>Confidence: {n.confidence}</p>
            <p>Reasoning: {n.reasoning}</p>
          </div>
        ))}
      </div>
    );
  };

  const renderTrades = () => {
    if (!trades.length) return <p>No trades yet.</p>;
    return (
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Time</th>
            <th>Symbol</th>
            <th>Decision</th>
            <th>Entry</th>
            <th>P/L</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id}>
              <td>{t.id}</td>
              <td>{t.timestamp}</td>
              <td>{t.symbol}</td>
              <td>{t.decision}</td>
              <td>{t.entry_price}</td>
              <td>{t.profit_loss}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  const renderPerformance = () => {
    if (!trades.length) return <p>No data yet.</p>;
    const profits = trades.map((t) => t.profit_loss || 0);
    const total = profits.reduce((a, b) => a + b, 0);
    return <p>Total P/L (sum of logged trades): {total}</p>;
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 20 }}>
      <header style={{ marginBottom: 16 }}>
        <h1>AI Hedge Fund Dashboard</h1>
        <p>Backend health: {health}</p>
        <div style={{ marginTop: 8 }}>
          <label>
            Trading mode:
            <select
              value={mode}
              onChange={(e) => handleModeChange(e.target.value)}
              style={{ marginLeft: 8 }}
            >
              <option value="virtual">virtual</option>
              <option value="paper">paper</option>
              <option value="live">live</option>
            </select>
          </label>
        </div>
      </header>

      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => setActiveTab("monitor")}>Real-time Monitor</button>
        <button onClick={() => setActiveTab("voting")}>AI Voting</button>
        <button onClick={() => setActiveTab("history")}>Trade History</button>
        <button onClick={() => setActiveTab("performance")}>Performance</button>
      </nav>

      <section style={{ marginBottom: 16 }}>
        <label>
          Symbol:
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            style={{ marginLeft: 8 }}
          />
        </label>
        <button onClick={handleAnalyze} style={{ marginLeft: 8 }}>
          Analyze
        </button>
        <button onClick={handleTrade} style={{ marginLeft: 8 }}>
          {`Trade (${mode})`}
        </button>
      </section>

      {activeTab === "monitor" && (
        <div>
          <h2>Real-time Monitor</h2>
          {renderDecisionSummary()}
        </div>
      )}

      {activeTab === "voting" && (
        <div>
          <h2>AI Voting</h2>
          {renderVotes()}
        </div>
      )}

      {activeTab === "history" && (
        <div>
          <h2>Trade History</h2>
          {renderTrades()}
        </div>
      )}

      {activeTab === "performance" && (
        <div>
          <h2>Performance</h2>
          {renderPerformance()}
        </div>
      )}
    </div>
  );
}

export default App;
