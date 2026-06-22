import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [today, setToday] = useState(null);
  const [text, setText] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadToday() {
    const res = await fetch(`${API_BASE_URL}/today`);
    setToday(await res.json());
  }

  useEffect(() => {
    loadToday().catch(() => setToday(null));
  }, []);

  async function sendMessage(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setResponse("");
    try {
      const res = await fetch(`${API_BASE_URL}/assistant/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: "web" }),
      });
      const data = await res.json();
      setResponse(data.response);
      setText("");
      await loadToday();
    } catch {
      setResponse("Could not reach the local assistant API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Private local assistant</p>
          <h1>Local LLM Jarvis</h1>
          <p className="lede">
            Capture tasks, reminders, water, and meals. The Android app will own the daily UX;
            this web surface is the companion workspace.
          </p>
        </div>
        <div className="status">API: {today ? "online" : "checking"}</div>
      </section>

      <section className="grid">
        <div className="panel focus">
          <h2>Quick Capture</h2>
          <form onSubmit={sendMessage}>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Try: Add a task to submit the insurance form tomorrow morning"
            />
            <button disabled={loading}>{loading ? "Thinking..." : "Send"}</button>
          </form>
          {response && <p className="response">{response}</p>}
        </div>

        <div className="panel">
          <h2>Today</h2>
          <p className="suggestion">{today?.suggestion || "No Today view loaded yet."}</p>

          <h3>Top priorities</h3>
          <ul>
            {(today?.top_priorities || []).map((task) => (
              <li key={task.id}>
                <span>{task.title}</span>
                <small>{Math.round(task.priority_score)} priority</small>
              </li>
            ))}
          </ul>

          <h3>Upcoming reminders</h3>
          <ul>
            {(today?.upcoming_reminders || []).map((reminder) => (
              <li key={reminder.id}>
                <span>{reminder.title}</span>
                <small>{reminder.intensity}</small>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

