"""Metrics aggregation functions for FIHG domains"""

import sqlite3
from typing import Optional, Dict, List
from datetime import datetime, timedelta


def aggregate_fihg_metrics(
    graph_name: str,
    time_window: Optional[timedelta] = None,
    db_path: str = "fihg.db"
) -> Dict:
    """Aggregate metrics for a given FIHG graph by querying the event_log.

    Args:
        graph_name: Name of the FIHG graph ("identity", "memory", "skills").
        time_window: Optional time window to filter metrics.
        db_path: Path to SQLite database file (default: "fihg.db").

    Returns:
        Dictionary with aggregated metrics including activity_count, error_count,
        success_rate, average wear, average freshness, and entity_count.
    """
    if graph_name not in ("identity", "memory", "skills"):
        raise ValueError(f"Unknown graph_name: {graph_name}. Must be one of: identity, memory, skills")

    # Ensure event_log table exists (create if missing)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            fihg TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT
        );
        """
    )
    conn.commit()

    cutoff_dt = datetime.utcnow() - time_window if time_window else None
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S") if cutoff_dt else None

    conditions = ["fihg = ?"]
    params = [graph_name]
    if cutoff_str:
        conditions.append("timestamp >= ?")
        params.append(cutoff_str)
    where_clause = " AND ".join(conditions)

    # activity count
    cur = conn.execute(f"SELECT COUNT(*) FROM event_log WHERE {where_clause}", params)
    activity_count = cur.fetchone()[0]

    # error count (event_type contains 'error')
    err_params = params.copy()
    cur = conn.execute(
        f"SELECT COUNT(*) FROM event_log WHERE {where_clause} AND event_type LIKE '%error%'",
        err_params
    )
    error_count = cur.fetchone()[0]

    success_rate = 1.0 - (error_count / activity_count) if activity_count > 0 else 1.0

    # Entity count from metrics table (if exists)
    try:
        cur = conn.execute("SELECT COUNT(DISTINCT entity_id) FROM metrics WHERE fihg = ?", (graph_name,))
        entity_count = cur.fetchone()[0] or 0
    except sqlite3.OperationalError:
        entity_count = 0

    # Average wear and freshness not stored centrally; use placeholders
    average_wear = 0.0
    average_freshness = 1.0

    conn.close()

    return {
        "graph_name": graph_name,
        "time_window": time_window,
        "cutoff_time": cutoff_dt,
        "activity_count": activity_count,
        "error_count": error_count,
        "success_rate": success_rate,
        "average_wear": average_wear,
        "average_freshness": average_freshness,
        "entity_count": entity_count,
        "computed_at": datetime.utcnow(),
    }


def get_skill_activation_stats() -> Dict:
    """Get activation statistics for the Skills FIHG.
    
    Returns:
        Dictionary with skill activation metrics including most/least activated
        skills, average activation count, and skill health indicators.
    """
    return {
        "total_skills": 0,
        "active_skills": 0,
        "inactive_skills": 0,
        "most_activated": None,
        "least_activated": None,
        "average_activation_count": 0.0,
        "average_success_rate": 1.0,
        "average_latency": 0.0,
        "skills_needing_refresh": [],
        "computed_at": datetime.utcnow(),
    }


def get_memory_retrieval_stats() -> Dict:
    """Get retrieval statistics for the Memory FIHG.
    
    Returns:
        Dictionary with memory retrieval metrics including retrieval counts,
        hit/miss rates, and memory freshness indicators.
    """
    return {
        "total_retrievals": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "average_freshness": 1.0,
        "average_trust": 1.0,
        "contradictions_found": 0,
        "most_retrieved": None,
        "stale_memories": [],
        "computed_at": datetime.utcnow(),
    }


def get_identity_confidence_stats() -> Dict:
    """Get confidence statistics for the Identity FIHG.
    
    Returns:
        Dictionary with identity confidence metrics including confidence levels,
        style consistency, and policy compliance scores.
    """
    return {
        "overall_confidence": 0.5,
        "style_consistency": 1.0,
        "policy_compliance": 1.0,
        "goal_alignment": 0.0,
        "identity_entities": 0,
        "high_confidence_count": 0,
        "low_confidence_count": 0,
        "confidence_distribution": {},
        "computed_at": datetime.utcnow(),
    }
