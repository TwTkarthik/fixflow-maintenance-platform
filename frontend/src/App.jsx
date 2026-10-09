import { useEffect, useState } from "react";

const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

function App() {
  const [health, setHealth] = useState({ state: "loading", data: null, error: "" });

  useEffect(() => {
    const controller = new AbortController();

    async function checkApiHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`The API returned HTTP ${response.status}.`);
        }

        const data = await response.json();
        setHealth({ state: "connected", data, error: "" });
      } catch (error) {
        if (error.name !== "AbortError") {
          setHealth({
            state: "error",
            data: null,
            error: "The FixFlow API is unavailable. Start the backend and try again.",
          });
        }
      }
    }

    checkApiHealth();
    return () => controller.abort();
  }, []);

  const statusLabel = {
    loading: "Checking connection",
    connected: "API connected",
    error: "API disconnected",
  }[health.state];

  return (
    <main className="page-shell">
      <section className="hero-card" aria-labelledby="page-title">
        <div className="eyebrow">Maintenance management platform</div>
        <h1 id="page-title">FixFlow</h1>
        <p className="intro">
          A clear starting point for managing equipment repairs, technician work,
          and maintenance history.
        </p>

        <div className={`status-panel status-${health.state}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>{statusLabel}</strong>
            {health.state === "loading" && <p>Contacting the local backend...</p>}
            {health.state === "connected" && (
              <p>The frontend received a response from the real health endpoint.</p>
            )}
            {health.state === "error" && <p>{health.error}</p>}
          </div>
        </div>

        {health.data && (
          <div className="response-card">
            <span>Backend response</span>
            <pre>{JSON.stringify(health.data, null, 2)}</pre>
          </div>
        )}

        <footer className="page-footer">
          <span>Initial application skeleton</span>
          <span>{apiBaseUrl}</span>
        </footer>
      </section>
    </main>
  );
}

export default App;
