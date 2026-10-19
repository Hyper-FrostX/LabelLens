
import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Checking backend...");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Backend response:", data);
        setStatus(
          data.status === "healthy" ? "Connected" : "Unexpected response"
        );
        setError("");
      })
      .catch((err) => {
        console.error("Backend connection failed:", err);
        setStatus("Disconnected");
        setError(err.message);
      });
  }, []);

  return (
    <main className="app">
      <div className="card">
        <p className="eyebrow">AI-POWERED FOOD LABEL ANALYZER</p>
        <h1>Label Lens</h1>
        <p className="subtitle">
          Understand what's inside your food.
        </p>

        <div className="status">
          <span
            className={`indicator ${status === "Connected" ? "online" : ""}`}
          />
          Backend: <strong>{status}</strong>
        </div>

        {error && <p className="error">{error}</p>}
      </div>
    </main>
  );
}

export default App;
