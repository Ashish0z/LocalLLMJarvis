import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || "";

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(
    () => localStorage.getItem("jarvis_api_base_url") || API_BASE_URL
  );
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("jarvis_api_key") || DEFAULT_API_KEY
  );
  const [today, setToday] = useState(null);
  const [text, setText] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [documentQuestion, setDocumentQuestion] = useState("");
  const [documentAnswer, setDocumentAnswer] = useState("");

  function headers(extra = {}) {
    return {
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...extra,
    };
  }

  async function loadToday() {
    const res = await fetch(`${apiBaseUrl}/today`, { headers: headers() });
    if (!res.ok) throw new Error(`Today failed: ${res.status}`);
    setToday(await res.json());
  }

  async function loadDocuments() {
    const res = await fetch(`${apiBaseUrl}/documents`, { headers: headers() });
    if (!res.ok) throw new Error(`Documents failed: ${res.status}`);
    const data = await res.json();
    setDocuments(data);
    if (!selectedDocumentId && data.length > 0) {
      setSelectedDocumentId(data[0].id);
    }
  }

  useEffect(() => {
    localStorage.setItem("jarvis_api_base_url", apiBaseUrl);
    localStorage.setItem("jarvis_api_key", apiKey);
    Promise.all([loadToday(), loadDocuments()]).catch((err) => {
      setError(err.message);
    });
  }, [apiBaseUrl, apiKey]);

  async function sendMessage(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setResponse("");
    setError("");
    try {
      const res = await fetch(`${apiBaseUrl}/assistant/message`, {
        method: "POST",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ text, source: "web" }),
      });
      if (!res.ok) throw new Error(`Capture failed: ${res.status}`);
      const data = await res.json();
      setResponse(data.response);
      setText("");
      await loadToday();
    } catch (err) {
      setError(err.message || "Could not reach the local assistant API.");
    } finally {
      setLoading(false);
    }
  }

  async function uploadDocument(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${apiBaseUrl}/documents`, {
        method: "POST",
        headers: headers(),
        body: form,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const document = await res.json();
      await loadDocuments();
      setSelectedDocumentId(document.id);
    } catch (err) {
      setError(err.message || "Could not upload document.");
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  async function askDocument(event) {
    event.preventDefault();
    if (!selectedDocumentId || !documentQuestion.trim()) return;
    setLoading(true);
    setDocumentAnswer("");
    setError("");
    try {
      const res = await fetch(`${apiBaseUrl}/documents/${selectedDocumentId}/ask`, {
        method: "POST",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ question: documentQuestion }),
      });
      if (!res.ok) throw new Error(`Document question failed: ${res.status}`);
      const data = await res.json();
      setDocumentAnswer(data.answer);
    } catch (err) {
      setError(err.message || "Could not ask the document.");
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
            Capture tasks, reminders, water, meals, and document questions. Android owns the
            daily UX; this web surface is the companion workspace.
          </p>
        </div>
        <div className="status">API: {today ? "online" : "checking"}</div>
      </section>

      <section className="settings">
        <label>
          API URL
          <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
        </label>
        <label>
          API key
          <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
        </label>
      </section>

      {error && <p className="error">{error}</p>}

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

      <section className="panel documents">
        <div className="panel-header">
          <h2>Documents</h2>
          <label className="upload">
            Upload file
            <input
              type="file"
              accept=".txt,.md,.markdown,.csv,.json,.log,text/plain,text/markdown,text/csv,application/json"
              onChange={uploadDocument}
            />
          </label>
        </div>

        {documents.length === 0 ? (
          <p className="muted">Upload a text, markdown, csv, json, or log file to ask questions about it.</p>
        ) : (
          <div className="document-grid">
            <ul>
              {documents.map((document) => (
                <li key={document.id}>
                  <button
                    className={document.id === selectedDocumentId ? "link selected" : "link"}
                    onClick={() => setSelectedDocumentId(document.id)}
                  >
                    {document.filename}
                  </button>
                  <small>{document.summary || "No summary"}</small>
                </li>
              ))}
            </ul>

            <form onSubmit={askDocument}>
              <textarea
                value={documentQuestion}
                onChange={(event) => setDocumentQuestion(event.target.value)}
                placeholder="Ask a question about the selected document"
              />
              <button disabled={loading || !selectedDocumentId || !documentQuestion.trim()}>
                Ask document
              </button>
              {documentAnswer && <p className="response">{documentAnswer}</p>}
            </form>
          </div>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
