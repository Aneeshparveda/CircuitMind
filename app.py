"""Local Streamlit host for the CircuitMind React forensic console."""

from __future__ import annotations

import base64
import json
import traceback
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from data.schema_adapter import standardize_dataframe
from engine import repair_memory
from engine.orchestrator import CircuitMindOrchestrator
from engine.test_integrity import fleet_tester_analysis
from reports.csv_generator import generate_csv_bytes
from reports.pdf_generator import generate_pdf_bytes


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_BUILD = PROJECT_ROOT / "frontend-vite" / "dist"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
BUILT_IN_DEMO_LOGS = (
    PROJECT_ROOT / "data" / "test_logs.csv",
    PROJECT_ROOT / "data" / "u3_cascade_demo_log.csv",
    PROJECT_ROOT / "data" / "dual_fault_demo_log.csv",
    PROJECT_ROOT / "data" / "novel_demo_log.csv",
)

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="CircuitMind")


class NpEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


@st.cache_resource
def get_engine() -> CircuitMindOrchestrator:
    return CircuitMindOrchestrator(
    )


@st.cache_data
def load_demo_data() -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in BUILT_IN_DEMO_LOGS if path.exists()]
    if not frames:
        raise FileNotFoundError("CircuitMind's built-in test logs could not be found.")
    return standardize_dataframe(pd.concat(frames, ignore_index=True, sort=False))


@st.cache_data
def load_validation_metrics() -> Dict[str, Any]:
    metrics_path = PROJECT_ROOT / "validation" / "metrics.json"
    if not metrics_path.exists():
        return {}
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    # The validator records seconds; the console displays milliseconds.
    if "inference_ms" not in metrics and metrics.get("average_inference_seconds") is not None:
        metrics["inference_ms"] = round(float(metrics["average_inference_seconds"]) * 1000, 1)
    # Attach the learned-weight provenance so the console can show the
    # "weights learned from 300 labeled boards" story on screen.
    cfg_path = PROJECT_ROOT / "config" / "diagnostic_weights.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        metrics["weights_note"] = cfg.get("weights_note", "")
        metrics["learned_weights"] = cfg.get("weights", {})
    except (json.JSONDecodeError, OSError):
        pass
    return metrics


@st.cache_data
def load_ground_truth() -> Dict[str, str]:
    """Board -> true root cause for the 100 benchmark boards, if available."""
    path = PROJECT_ROOT / "validation" / "ground_truth_blind.csv"
    if not path.exists():
        return {}
    try:
        truth = pd.read_csv(path)
        return {str(row.board_id): str(row.root_cause) for row in truth.itertuples(index=False)}
    except Exception:
        return {}


@st.cache_data
def load_component_options() -> list[Dict[str, str]]:
    """Local BOM index for the optional inspection and simulation selector."""
    bom_path = PROJECT_ROOT / "data" / "components.csv"
    if not bom_path.exists():
        return []
    bom = pd.read_csv(bom_path, usecols=["refdes", "desc", "net"])
    return [
        {"refdes": str(row.refdes), "desc": str(row.desc), "net": str(row.net)}
        for row in bom.itertuples(index=False)
    ]


def clean_nans(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    elif isinstance(obj, (float, np.floating)):
        return None if np.isnan(obj) else float(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return clean_nans(obj.tolist())
    return obj


def serializable(value: Any) -> Any:
    return clean_nans(value)


def initialize_state() -> None:
    defaults = {
        "ui_state": "intake",
        "active_logs": None,
        "selected_board": "",
        "selected_component": "",
        "uploaded_file": None,
        "report": None,
        "simulation": None,
        "challenge_open": False,
        "error_message": "",
        "repair_notes": "",
        "pdf_base64": "",
        "csv_base64": "",
        "fleet": None,
        "fleet_scan_ms": None,
        "verified_confirmation": None,
        "revealed_truth": None,
        "fleet_tester": None,
        "last_event_id": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def demo_cases() -> list[Dict[str, str]]:
    return [
        {
            "id": "strong",
            "board_id": "BRD_0415",
            "label": "Strong cascade case",
            "subtitle": "Power-domain symptoms — benchmark board with the honest multi-fault flag",
        },
        {
            "id": "difficult",
            "board_id": "BRD_0401",
            "label": "Difficult case",
            "subtitle": "Close alternatives that require an additional physical test",
        },
        {
            "id": "u3_cascade",
            "board_id": "BRD_U3_CASCADE_001",
            "label": "U3 power cascade",
            "subtitle": "ICT/FCT log: a low 5 V rail causing downstream functional failures",
        },
        {
            "id": "dual_fault",
            "board_id": "BRD_DUAL_FAULT_001",
            "label": "Dual fault case",
            "subtitle": "Two independent faults — the system refuses to force one root cause",
        },
        {
            "id": "novel",
            "board_id": "BRD_NOVEL_001",
            "label": "Novel / inconclusive case",
            "subtitle": "Unfamiliar failure pattern — the system knows when it does not know",
        },
        {
            "id": "fleet",
            "board_id": "",
            "label": "Fleet scan",
            "subtitle": "Multi-board diagnostic sweep — 30 boards, one pass",
        },
        {
            "id": "tester",
            "board_id": "",
            "label": "Tester-anomaly lot",
            "subtitle": "8 boards fail the same test at the same value — is it the board or the station?",
        },
    ]


def set_demo(case_id: str) -> None:
    case = next((item for item in demo_cases() if item["id"] == case_id), None)
    if case is None:
        raise ValueError("Unknown demo case requested.")
    demo_logs = load_demo_data()
    if case_id == "fleet":
        # The fleet demo loads a curated multi-board set so the SCAN ALL
        # pipeline (fleet grid + projection banner) is demoable live without
        # hunting for a CSV. Curated to 30 boards: the three demo boards plus
        # the first 27 others in the corpus — snappy scan, tidy grid.
        demo_ids = ["BRD_0415", "BRD_0401", "BRD_U3_CASCADE_001", "BRD_DUAL_FAULT_001"]
        others = [
            board for board in sorted(demo_logs["board_id"].astype(str).unique())
            if board not in demo_ids
        ][:27]
        selected_ids = demo_ids + others
        demo_logs = demo_logs.loc[
            demo_logs["board_id"].astype(str).isin(selected_ids)
        ].copy()
        label = f"Fleet of {len(selected_ids)} boards"
    elif case_id == "tester":
        # A lot where every board fails the same test at the same value — the
        # canonical 'failure or tester?' scenario. The fleet scan must say
        # TEST SYSTEM SUSPECTED instead of N independent board faults.
        tester_path = PROJECT_ROOT / "data" / "tester_anomaly_demo_log.csv"
        demo_logs = standardize_dataframe(pd.read_csv(tester_path))
        selected_ids = sorted(demo_logs["board_id"].astype(str).unique())
        label = f"Tester-anomaly lot ({len(selected_ids)} boards, station STA-03 / fixture FIX-07)"
    else:
        # A single-case demo is a self-contained board, not the whole
        # benchmark corpus. This keeps the continuation screen focused.
        demo_logs = demo_logs.loc[
            demo_logs["board_id"].astype(str) == case["board_id"]
        ].copy()
        label = case["label"]
    if demo_logs.empty:
        raise ValueError("The requested built-in case has no test rows.")
    st.session_state.active_logs = demo_logs
    st.session_state.selected_board = (
        case["board_id"] if case_id != "fleet" else selected_ids[0]
    )
    st.session_state.selected_component = ""
    st.session_state.uploaded_file = {"name": label, "demo": True}
    st.session_state.report = None
    st.session_state.simulation = None
    st.session_state.challenge_open = False
    st.session_state.error_message = ""
    st.session_state.repair_notes = ""
    st.session_state.pdf_base64 = ""
    st.session_state.csv_base64 = ""
    st.session_state.verified_confirmation = None
    st.session_state.ui_state = "ready"


def handle_upload(event: Dict[str, Any]) -> None:
    csv_text = event.get("csv_text", "")
    filename = event.get("filename", "uploaded-log.csv")
    byte_count = len(csv_text.encode("utf-8"))
    if not csv_text.strip():
        raise ValueError("The selected file is empty.")
    if byte_count > MAX_UPLOAD_BYTES:
        raise ValueError("The selected CSV exceeds the 5 MB local upload limit.")

    try:
        raw = pd.read_csv(StringIO(csv_text))
    except Exception as error:
        raise ValueError("CircuitMind could not read that file as a CSV.") from error
    normalized = standardize_dataframe(raw)
    board_ids = normalized["board_id"].dropna().astype(str).unique().tolist()
    if not board_ids:
        raise ValueError("No board identifier could be derived from the CSV.")

    st.session_state.active_logs = normalized
    st.session_state.selected_board = board_ids[0]
    st.session_state.selected_component = ""
    st.session_state.uploaded_file = {"name": filename, "size": byte_count, "demo": False}
    st.session_state.report = None
    st.session_state.simulation = None
    st.session_state.challenge_open = False
    st.session_state.error_message = ""
    st.session_state.repair_notes = ""
    st.session_state.pdf_base64 = ""
    st.session_state.csv_base64 = ""
    st.session_state.fleet = None
    st.session_state.verified_confirmation = None
    st.session_state.ui_state = "ready"


def run_fleet_scan() -> None:
    """Run every board in the active logs through the pipeline into a fleet grid."""
    logs = st.session_state.active_logs
    if logs is None:
        raise ValueError("Load a demo case or upload a test log before scanning.")
    import time
    scan_start = time.perf_counter()
    fleet = []
    for board_id in sorted(logs["board_id"].astype(str).unique()):
        try:
            report = serializable(
                get_engine().analyze(board_id, logs, repair_notes=st.session_state.repair_notes)
            )
            suspects = report.get("suspects") or []
            fleet.append({
                "board_id": board_id,
                "status": report["status"],
                "confidence_tier": report.get("confidence_tier", ""),
                "top_refdes": suspects[0]["refdes"] if suspects else "",
                "top_score": suspects[0]["score"] if suspects else None,
                "failed_tests": len(report.get("signature", {}).get("failed_tests", [])),
                "fingerprint": report.get("fingerprint", ""),
            })
        except Exception:
            fleet.append({
                "board_id": board_id,
                "status": "ERROR",
                "confidence_tier": "",
                "top_refdes": "",
                "top_score": None,
                "failed_tests": 0,
            })
    st.session_state.fleet = fleet
    st.session_state.fleet_scan_ms = round((time.perf_counter() - scan_start) * 1000, 1)
    # 'Failure or tester?' — fleet-level test-failure-rate analysis. Ground
    # truth is not part of the fleet payload (Bug C).
    st.session_state.fleet_tester = serializable(fleet_tester_analysis(logs))
    st.session_state.error_message = ""
    st.session_state.ui_state = "ready"


def run_analysis(board_id: str, component_id: str = "") -> None:
    logs = st.session_state.active_logs
    if logs is None:
        raise ValueError("Load a demo case or upload a test log before analysis.")
    available = logs["board_id"].astype(str).unique().tolist()
    selected = board_id if board_id in available else available[0]
    st.session_state.selected_board = selected
    st.session_state.selected_component = component_id
    st.session_state.report = serializable(
        get_engine().analyze(selected, logs, repair_notes=st.session_state.repair_notes)
    )
    # Ground truth NEVER rides in the analysis payload (Bug C). It is only
    # delivered after an explicit reveal action.
    st.session_state.revealed_truth = None
    st.session_state.simulation = None
    st.session_state.challenge_open = False
    st.session_state.error_message = ""
    st.session_state.ui_state = "results"


def handle_event(event: Dict[str, Any]) -> None:
    action = event.get("action")
    if action == "load_demo":
        set_demo(str(event.get("case_id", "")))
    elif action == "upload_csv_text":
        handle_upload(event)
    elif action == "analyze":
        notes = event.get("repair_notes")
        if notes is not None:
            st.session_state.repair_notes = str(notes)[:2000]
        run_analysis(str(event.get("board_id", "")), str(event.get("component_id", "")))
    elif action == "scan_all":
        run_fleet_scan()
    elif action == "challenge_finding":
        st.session_state.challenge_open = True
    elif action == "reveal_truth":
        # The ONLY path that releases ground truth to the frontend (Bug C).
        # It requires an explicit user action and only answers for the board
        # currently under analysis.
        board_id = str(event.get("board_id", ""))
        if st.session_state.report is None or board_id != str(st.session_state.report.get("board_id", "")):
            st.session_state.revealed_truth = None
        else:
            st.session_state.revealed_truth = load_ground_truth().get(board_id)
    elif action == "simulate_repair":
        if not st.session_state.report:
            raise ValueError("Run an investigation before simulating a repair.")
        refdes = str(event.get("refdes", ""))
        st.session_state.simulation = serializable(
            get_engine().simulate_repair(st.session_state.report, refdes)
        )
    elif action == "record_verified_repair":
        if not st.session_state.report:
            raise ValueError("Run an investigation before recording a repair.")
        report = st.session_state.report
        refdes = str(event.get("refdes", ""))
        # Explicit technician confirmation — never hardcoded (Bug E). The
        # record button stays disabled until the technician ticks both boxes.
        technician_confirmed = bool(event.get("technician_confirmed", False))
        retest_pass = bool(event.get("retest_pass", False))
        failed_steps = "|".join(
            t["test_step"] for t in report.get("signature", {}).get("failed_tests", [])
        )
        # Post-diagnosis technician note is SEPARATE from the pre-diagnosis
        # repair notes (Bug F): the pre-diagnosis observation must never be
        # stored as the verified outcome, or the system would be learning from
        # the evidence that produced the diagnosis it is confirming.
        technician_note = str(event.get("technician_note", "")).strip()[:400]
        st.session_state.verified_confirmation = serializable(
            repair_memory.add_verified_case(
                board_id=str(report.get("board_id", "")),
                refdes=refdes,
                failed_steps=failed_steps,
                notes=technician_note,
                retest_pass=retest_pass,
                technician_confirmed=technician_confirmed,
            )
        )
        conf = st.session_state.verified_confirmation
        if conf.get("added"):
            # Authoritative sync of active session report's verification object
            contract = st.session_state.report.get("diagnostic_contract")
            if contract and isinstance(contract.get("verification"), dict):
                verif = contract["verification"]
                verif["technician_confirmed"] = True
                verif["physical_repair_recorded"] = True
                verif["retest_passed"] = True
                verif["verified_repair"] = True
                verif["repair_memory_admitted"] = True
                verif["state"] = "VERIFIED_REPAIR"
                verif["disclaimer"] = f"Verified repair admitted to session memory ({conf.get('repair_id')})."
            # Refresh the ACTIVE engine so retrieval actually sees the new
            # case (Bug D) — the cached engine otherwise keeps its stale
            # memory until the process restarts.
            get_engine.clear()
    elif action == "export_report":
        if not st.session_state.report:
            raise ValueError("Run an investigation before exporting a report.")
        st.session_state.pdf_base64 = base64.b64encode(
            generate_pdf_bytes(st.session_state.report)
        ).decode("ascii")
    elif action == "export_csv":
        if not st.session_state.report:
            raise ValueError("Run an investigation before exporting a report.")
        st.session_state.csv_base64 = base64.b64encode(
            generate_csv_bytes(st.session_state.report)
        ).decode("ascii")
    elif action == "dismiss_error":
        st.session_state.error_message = ""
    elif action == "reset":
        st.session_state.revealed_truth = None
        st.session_state.fleet_tester = None
        st.session_state.ui_state = "intake"
        st.session_state.active_logs = None
        st.session_state.selected_board = ""
        st.session_state.selected_component = ""
        st.session_state.uploaded_file = None
        st.session_state.report = None
        st.session_state.simulation = None
        st.session_state.challenge_open = False
        st.session_state.error_message = ""
        st.session_state.repair_notes = ""
        st.session_state.pdf_base64 = ""
        st.session_state.csv_base64 = ""
        st.session_state.fleet = None
        st.session_state.fleet_scan_ms = None
        st.session_state.verified_confirmation = None


initialize_state()

if not FRONTEND_BUILD.exists():
    st.error("CircuitMind’s local visual console has not been built. Run `npm run build` in frontend-vite.")
    st.stop()

forensics_console = components.declare_component(
    "forensics_console", path=str(FRONTEND_BUILD)
)

payload = {
    "ui_state": st.session_state.ui_state,
    "demo_cases": demo_cases(),
    "selected_board": st.session_state.selected_board,
    "selected_component": st.session_state.selected_component,
    "board_ids": (
        st.session_state.active_logs["board_id"].astype(str).unique().tolist()
        if st.session_state.active_logs is not None
        else []
    ),
    "component_options": load_component_options(),
    "uploaded_file": st.session_state.uploaded_file,
    "report": st.session_state.report,
    "simulation": st.session_state.simulation,
    "challenge_open": st.session_state.challenge_open,
    "error_message": st.session_state.error_message,
    "pdf_base64": st.session_state.pdf_base64,
    "csv_base64": st.session_state.csv_base64,
    "fleet": st.session_state.fleet,
    "fleet_scan_ms": st.session_state.fleet_scan_ms,
    "fleet_tester": st.session_state.fleet_tester,
    "verified_confirmation": st.session_state.verified_confirmation,
    "revealed_truth": st.session_state.revealed_truth,
    "max_upload_bytes": MAX_UPLOAD_BYTES,
    "validation_metrics": load_validation_metrics(),
}

response = forensics_console(**payload, key="circuitmind_forensics_console")
event_id = response.get("event_id", "") if isinstance(response, dict) else ""
if response and event_id != st.session_state.last_event_id:
    try:
        st.session_state.last_event_id = event_id
        handle_event(response)
    except ValueError as error:
        st.session_state.error_message = str(error)
        st.session_state.ui_state = "error"
    except Exception as error:
        traceback.print_exc()
        st.session_state.error_message = (
            f"CircuitMind could not complete that request "
            f"({type(error).__name__}: {str(error)[:140]})."
        )
        st.session_state.ui_state = "error"
    st.rerun()

st.markdown(
    """
    <style>
      #MainMenu, header, footer { visibility: hidden; }
      .stApp { background: #071015; }
      .block-container { padding: 0 !important; max-width: none !important; }
      iframe { min-height: 100vh; border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)
