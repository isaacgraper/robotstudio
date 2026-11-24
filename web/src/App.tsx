/**
 * Robotstudio - Visual Robot Framework Authoring Platform
 * Main Application Component
 *
 * Top-level React component orchestrating the UI: suite sidebar, Blockly editor,
 * preview/validation/run panes, and toolbar actions. Communicates with the
 * backend API via the client module.
 *
 * @packageDocumentation
 */

import { useEffect, useState, useCallback, useMemo } from "react";
import { BlocklyEditor } from "./components/BlocklyEditor";
import { fetchCatalog, fetchSuites, fetchSuite, saveSuite, updateSuite, deleteSuite, previewDocument, validateDocument, initWorkspace, runSuite, runExportUrl, catalogToKeywordOptions } from "./api/client";
import type { RunSummary } from "./api/client";
import type { CanvasDocument } from "./types/canvas";

/**
 * Suite entry as displayed in the sidebar list.
 */
interface SuiteEntry {
  stem: string;
  name: string;
  tests: number;
  keywords: number;
  updated: string;
}

/**
 * App - Root component for the Robotstudio web application.
 *
 * Manages global state: catalog, suite list, current document, and UI panes.
 * Provides handlers for all user actions (save, run, validate, preview, delete).
 *
 * @returns Main application layout
 */
function App() {
  const [catalog, setCatalog] = useState<{ keywords: Array<any> } | null>(null);
  const [suites, setSuites] = useState<SuiteEntry[]>([]);
  const [currentSuite, setCurrentSuite] = useState<SuiteEntry | null>(null);
  const [document, setDocument] = useState<CanvasDocument | null>(null);
  const [expertMode, setExpertMode] = useState(false);
  const [preview, setPreview] = useState<{ robot_text: string; validation: any } | null>(null);
  const [validation, setValidation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<RunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    try {
      const cat = await fetchCatalog();
      setCatalog(cat);
    } catch (e) {
      console.error("Failed to load catalog:", e);
    }
  }, []);

  const loadSuites = useCallback(async () => {
    try {
      const s = await fetchSuites();
      setSuites(s);
    } catch (e) {
      console.error("Failed to load suites:", e);
    }
  }, []);

  const loadInitial = useCallback(async () => {
    setLoading(true);
    await Promise.all([loadCatalog(), loadSuites()]);
    setLoading(false);
  }, [loadCatalog, loadSuites]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  const handleSuiteSelect = async (suite: SuiteEntry) => {
    setCurrentSuite(suite);
    try {
      const data = await fetchSuite(suite.stem);
      setDocument(data.document);
    } catch (e) {
      setError("Failed to load suite");
      console.error(e);
    }
  };

  const handleNewSuite = async () => {
    try {
      const data = await initWorkspace();
      setSuites((prev) => [data.suite, ...prev]);
      await handleSuiteSelect(data.suite);
    } catch (e) {
      setError("Failed to create suite");
      console.error(e);
    }
  };

  const handleDocumentChange = useCallback((doc: CanvasDocument) => {
    setDocument(doc);
    setValidation(null);
    setPreview(null);
    setRun(null);
  }, []);

  const handleSave = async () => {
    if (!document) return;
    setSaving(true);
    setError(null);
    try {
      const stem = currentSuite?.stem;
      if (stem) {
        await updateSuite(stem, document);
      } else {
        const result = await saveSuite(document);
        setCurrentSuite({ stem: result.stem, name: document.name, tests: document.tests.length, keywords: document.keywords.length, updated: new Date().toISOString() });
      }
      await loadSuites();
      setError(null);
    } catch (e) {
      setError("Failed to save suite");
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (!document || !currentSuite) return;
    setRunning(true);
    setError(null);
    setRun(null);
    try {
      // Make sure the workspace copy matches what is on screen.
      await updateSuite(currentSuite.stem, document);
      const summary = await runSuite(currentSuite.stem);
      setRun(summary);
      if (summary.status !== "passed" && summary.error) setError(summary.error);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  const handlePreview = async () => {
    if (!document) return;
    try {
      const result = await previewDocument(document);
      setPreview(result);
    } catch (e) {
      setError("Preview failed");
      console.error(e);
    }
  };

  const handleValidate = async (dryRun = false) => {
    if (!document) return;
    try {
      const result = await validateDocument(document, dryRun);
      setValidation(result.validation);
    } catch (e) {
      setError("Validation failed");
      console.error(e);
    }
  };

  const handleDelete = async () => {
    if (!currentSuite) return;
    if (!window.confirm(`Delete suite "${currentSuite.name}"?`)) return;
    try {
      await deleteSuite(currentSuite.stem);
      await loadSuites();
      setCurrentSuite(null);
      setDocument(null);
    } catch (e) {
      setError("Delete failed");
      console.error(e);
    }
  };

  // Stable identity: Blockly only rebuilds its toolbox when this actually changes.
  const keywordOptions = useMemo(
    () => (catalog ? catalogToKeywordOptions(catalog) : []),
    [catalog]
  );

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading Robotstudio...</p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Robotstudio</h1>
        <div className="header-actions">
          <label className="expert-toggle">
            <input
              type="checkbox"
              checked={expertMode}
              onChange={(e) => setExpertMode(e.target.checked)}
            />
            Expert Mode
          </label>
        </div>
      </header>

      {error && <div className="error-banner">{error} <button onClick={() => setError(null)}>✕</button></div>}

      <div className="app-body">
        <aside className="sidebar">
          <section className="suite-list">
            <h2>Suites</h2>
            <button className="new-suite-btn" onClick={handleNewSuite}>
              + New Suite
            </button>
            <ul>
              {suites.map((suite) => (
                <li
                  key={suite.stem}
                  className={currentSuite?.stem === suite.stem ? "active" : ""}
                  onClick={() => handleSuiteSelect(suite)}
                >
                  <strong>{suite.name}</strong>
                  <span className="suite-meta">
                    {suite.tests} tests, {suite.keywords} keywords
                  </span>
                  <time className="suite-time">{new Date(suite.updated).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <main className="editor-pane">
          {document ? (
            <>
              <div className="editor-toolbar">
                <button onClick={handleSave} disabled={saving} className="primary">
                  {saving ? "Saving..." : "Save"}
                </button>
                <button onClick={handlePreview}>Preview</button>
                <button onClick={() => handleValidate(false)}>Validate</button>
                <button onClick={() => handleValidate(true)}>Dry Run</button>
                <button onClick={handleRun} disabled={running || !currentSuite} className="run">
                  {running ? "Running..." : "▶ Run"}
                </button>
                {currentSuite && (
                  <button onClick={handleDelete} className="danger">
                    Delete
                  </button>
                )}
              </div>

              <div className="editor-split">
                <div className="blockly-pane">
                  <BlocklyEditor
                    initialDocument={document}
                    documentKey={currentSuite?.stem ?? "new"}
                    onChange={handleDocumentChange}
                    expertMode={expertMode}
                    keywordOptions={keywordOptions}
                  />
                </div>

                {(preview || validation || run) && (
                  <aside className="preview-pane">
                    {run && (
                      <section className="preview-section">
                        <h3>Run Result</h3>
                        <div className={`validation-status ${run.status === "passed" ? "ok" : "fail"}`}>
                          {run.status === "passed" ? "✓ Passed" : `✗ ${run.status}`}
                          <span>
                            {run.passed}/{run.total} passed · {run.duration_ms} ms
                          </span>
                        </div>
                        {run.error && <p className="run-error">{run.error}</p>}
                        <ul className="run-cases">
                          {(run.cases ?? []).map((c, i) => (
                            <li key={i} className={(c.status ?? "").toLowerCase()}>
                              <strong>{c.status}</strong> {c.name}
                              <span className="run-case-time">{c.elapsed_ms} ms</span>
                              {c.message && <em>{c.message}</em>}
                            </li>
                          ))}
                        </ul>
                        <div className="run-exports">
                          <a href={runExportUrl(run.run_id, "junit")}>JUnit XML</a>
                          <a href={runExportUrl(run.run_id, "results-csv")}>Results CSV</a>
                          <a href={runExportUrl(run.run_id, "results-json")}>Results JSON</a>
                          <a href={runExportUrl(run.run_id, "bundle")}>Bundle ZIP</a>
                        </div>
                        <p className="run-artifacts">Artifacts: {run.output_dir}</p>
                      </section>
                    )}
                    {preview && (
                      <section className="preview-section">
                        <h3>Generated Robot Source</h3>
                        <pre className="robot-source">{preview.robot_text}</pre>
                        <details>
                          <summary>Validation</summary>
                          <pre>{JSON.stringify(preview.validation, null, 2)}</pre>
                        </details>
                      </section>
                    )}
                    {validation && !preview && (
                      <section className="preview-section">
                        <h3>Validation Result</h3>
                        <div className={`validation-status ${validation.ok ? "ok" : "fail"}`}>
                          {validation.ok ? "✓ Valid" : "✗ Invalid"}
                          <span>{validation.test_count} tests</span>
                        </div>
                        {validation.messages.length > 0 && (
                          <ul className="validation-messages">
                            {validation.messages.map((msg: any, i: number) => (
                              <li key={i} className={msg.level}>
                                <strong>{msg.level}:</strong> {msg.message}
                              </li>
                            ))}
                          </ul>
                        )}
                      </section>
                    )}
                  </aside>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <h2>Welcome to Robotstudio</h2>
              <p>Select a suite from the sidebar or create a new one to start building.</p>
              <button onClick={handleNewSuite} className="primary">
                Create Demo Suite
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;