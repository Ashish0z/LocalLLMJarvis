import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || "";
const UNDO_DELAY_MS = 5000;

/**
 * Convert an ISO 8601 datetime string (possibly with timezone) to the
 * "YYYY-MM-DDTHH:MM" format required by <input type="datetime-local">.
 * The value is expressed in the user's local timezone.
 */
function toDatetimeLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/** Fetch JSON with structured error detail parsing from FastAPI responses. */
async function fetchJSON(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (networkErr) {
    throw new Error(
      `Cannot reach API — check the service is running. (${networkErr.message})`
    );
  }
  if (res.status === 204) return null;
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) {
        detail =
          typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {}
    if (res.status === 401 || res.status === 403) {
      detail += " — check your API key in Settings";
    } else if (res.status === 404) {
      detail += " — the item may have already been deleted";
    } else if (res.status >= 500) {
      detail += " — server error, try again shortly";
    }
    throw new Error(detail);
  }
  return res.json();
}

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(
    () => localStorage.getItem("jarvis_api_base_url") || API_BASE_URL
  );
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("jarvis_api_key") || DEFAULT_API_KEY
  );

  const [today, setToday] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [documents, setDocuments] = useState([]);

  const [text, setText] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [documentQuestion, setDocumentQuestion] = useState("");
  const [documentAnswer, setDocumentAnswer] = useState("");
  const [contextChunks, setContextChunks] = useState([]);
  const [showContext, setShowContext] = useState(false);

  const [editingTask, setEditingTask] = useState(null);
  const [editingReminder, setEditingReminder] = useState(null);

  const [confirmDeleteDocId, setConfirmDeleteDocId] = useState(null);
  const [undoDoc, setUndoDoc] = useState(null);
  const undoTimerRef = useRef(null);

  function headers(extra = {}) {
    return {
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...extra,
    };
  }

  async function loadAll() {
    const [todayRes, tasksRes, remindersRes, docsRes] = await Promise.allSettled([
      fetchJSON(`${apiBaseUrl}/today`, { headers: headers() }),
      fetchJSON(`${apiBaseUrl}/tasks?status=pending`, { headers: headers() }),
      fetchJSON(`${apiBaseUrl}/reminders?status=active`, { headers: headers() }),
      fetchJSON(`${apiBaseUrl}/documents`, { headers: headers() }),
    ]);

    if (todayRes.status === "fulfilled") setToday(todayRes.value);
    if (tasksRes.status === "fulfilled") setTasks(tasksRes.value ?? []);
    if (remindersRes.status === "fulfilled") setReminders(remindersRes.value ?? []);
    if (docsRes.status === "fulfilled") {
      const data = docsRes.value ?? [];
      setDocuments(data);
      setSelectedDocumentId((prev) => prev || (data.length > 0 ? data[0].id : ""));
    }

    const firstError = [todayRes, tasksRes, remindersRes, docsRes].find(
      (r) => r.status === "rejected"
    );
    if (firstError) setError(firstError.reason.message);
  }

  useEffect(() => {
    localStorage.setItem("jarvis_api_base_url", apiBaseUrl);
    localStorage.setItem("jarvis_api_key", apiKey);
    void loadAll();
  }, [apiBaseUrl, apiKey]);

  async function sendMessage(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setResponse("");
    setError("");
    try {
      const data = await fetchJSON(`${apiBaseUrl}/assistant/message`, {
        method: "POST",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ text, source: "web" }),
      });
      setResponse(data.response);
      setText("");
      await loadAll();
    } catch (err) {
      setError(err.message || "Could not reach the local assistant API.");
    } finally {
      setLoading(false);
    }
  }

  async function completeTask(id) {
    setError("");
    try {
      await fetchJSON(`${apiBaseUrl}/tasks/${id}`, {
        method: "PATCH",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ status: "done" }),
      });
      setTasks((prev) => prev.filter((t) => t.id !== id));
      setToday((prev) =>
        prev
          ? { ...prev, top_priorities: prev.top_priorities.filter((t) => t.id !== id) }
          : prev
      );
    } catch (err) {
      setError(err.message || "Could not complete task.");
    }
  }

  async function saveTask(id, patch) {
    setError("");
    try {
      const updated = await fetchJSON(`${apiBaseUrl}/tasks/${id}`, {
        method: "PATCH",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(patch),
      });
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
      setEditingTask(null);
    } catch (err) {
      setError(err.message || "Could not update task.");
    }
  }

  async function completeReminder(id) {
    setError("");
    try {
      await fetchJSON(`${apiBaseUrl}/reminders/${id}`, {
        method: "PATCH",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ status: "done" }),
      });
      setReminders((prev) => prev.filter((r) => r.id !== id));
      setToday((prev) =>
        prev
          ? {
              ...prev,
              upcoming_reminders: prev.upcoming_reminders.filter((r) => r.id !== id),
            }
          : prev
      );
    } catch (err) {
      setError(err.message || "Could not complete reminder.");
    }
  }

  async function saveReminder(id, patch) {
    setError("");
    try {
      const updated = await fetchJSON(`${apiBaseUrl}/reminders/${id}`, {
        method: "PATCH",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(patch),
      });
      setReminders((prev) => prev.map((r) => (r.id === id ? updated : r)));
      setEditingReminder(null);
    } catch (err) {
      setError(err.message || "Could not update reminder.");
    }
  }

  function initiateDeleteDocument(id) {
    setConfirmDeleteDocId(id);
  }

  function cancelDeleteDocument() {
    setConfirmDeleteDocId(null);
  }

  function confirmDeleteDocument(id) {
    const idx = documents.findIndex((d) => d.id === id);
    const doc = documents[idx];
    // Compute remaining before any state updates to avoid stale-closure issues.
    const remaining = documents.filter((d) => d.id !== id);
    setConfirmDeleteDocId(null);
    setDocuments(remaining);
    if (selectedDocumentId === id) {
      setSelectedDocumentId(remaining.length > 0 ? remaining[0].id : "");
    }
    setUndoDoc({ id, doc, idx });
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    undoTimerRef.current = setTimeout(async () => {
      setUndoDoc(null);
      try {
        await fetchJSON(`${apiBaseUrl}/documents/${id}`, {
          method: "DELETE",
          headers: headers(),
        });
      } catch (err) {
        setError(err.message || "Could not delete document.");
        if (doc) restoreDocumentAt(doc, idx);
      }
    }, UNDO_DELAY_MS);
  }

  function restoreDocumentAt(doc, idx) {
    setDocuments((prev) => {
      const next = [...prev];
      // Clamp the index in case other items were added/removed in the interim.
      next.splice(Math.min(idx, next.length), 0, doc);
      return next;
    });
  }

  function undoDeleteDocument() {
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    if (undoDoc?.doc) restoreDocumentAt(undoDoc.doc, undoDoc.idx);
    setUndoDoc(null);
  }

  async function uploadDocument(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const document = await fetchJSON(`${apiBaseUrl}/documents`, {
        method: "POST",
        headers: headers(),
        body: form,
      });
      setDocuments((prev) => [document, ...prev]);
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
    setContextChunks([]);
    setShowContext(false);
    setError("");
    try {
      const data = await fetchJSON(`${apiBaseUrl}/documents/${selectedDocumentId}/ask`, {
        method: "POST",
        headers: headers({ "Content-Type": "application/json" }),
        body: JSON.stringify({ question: documentQuestion }),
      });
      setDocumentAnswer(data.answer);
      setContextChunks(data.context_chunks ?? []);
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

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="link error-dismiss" onClick={() => setError("")} aria-label="Dismiss error">
            ✕
          </button>
        </div>
      )}

      {undoDoc && (
        <div className="undo-banner" role="status">
          <span>Document deleted.</span>
          <button className="link undo-action" onClick={undoDeleteDocument}>
            Undo
          </button>
        </div>
      )}

      <section className="grid">
        <div className="panel focus">
          <h2>Quick Capture</h2>
          <form onSubmit={sendMessage}>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Try: Add a task to submit the insurance form tomorrow morning"
            />
            <button disabled={loading}>{loading ? "Thinking…" : "Send"}</button>
          </form>
          {response && <p className="response">{response}</p>}
        </div>

        <div className="panel">
          <h2>Today</h2>
          <p className="suggestion">{today?.suggestion || "No Today view loaded yet."}</p>

          <h3>Top priorities</h3>
          {(today?.top_priorities ?? []).length === 0 ? (
            <p className="muted">No pending tasks.</p>
          ) : (
            <ul>
              {(today?.top_priorities ?? []).map((task) => (
                <li key={task.id} className="action-row">
                  <span className="row-title">{task.title}</span>
                  <div className="row-actions">
                    <small>{Math.round(task.priority_score)} pts</small>
                    <button
                      className="btn-sm"
                      onClick={() => completeTask(task.id)}
                      title="Mark done"
                    >
                      ✓
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <h3>Upcoming reminders</h3>
          {(today?.upcoming_reminders ?? []).length === 0 ? (
            <p className="muted">No upcoming reminders.</p>
          ) : (
            <ul>
              {(today?.upcoming_reminders ?? []).map((reminder) => (
                <li key={reminder.id} className="action-row">
                  <span className="row-title">{reminder.title}</span>
                  <div className="row-actions">
                    <small>{reminder.intensity}</small>
                    <button
                      className="btn-sm"
                      onClick={() => completeReminder(reminder.id)}
                      title="Mark done"
                    >
                      ✓
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="panel entity-section">
        <h2>Tasks</h2>
        {tasks.length === 0 ? (
          <p className="muted">No pending tasks. Use Quick Capture to add one.</p>
        ) : (
          <ul>
            {tasks.map((task) =>
              editingTask?.id === task.id ? (
                <li key={task.id}>
                  <TaskEditForm
                    task={editingTask}
                    onChange={setEditingTask}
                    onSave={() => {
                      const { id, title, notes, due_at } = editingTask;
                      const patch = { title };
                      if (notes !== undefined) patch.notes = notes || null;
                      patch.due_at = due_at || null;
                      saveTask(id, patch);
                    }}
                    onCancel={() => setEditingTask(null)}
                  />
                </li>
              ) : (
                <li key={task.id} className="action-row">
                  <div className="row-info">
                    <span className="row-title">{task.title}</span>
                    {task.due_at && (
                      <small>{new Date(task.due_at).toLocaleString()}</small>
                    )}
                    {task.notes && <small className="row-notes">{task.notes}</small>}
                  </div>
                  <div className="row-actions">
                    <small>{Math.round(task.priority_score)} pts</small>
                    <button
                      className="btn-sm btn-secondary"
                      title="Edit task"
                      onClick={() =>
                        setEditingTask({
                          id: task.id,
                          title: task.title,
                          notes: task.notes ?? "",
                          due_at: toDatetimeLocal(task.due_at),
                        })
                      }
                    >
                      ✎
                    </button>
                    <button
                      className="btn-sm"
                      title="Mark done"
                      onClick={() => completeTask(task.id)}
                    >
                      ✓
                    </button>
                  </div>
                </li>
              )
            )}
          </ul>
        )}
      </section>

      <section className="panel entity-section">
        <h2>Reminders</h2>
        {reminders.length === 0 ? (
          <p className="muted">No active reminders. Use Quick Capture to add one.</p>
        ) : (
          <ul>
            {reminders.map((reminder) =>
              editingReminder?.id === reminder.id ? (
                <li key={reminder.id}>
                  <ReminderEditForm
                    reminder={editingReminder}
                    onChange={setEditingReminder}
                    onSave={() => {
                      const { id, title, remind_at, intensity } = editingReminder;
                      const patch = { title, intensity, remind_at: remind_at || null };
                      saveReminder(id, patch);
                    }}
                    onCancel={() => setEditingReminder(null)}
                  />
                </li>
              ) : (
                <li key={reminder.id} className="action-row">
                  <div className="row-info">
                    <span className="row-title">{reminder.title}</span>
                    {reminder.remind_at && (
                      <small>{new Date(reminder.remind_at).toLocaleString()}</small>
                    )}
                  </div>
                  <div className="row-actions">
                    <small>{reminder.intensity}</small>
                    <button
                      className="btn-sm btn-secondary"
                      title="Edit reminder"
                      onClick={() =>
                        setEditingReminder({
                          id: reminder.id,
                          title: reminder.title,
                          remind_at: toDatetimeLocal(reminder.remind_at),
                          intensity: reminder.intensity,
                        })
                      }
                    >
                      ✎
                    </button>
                    <button
                      className="btn-sm"
                      title="Mark done"
                      onClick={() => completeReminder(reminder.id)}
                    >
                      ✓
                    </button>
                  </div>
                </li>
              )
            )}
          </ul>
        )}
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

        {documents.length === 0 && !undoDoc ? (
          <p className="muted">
            Upload a text, markdown, csv, json, or log file to ask questions about it.
          </p>
        ) : (
          <div className="document-grid">
            <ul>
              {documents.map((doc) => (
                <li key={doc.id} className="doc-item">
                  {confirmDeleteDocId === doc.id ? (
                    <div className="confirm-delete">
                      <span>Delete &ldquo;{doc.filename}&rdquo;?</span>
                      <div className="row-actions">
                        <button
                          className="btn-sm btn-danger"
                          onClick={() => confirmDeleteDocument(doc.id)}
                        >
                          Delete
                        </button>
                        <button className="btn-sm btn-secondary" onClick={cancelDeleteDocument}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="doc-info">
                        <button
                          className={`link${doc.id === selectedDocumentId ? " selected" : ""}`}
                          onClick={() => setSelectedDocumentId(doc.id)}
                        >
                          {doc.filename}
                        </button>
                        <small>{doc.summary || "No summary"}</small>
                      </div>
                      <button
                        className="btn-sm btn-danger"
                        title="Delete document"
                        onClick={() => initiateDeleteDocument(doc.id)}
                      >
                        ✕
                      </button>
                    </>
                  )}
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
              {documentAnswer && (
                <div>
                  <p className="response">{documentAnswer}</p>
                  {contextChunks.length > 0 && (
                    <div className="context-snippets">
                      <button
                        type="button"
                        className="link context-toggle"
                        onClick={() => setShowContext((v) => !v)}
                      >
                        {showContext ? "Hide" : "Show"} retrieved context ({contextChunks.length} {contextChunks.length === 1 ? "snippet" : "snippets"})
                      </button>
                      {showContext && (
                        <ol className="context-list">
                          {contextChunks.map((chunk, i) => (
                            <li key={i}>
                              <pre className="context-chunk">{chunk}</pre>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  )}
                </div>
              )}
            </form>
          </div>
        )}
      </section>
    </main>
  );
}

function TaskEditForm({ task, onChange, onSave, onCancel }) {
  return (
    <div className="inline-edit">
      <input
        value={task.title}
        onChange={(e) => onChange((prev) => ({ ...prev, title: e.target.value }))}
        placeholder="Title"
        required
      />
      <input
        value={task.notes}
        onChange={(e) => onChange((prev) => ({ ...prev, notes: e.target.value }))}
        placeholder="Notes (optional)"
      />
      <input
        type="datetime-local"
        value={task.due_at}
        onChange={(e) => onChange((prev) => ({ ...prev, due_at: e.target.value }))}
      />
      <div className="edit-actions">
        <button type="button" className="btn-sm" onClick={onSave} disabled={!task.title.trim()}>
          Save
        </button>
        <button type="button" className="btn-sm btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ReminderEditForm({ reminder, onChange, onSave, onCancel }) {
  return (
    <div className="inline-edit">
      <input
        value={reminder.title}
        onChange={(e) => onChange((prev) => ({ ...prev, title: e.target.value }))}
        placeholder="Title"
        required
      />
      <input
        type="datetime-local"
        value={reminder.remind_at}
        onChange={(e) => onChange((prev) => ({ ...prev, remind_at: e.target.value }))}
      />
      <select
        value={reminder.intensity}
        onChange={(e) => onChange((prev) => ({ ...prev, intensity: e.target.value }))}
      >
        <option value="gentle">Gentle</option>
        <option value="standard">Standard</option>
        <option value="persistent">Persistent</option>
      </select>
      <div className="edit-actions">
        <button
          type="button"
          className="btn-sm"
          onClick={onSave}
          disabled={!reminder.title.trim()}
        >
          Save
        </button>
        <button type="button" className="btn-sm btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
