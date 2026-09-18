import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);

  const [instruction, setInstruction] = useState(
    "Find duplicate customer records. Merge only when confident; flag uncertain cases."
  );

  const [result, setResult] = useState(null);
  const [manualDecisions, setManualDecisions] = useState({});

  const [loading, setLoading] = useState(false);
  const [applyingDecision, setApplyingDecision] = useState("");
  const [downloading, setDownloading] = useState("");

  const [error, setError] = useState("");
  const [candidateErrors, setCandidateErrors] = useState({});

  // =====================================================
  // ANALYZE DATASET
  // =====================================================

  const analyzeDataset = async () => {
    if (!file) {
      setError("Please select a dataset first.");
      return;
    }

    setLoading(true);
    setError("");
    setCandidateErrors({});
    setResult(null);
    setManualDecisions({});

    const formData = new FormData();

    formData.append("file", file);
    formData.append("instruction", instruction);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/analyze",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Something went wrong while analyzing the dataset."
        );
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // HUMAN REVIEW DECISION
  // =====================================================

  const handleManualDecision = async (candidate, decision) => {
    if (!result) {
      return;
    }

    const pairKey =
      `${candidate.record_1_id}-${candidate.record_2_id}`;

    const updatedManualDecisions = {
      ...manualDecisions,
      [pairKey]: decision,
    };

    setApplyingDecision(pairKey);
    setError("");

    setCandidateErrors((previous) => ({
      ...previous,
      [pairKey]: "",
    }));

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/apply-decisions",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            records: result.preview,
            candidates: result.candidates,
            manual_decisions: updatedManualDecisions,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not apply the human review decision."
        );
      }

      setManualDecisions(updatedManualDecisions);

      setCandidateErrors((previous) => ({
        ...previous,
        [pairKey]: "",
      }));

      setResult((previous) => ({
        ...previous,

        summary: data.summary,

        data_quality_report:
          data.data_quality_report,

        master_record_count:
          data.master_record_count,

        master_data:
          data.master_data,

        candidates:
          data.candidates,
      }));
    } catch (err) {
      setCandidateErrors((previous) => ({
        ...previous,
        [pairKey]: err.message,
      }));
    } finally {
      setApplyingDecision("");
    }
  };

  // =====================================================
  // DOWNLOAD FILE
  // =====================================================

  const downloadExport = async (type) => {
    if (!result) {
      setError("Please analyze a dataset first.");
      return;
    }

    let endpoint = "";
    let filename = "";

    if (type === "csv") {
      endpoint = "/export/csv";
      filename = "clean_master_dataset.csv";
    } else if (type === "xlsx") {
      endpoint = "/export/xlsx";
      filename = "clean_master_dataset.xlsx";
    } else if (type === "log") {
      endpoint = "/export/decision-log";
      filename = "decision_log.csv";
    } else {
      return;
    }

    setDownloading(type);
    setError("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000${endpoint}`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            master_data: result.master_data,
            candidates: result.candidates,
          }),
        }
      );

      if (!response.ok) {
        let message = "Could not download the file.";

        try {
          const errorData = await response.json();

          message =
            errorData.detail ||
            message;
        } catch {
          // Use default message.
        }

        throw new Error(message);
      }

      const blob = await response.blob();

      const url =
        window.URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;
      link.download = filename;

      document.body.appendChild(link);

      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading("");
    }
  };

  // =====================================================
  // DATA QUALITY HELPERS
  // =====================================================

  const getQualityStatusClass = (status) => {
    if (status === "CLEAN") {
      return "quality-clean";
    }

    if (status === "REVIEW_RECOMMENDED") {
      return "quality-review";
    }

    if (status === "CONFLICTS_PRESERVED") {
      return "quality-conflict";
    }

    if (status === "MISSING_DATA") {
      return "quality-missing";
    }

    return "quality-review";
  };

  const getQualityStatusText = (status) => {
    if (status === "CLEAN") {
      return "Clean";
    }

    if (status === "REVIEW_RECOMMENDED") {
      return "Review Recommended";
    }

    if (status === "CONFLICTS_PRESERVED") {
      return "Conflicts Preserved";
    }

    if (status === "MISSING_DATA") {
      return "Missing Data";
    }

    return status;
  };

  // =====================================================
  // DECISION SOURCE DISPLAY
  // =====================================================

  const getDecisionSourceText = (candidate) => {
    if (candidate.decision_source === "HUMAN") {
      return "HUMAN REVIEW";
    }

    if (
      candidate.original_decision === "REVIEW" &&
      candidate.ai_review
    ) {
      return "AGENT + AI REVIEW";
    }

    return "AUTOMATIC RULES";
  };

  // =====================================================
  // PAGE
  // =====================================================

  return (
    <div className="app">

      {/* ================= HEADER ================= */}

      <header className="header">

        <div className="logo">
          <span>✦</span>
          Data Cleanup Agent
        </div>

        <div className="status">
          <span className="status-dot"></span>
          Agent Ready
        </div>

      </header>

      <main className="container">

        {/* ================= HERO ================= */}

        <section className="hero">

          <div className="badge">
            AI-POWERED DATA QUALITY
          </div>

          <h1>
            Turn messy customer data into a
            <span> clean master dataset.</span>
          </h1>

          <p>
            Upload your customer data, describe how you want
            it cleaned, and let the agent detect duplicates,
            inconsistencies and conflicting customer records.
          </p>

        </section>

        {/* ================= WORKSPACE ================= */}

        <section className="workspace">

          {/* CLEANUP INSTRUCTION */}

          <div className="card">

            <div className="step-number">
              1
            </div>

            <h2>
              Tell the agent what to do
            </h2>

            <p className="description">
              Describe your cleanup requirements in natural
              language.
            </p>

            <textarea
              value={instruction}
              onChange={(e) =>
                setInstruction(e.target.value)
              }
              placeholder="Enter cleanup instructions..."
            />

          </div>

          {/* FILE UPLOAD */}

          <div className="card">

            <div className="step-number">
              2
            </div>

            <h2>
              Upload your dataset
            </h2>

            <p className="description">
              Supported formats: CSV, JSON and XLSX
            </p>

            <label className="upload-box">

              <div className="upload-icon">
                ↑
              </div>

              <strong>
                {file
                  ? file.name
                  : "Choose a dataset"}
              </strong>

              <span>
                {file
                  ? "File selected successfully"
                  : "Click here to select CSV, JSON or XLSX"}
              </span>

              <input
                type="file"
                accept=".csv,.json,.xlsx"
                onChange={(e) => {
                  setFile(e.target.files[0]);
                  setResult(null);
                  setManualDecisions({});
                  setCandidateErrors({});
                  setError("");
                }}
                hidden
              />

            </label>

          </div>

          {/* ANALYZE */}

          <button
            className="analyze-button"
            disabled={!file || loading}
            onClick={analyzeDataset}
          >
            {loading
              ? "Analyzing Dataset..."
              : "✦ Analyze & Clean Dataset"}
          </button>

          {/* GLOBAL ERROR */}

          {error && (
            <div className="error-message">
              ⚠ {error}
            </div>
          )}

          {/* =================================================
              RESULTS
          ================================================= */}

          {result && (
            <section className="results">

              {/* RESULTS HEADING */}

              <div className="results-heading">

                <span className="results-label">
                  ANALYSIS COMPLETE
                </span>

                <h2>
                  Cleanup Analysis
                </h2>

                <p>
                  {result.filename} •{" "}
                  {result.total_records} records analyzed
                </p>

              </div>

              {/* ================= SUMMARY ================= */}

              <div className="summary-grid">

                <div className="summary-card">

                  <span>
                    Total Records
                  </span>

                  <strong>
                    {result.total_records}
                  </strong>

                </div>

                <div className="summary-card merge">

                  <span>
                    Merge Decisions
                  </span>

                  <strong>
                    {result.summary.merge}
                  </strong>

                </div>

                <div className="summary-card review">

                  <span>
                    Needs Review
                  </span>

                  <strong>
                    {result.summary.review}
                  </strong>

                </div>

                <div className="summary-card separate">

                  <span>
                    Keep Separate
                  </span>

                  <strong>
                    {result.summary.keep_separate}
                  </strong>

                </div>

              </div>

              {/* =================================================
                  DATA QUALITY REPORT
              ================================================= */}

              {result.data_quality_report && (
                <div className="quality-section">

                  <div className="quality-heading">

                    <div>

                      <span className="quality-label">
                        DATA HEALTH
                      </span>

                      <h2>
                        Data Quality Report
                      </h2>

                      <p className="description">
                        A live summary of duplicate,
                        completeness and conflict checks
                        performed on your dataset.
                      </p>

                    </div>

                    <div
                      className={`quality-status ${getQualityStatusClass(
                        result.data_quality_report.status
                      )}`}
                    >
                      <span className="quality-status-dot"></span>

                      {getQualityStatusText(
                        result.data_quality_report.status
                      )}
                    </div>

                  </div>

                  <div className="quality-grid">

                    {/* MISSING VALUES */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ◫
                      </span>

                      <div>
                        <span>
                          Missing Values
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .missing_values
                          }
                        </strong>
                      </div>

                    </div>

                    {/* DUPLICATE CANDIDATES */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ◉
                      </span>

                      <div>
                        <span>
                          Duplicate Candidates
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .duplicate_candidates
                          }
                        </strong>
                      </div>

                    </div>

                    {/* CONFLICTS */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ⚠
                      </span>

                      <div>
                        <span>
                          Conflicts Detected
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .conflicts_detected
                          }
                        </strong>
                      </div>

                    </div>

                    {/* AUTOMATIC MERGES */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ✓
                      </span>

                      <div>
                        <span>
                          Automatic Merges
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .automatic_merges ??
                            result
                              .data_quality_report
                              .auto_merges ??
                            0
                          }
                        </strong>
                      </div>

                    </div>

                    {/* HUMAN APPROVED MERGES */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ♙
                      </span>

                      <div>
                        <span>
                          Human-Approved Merges
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .human_approved_merges ??
                            0
                          }
                        </strong>
                      </div>

                    </div>

                    {/* HUMAN REVIEW */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ?
                      </span>

                      <div>
                        <span>
                          Needs Human Review
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .needs_human_review
                          }
                        </strong>
                      </div>

                    </div>

                    {/* MASTER RECORDS */}

                    <div className="quality-card">

                      <span className="quality-card-icon">
                        ✦
                      </span>

                      <div>
                        <span>
                          Clean Master Records
                        </span>

                        <strong>
                          {
                            result
                              .data_quality_report
                              .clean_master_records
                          }
                        </strong>
                      </div>

                    </div>

                  </div>

                  {/* QUALITY MESSAGE */}

                  <div
                    className={`quality-message ${getQualityStatusClass(
                      result.data_quality_report.status
                    )}`}
                  >

                    <div className="quality-message-icon">
                      {result.data_quality_report.status ===
                      "CLEAN"
                        ? "✓"
                        : "!"}
                    </div>

                    <div>

                      <strong>
                        {getQualityStatusText(
                          result.data_quality_report.status
                        )}
                      </strong>

                      <p>
                        {
                          result
                            .data_quality_report
                            .status_message
                        }
                      </p>

                    </div>

                  </div>

                </div>
              )}

              {/* =================================================
                  DUPLICATE CANDIDATES
              ================================================= */}

              <div className="candidate-section">

                <h2>
                  Duplicate Candidates
                </h2>

                <p className="description">
                  Review possible duplicate records and
                  resolve ambiguous cases safely.
                </p>

                {result.candidates
                  .filter(
                    (candidate) =>
                      candidate.decision !==
                        "KEEP_SEPARATE" ||
                      candidate.decision_source ===
                        "HUMAN"
                  )
                  .map((candidate, index) => {

                    const pairKey =
                      `${candidate.record_1_id}-${candidate.record_2_id}`;

                    const isApplying =
                      applyingDecision === pairKey;

                    const candidateError =
                      candidateErrors[pairKey];

                    return (
                      <div
                        className="candidate-card"
                        key={pairKey || index}
                      >

                        {/* TOP */}

                        <div className="candidate-top">

                          <div>

                            <strong>
                              {candidate.record_1_id}
                            </strong>

                            <span className="arrow">
                              →
                            </span>

                            <strong>
                              {candidate.record_2_id}
                            </strong>

                          </div>

                          <div
                            className={`decision-badge ${
                              candidate.decision === "MERGE"
                                ? "merge-badge"
                                : candidate.decision ===
                                  "KEEP_SEPARATE"
                                ? "separate-badge"
                                : "review-badge"
                            }`}
                          >
                            {candidate.decision}
                          </div>

                        </div>

                        {/* CONFIDENCE */}

                        <div className="confidence">
                          Confidence:{" "}
                          <strong>
                            {candidate.score}%
                          </strong>
                        </div>

                        {/* REASON */}

                        <p className="reason">
                          {candidate.reason}
                        </p>

                        {/* AI INVESTIGATION */}

                        {candidate.ai_review && (
                          <div className="ai-review-box">

                            <h4>
                              ✨ Ambiguity Investigation
                            </h4>

                            <p>
                              <strong>
                                Recommendation:
                              </strong>{" "}
                              {
                                candidate
                                  .ai_review
                                  .ai_decision
                              }
                            </p>

                            <p>
                              <strong>
                                Reason:
                              </strong>{" "}
                              {
                                candidate
                                  .ai_review
                                  .ai_reason
                              }
                            </p>

                            {candidate.ai_review
                              .requires_human_review &&
                              candidate.decision ===
                                "REVIEW" && (
                                <>

                                  <p className="human-review-text">
                                    ⚠ Human confirmation
                                    required before merging.
                                  </p>

                                  <div className="manual-review-section">

                                    <p className="manual-review-title">
                                      Your Decision
                                    </p>

                                    <div className="manual-review-buttons">

                                      <button
                                        type="button"
                                        className="manual-merge-btn"
                                        disabled={isApplying}
                                        onClick={() =>
                                          handleManualDecision(
                                            candidate,
                                            "MERGE"
                                          )
                                        }
                                      >
                                        {isApplying
                                          ? "Checking..."
                                          : "✓ Merge Records"}
                                      </button>

                                      <button
                                        type="button"
                                        className="manual-separate-btn"
                                        disabled={isApplying}
                                        onClick={() =>
                                          handleManualDecision(
                                            candidate,
                                            "KEEP_SEPARATE"
                                          )
                                        }
                                      >
                                        {isApplying
                                          ? "Checking..."
                                          : "Keep Separate"}
                                      </button>

                                    </div>

                                  </div>

                                </>
                              )}

                            {/* INLINE SAFETY ERROR */}

                            {candidateError && (
                              <div className="merge-blocked-box">

                                <div className="merge-blocked-icon">
                                  ⚠
                                </div>

                                <div>

                                  <strong>
                                    Merge Blocked
                                  </strong>

                                  <p>
                                    {candidateError}
                                  </p>

                                  <span>
                                    No customer records were
                                    merged.
                                  </span>

                                </div>

                              </div>
                            )}

                            {/* HUMAN DECISION SUCCESS */}

                            {candidate.decision_source ===
                              "HUMAN" && (
                              <div className="manual-decision-result">

                                <span>
                                  ✓ Human decision applied:
                                </span>{" "}

                                <strong>
                                  {candidate.decision}
                                </strong>

                              </div>
                            )}

                          </div>
                        )}

                        {/* FIELD SCORES */}

                        <div className="field-scores">

                          {Object.entries(
                            candidate.field_scores
                          ).map(([field, score]) => (

                            <div
                              className="field-score"
                              key={field}
                            >

                              <span>
                                {field}
                              </span>

                              <strong>
                                {score}%
                              </strong>

                            </div>

                          ))}

                        </div>

                      </div>
                    );
                  })}

              </div>

              {/* =================================================
                  CLEAN MASTER DATASET
              ================================================= */}

              <div className="master-section">

                <div className="master-heading">

                  <span className="master-label">
                    CLEANED OUTPUT
                  </span>

                  <h2>
                    Clean Master Dataset
                  </h2>

                  <p className="description">
                    {result.master_record_count} master records
                    created from{" "}
                    {result.total_records} original records.
                  </p>

                  <div className="export-buttons">

                    <button
                      type="button"
                      className="export-button"
                      disabled={downloading !== ""}
                      onClick={() =>
                        downloadExport("csv")
                      }
                    >
                      {downloading === "csv"
                        ? "Preparing CSV..."
                        : "↓ Download Clean CSV"}
                    </button>

                    <button
                      type="button"
                      className="export-button"
                      disabled={downloading !== ""}
                      onClick={() =>
                        downloadExport("xlsx")
                      }
                    >
                      {downloading === "xlsx"
                        ? "Preparing XLSX..."
                        : "↓ Download Clean XLSX"}
                    </button>

                    <button
                      type="button"
                      className="export-button secondary-export"
                      disabled={downloading !== ""}
                      onClick={() =>
                        downloadExport("log")
                      }
                    >
                      {downloading === "log"
                        ? "Preparing Log..."
                        : "↓ Download Decision Log"}
                    </button>

                  </div>

                </div>

                <div className="table-wrapper">

                  <table className="master-table">

                    <thead>
                      <tr>
                        <th>Customer ID</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Address</th>
                        <th>City</th>
                        <th>Last Updated</th>
                        <th>Source</th>
                        <th>Merged From</th>
                        <th>Conflicts</th>
                      </tr>
                    </thead>

                    <tbody>

                      {result.master_data.map(
                        (record, index) => (

                          <tr key={index}>

                            <td>
                              <strong>
                                {record.customer_id}
                              </strong>
                            </td>

                            <td>{record.name}</td>
                            <td>{record.email}</td>
                            <td>{record.phone}</td>
                            <td>{record.address}</td>
                            <td>{record.city}</td>

                            <td>
                              {record.last_updated}
                            </td>

                            <td>
                              {record.source}
                            </td>

                            <td>
                              <span className="merged-from">
                                {record.merged_from}
                              </span>
                            </td>

                            <td>

                              {record.conflicts ? (
                                <span className="conflict-value">
                                  ⚠ {record.conflicts}
                                </span>
                              ) : (
                                <span className="no-conflict">
                                  None
                                </span>
                              )}

                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              </div>

              {/* =================================================
                  DECISION LOG
              ================================================= */}

              <div className="decision-log-section">

                <div className="decision-log-heading">

                  <span className="log-label">
                    AUDIT TRAIL
                  </span>

                  <h2>
                    Decision Log
                  </h2>

                  <p className="description">
                    Every candidate pair processed by the
                    agent, including its decision,
                    confidence, reason and decision source.
                  </p>

                </div>

                <div className="decision-log">

                  {result.candidates.map(
                    (candidate, index) => (

                      <div
                        className="log-row"
                        key={
                          `${candidate.record_1_id}-${candidate.record_2_id}-${index}`
                        }
                      >

                        <div className="log-pair">

                          <strong>
                            {candidate.record_1_id}
                          </strong>

                          <span>↔</span>

                          <strong>
                            {candidate.record_2_id}
                          </strong>

                        </div>

                        <div>

                          <span
                            className={`log-decision ${
                              candidate.decision === "MERGE"
                                ? "log-merge"
                                : candidate.decision ===
                                  "KEEP_SEPARATE"
                                ? "log-separate"
                                : "log-review"
                            }`}
                          >
                            {candidate.decision}
                          </span>

                        </div>

                        <div className="log-confidence">
                          {candidate.score}%
                        </div>

                        <div className="log-reason">

                          {candidate.reason}

                          <div className="decision-source">

                            Source:{" "}

                            <strong>
                              {getDecisionSourceText(
                                candidate
                              )}
                            </strong>

                          </div>

                        </div>

                      </div>

                    )
                  )}

                </div>

              </div>

            </section>
          )}

        </section>

      </main>

    </div>
  );
}

export default App;