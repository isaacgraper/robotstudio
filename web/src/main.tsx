/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * Application Entry Point
 *
 * Bootstraps the React application with an error boundary for graceful
 * error handling. Renders the main App component into the DOM.
 *
 * @packageDocumentation
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

/**
 * ErrorBoundary - Catches React rendering errors and displays a friendly message.
 * Prevents the entire app from crashing on component errors.
 */
interface ErrorBoundaryState {
  error: Error | null;
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Robotstudio UI error:", error, info);
  }

  render() {
    const error = this.state.error;
    if (error) {
      return (
        <div className="app-error">
          <h1>Robotstudio hit an error</h1>
          <pre>{error.message || String(error)}</pre>
          <button onClick={() => this.setState({ error: null })}>Retry</button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
