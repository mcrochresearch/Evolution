#!/usr/bin/env python3
"""
CORTEX — Persistent Hybrid Memory Engine for Evolution
======================================================

Takes the best ideas from:
  - OMEGA:     Typed coding-specific memories, dedup, conflict detection
  - Zep/Graphiti: Temporal validity windows, hybrid retrieval, graph traversal
  - Mem0:      Incremental extraction, confidence scoring
  - Letta:     3-tier hierarchy (core/recall/archival)

Architecture:
  Single SQLite database with FTS5 for keyword search, TF-IDF cosine
  similarity for semantic search, adjacency-list graph for relationships,
  and temporal validity tracking. Zero external dependencies beyond Python
  stdlib.

Usage:
  python3 engine/memory.py store <type> <content> [--context ...] [--files ...]
  python3 engine/memory.py recall <query> [--type ...] [--limit N]
  python3 engine/memory.py invalidate <id> [--reason ...]
  python3 engine/memory.py relate <id1> <id2> <relation>
  python3 engine/memory.py checkpoint --goal "..." --strategy "..." --cycle N
  python3 engine/memory.py resume
  python3 engine/memory.py consolidate
  python3 engine/memory.py stats
  python3 engine/memory.py gc
  python3 engine/memory.py export
  python3 engine/memory.py core [--refresh]
"""

import sqlite3
import json
import hashlib
import math
import re
import sys
import os
import uuid
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MEMORY_TYPES = [
    "decision",      # Architectural or technical decisions with rationale
    "bug-fix",       # What broke, why, and how it was fixed
    "pattern",       # Recurring successful approaches
    "architecture",  # Structural knowledge about the codebase
    "preference",    # User/project preferences and conventions
    "debug",         # Debugging insights and error resolutions
    "insight",       # General learnings and observations
    "warning",       # Things to avoid, known failure modes
    "procedure",     # Step-by-step recipes that work
    "goal-outcome",  # How goals ended: what worked, what didn't
]

RELATION_TYPES = [
    "supersedes",    # New memory replaces old one
    "contradicts",   # Memories conflict — needs resolution
    "supports",      # Evidence reinforcing another memory
    "related",       # Loose topical connection
    "depends-on",    # X only applies if Y is true
    "caused-by",     # X happened because of Y
    "fixes",         # X is the fix for problem Y
]

# How many seconds old a memory is before time decay kicks in
TIME_DECAY_HALF_LIFE_DAYS = 30

# Similarity threshold for deduplication
DEDUP_SIMILARITY_THRESHOLD = 0.85

# Max memories returned by default
DEFAULT_RECALL_LIMIT = 10

# Core memory max items (always loaded into context)
CORE_MEMORY_LIMIT = 20

STATE_DIR = "evolution/.state"
DB_PATH = os.path.join(STATE_DIR, "cortex.db")


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_db(db_path=None):
    """Get a connection to the memory database, creating it if needed."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id          TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            content     TEXT NOT NULL,
            context     TEXT DEFAULT '',
            source_session TEXT DEFAULT '',
            source_cycle   INTEGER,
            confidence  REAL DEFAULT 1.0,
            importance  REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            created_at  TEXT NOT NULL,
            valid_from  TEXT,
            valid_until TEXT,
            invalidated_by TEXT,
            tags        TEXT DEFAULT '[]',
            related_files TEXT DEFAULT '[]',
            content_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relationships (
            source_id   TEXT NOT NULL,
            target_id   TEXT NOT NULL,
            relation    TEXT NOT NULL,
            weight      REAL DEFAULT 1.0,
            created_at  TEXT NOT NULL,
            PRIMARY KEY (source_id, target_id, relation),
            FOREIGN KEY (source_id) REFERENCES memories(id),
            FOREIGN KEY (target_id) REFERENCES memories(id)
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            goal        TEXT DEFAULT '',
            current_task TEXT DEFAULT '',
            active_strategy TEXT DEFAULT '',
            cycle_number INTEGER DEFAULT 0,
            fitness     REAL DEFAULT 0.0,
            working_state TEXT DEFAULT '{}',
            files_in_progress TEXT DEFAULT '[]',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vocabulary (
            term        TEXT PRIMARY KEY,
            idf         REAL NOT NULL,
            doc_count   INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tfidf_vectors (
            memory_id   TEXT NOT NULL,
            term        TEXT NOT NULL,
            tfidf       REAL NOT NULL,
            PRIMARY KEY (memory_id, term),
            FOREIGN KEY (memory_id) REFERENCES memories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
        CREATE INDEX IF NOT EXISTS idx_memories_valid ON memories(valid_until);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash);
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id);
    """)

    # FTS5 — may not be available in all builds
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, context, tags, content='memories', content_rowid=rowid)
        """)
        # Triggers to keep FTS in sync
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, context, tags)
                VALUES (new.rowid, new.content, new.context, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, context, tags)
                VALUES ('delete', old.rowid, old.content, old.context, old.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, context, tags)
                VALUES ('delete', old.rowid, old.content, old.context, old.tags);
                INSERT INTO memories_fts(rowid, content, context, tags)
                VALUES (new.rowid, new.content, new.context, new.tags);
            END;
        """)
    except Exception:
        pass  # FTS5 not available — will fall back to LIKE queries

    conn.commit()


# ---------------------------------------------------------------------------
# Text processing (zero-dependency TF-IDF)
# ---------------------------------------------------------------------------

# Stop words for English — enough to be useful without a library
STOP_WORDS = frozenset(
    "a an and are as at be by for from has have he her his i in is it its "
    "me my no not of on or our s she so t that the their them then there "
    "these they this to us was we were what when which who will with you your "
    "been being do does doing done had having how if into just more most much "
    "nor only other own same should such than that those through too very "
    "would could should about after again all also am any because before between "
    "both but can did each few get got has here him himself how its itself let "
    "like may might must need new now off old once one our out over own part "
    "put right say see seem she since so some still such take tell than that "
    "the their them then there these they thing think this those time to too "
    "two up us use very want way we well what when where which while who why "
    "will with work would year".split()
)


def tokenize(text):
    """Split text into lowercase tokens, removing stop words and short tokens."""
    tokens = re.findall(r'[a-z][a-z0-9_.-]*[a-z0-9]|[a-z]', text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def compute_tf(tokens):
    """Compute term frequency for a token list."""
    counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {term: count / total for term, count in counts.items()}


def content_hash(content):
    """SHA-256 of normalized content for dedup."""
    normalized = re.sub(r'\s+', ' ', content.strip().lower())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# TF-IDF index management
# ---------------------------------------------------------------------------

def rebuild_idf(conn):
    """Recompute IDF values across all memories."""
    total_docs = conn.execute("SELECT COUNT(*) FROM memories WHERE valid_until IS NULL").fetchone()[0]
    if total_docs == 0:
        return

    # Count document frequency for each term
    term_doc_counts = Counter()
    rows = conn.execute("SELECT id, content, context FROM memories WHERE valid_until IS NULL").fetchall()
    for row in rows:
        text = f"{row['content']} {row['context']}"
        unique_terms = set(tokenize(text))
        for term in unique_terms:
            term_doc_counts[term] += 1

    # Write vocabulary
    conn.execute("DELETE FROM vocabulary")
    conn.executemany(
        "INSERT INTO vocabulary (term, idf, doc_count) VALUES (?, ?, ?)",
        [(term, math.log((total_docs + 1) / (count + 1)) + 1, count)
         for term, count in term_doc_counts.items()]
    )

    # Rebuild all TF-IDF vectors
    conn.execute("DELETE FROM tfidf_vectors")
    idf_map = {r['term']: r['idf'] for r in conn.execute("SELECT term, idf FROM vocabulary").fetchall()}

    batch = []
    for row in rows:
        text = f"{row['content']} {row['context']}"
        tf = compute_tf(tokenize(text))
        for term, tf_val in tf.items():
            idf_val = idf_map.get(term, 1.0)
            batch.append((row['id'], term, tf_val * idf_val))

    conn.executemany(
        "INSERT INTO tfidf_vectors (memory_id, term, tfidf) VALUES (?, ?, ?)",
        batch
    )
    conn.commit()


def index_single_memory(conn, memory_id, text):
    """Add TF-IDF vector for a single memory (incremental update)."""
    total_docs = conn.execute("SELECT COUNT(*) FROM memories WHERE valid_until IS NULL").fetchone()[0]
    tokens = tokenize(text)
    tf = compute_tf(tokens)

    # Use existing IDF values, with fallback
    idf_map = {r['term']: r['idf'] for r in conn.execute("SELECT term, idf FROM vocabulary").fetchall()}

    conn.execute("DELETE FROM tfidf_vectors WHERE memory_id = ?", (memory_id,))
    batch = []
    for term, tf_val in tf.items():
        idf_val = idf_map.get(term, math.log((total_docs + 1) / 2) + 1)
        batch.append((memory_id, term, tf_val * idf_val))

    if batch:
        conn.executemany(
            "INSERT INTO tfidf_vectors (memory_id, term, tfidf) VALUES (?, ?, ?)",
            batch
        )

    # Periodically rebuild IDF (every 50 memories)
    if total_docs % 50 == 0 and total_docs > 0:
        rebuild_idf(conn)


def cosine_similarity(conn, query_text, limit=50):
    """Compute cosine similarity between query and all memories using TF-IDF."""
    tokens = tokenize(query_text)
    if not tokens:
        return {}

    tf = compute_tf(tokens)
    idf_map = {r['term']: r['idf'] for r in conn.execute("SELECT term, idf FROM vocabulary").fetchall()}

    # Build query vector
    query_vec = {}
    for term, tf_val in tf.items():
        idf_val = idf_map.get(term, 0)
        if idf_val > 0:
            query_vec[term] = tf_val * idf_val

    if not query_vec:
        return {}

    # Query magnitude
    q_mag = math.sqrt(sum(v * v for v in query_vec.values()))
    if q_mag == 0:
        return {}

    # Get dot products with stored vectors
    placeholders = ','.join('?' * len(query_vec))
    terms = list(query_vec.keys())

    rows = conn.execute(f"""
        SELECT memory_id, term, tfidf
        FROM tfidf_vectors
        WHERE term IN ({placeholders})
    """, terms).fetchall()

    # Compute dot products
    dot_products = Counter()
    for row in rows:
        dot_products[row['memory_id']] += query_vec.get(row['term'], 0) * row['tfidf']

    # Get document magnitudes
    doc_mags = {}
    for mid in dot_products:
        mag_rows = conn.execute(
            "SELECT SUM(tfidf * tfidf) as mag2 FROM tfidf_vectors WHERE memory_id = ?",
            (mid,)
        ).fetchone()
        doc_mags[mid] = math.sqrt(mag_rows['mag2']) if mag_rows['mag2'] else 0

    # Cosine similarity
    scores = {}
    for mid, dot in dot_products.items():
        d_mag = doc_mags.get(mid, 0)
        if d_mag > 0:
            scores[mid] = dot / (q_mag * d_mag)

    return dict(sorted(scores.items(), key=lambda x: -x[1])[:limit])


# ---------------------------------------------------------------------------
# Hybrid retrieval engine
# ---------------------------------------------------------------------------

def hybrid_recall(conn, query, memory_type=None, limit=DEFAULT_RECALL_LIMIT,
                  include_expired=False, boost_graph=True):
    """
    Hybrid retrieval combining:
      1. FTS5 keyword search (BM25 ranking)
      2. TF-IDF cosine similarity (semantic)
      3. Graph traversal boost (connected memories score higher)
      4. Time decay (older = lower score)
      5. Access frequency boost (frequently useful = higher score)
      6. Importance weighting
    """
    now = datetime.utcnow().isoformat()
    scores = Counter()  # memory_id -> combined score

    # --- Pass 1: FTS5 keyword search ---
    fts_results = set()
    try:
        # Escape FTS5 special characters
        safe_query = re.sub(r'[^\w\s]', ' ', query)
        terms = safe_query.split()
        if terms:
            fts_query = ' OR '.join(terms)
            rows = conn.execute("""
                SELECT rowid, rank FROM memories_fts
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit * 3)).fetchall()

            for row in rows:
                # Convert rowid to memory id
                mem = conn.execute("SELECT id FROM memories WHERE rowid = ?", (row['rowid'],)).fetchone()
                if mem:
                    # BM25 rank is negative (lower = better), normalize to 0-1
                    bm25_score = min(1.0, -row['rank'] / 10.0) if row['rank'] else 0.0
                    scores[mem['id']] += bm25_score * 0.35  # 35% weight
                    fts_results.add(mem['id'])
    except Exception:
        # FTS5 not available — fall back to LIKE
        terms = tokenize(query)
        for term in terms[:5]:
            rows = conn.execute(
                "SELECT id FROM memories WHERE content LIKE ? OR context LIKE ?",
                (f'%{term}%', f'%{term}%')
            ).fetchall()
            for row in rows:
                scores[row['id']] += 0.07  # Small boost per matching term
                fts_results.add(row['id'])

    # --- Pass 2: TF-IDF cosine similarity ---
    semantic_scores = cosine_similarity(conn, query, limit=limit * 3)
    for mid, sim in semantic_scores.items():
        scores[mid] += sim * 0.35  # 35% weight

    # --- Pass 3: Filter by type and validity ---
    valid_ids = set()
    for mid in scores:
        mem = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
        if not mem:
            continue
        if memory_type and mem['type'] != memory_type:
            continue
        if not include_expired and mem['valid_until']:
            continue
        valid_ids.add(mid)

    scores = Counter({k: v for k, v in scores.items() if k in valid_ids})

    # --- Pass 4: Time decay ---
    for mid in list(scores):
        mem = conn.execute("SELECT created_at, importance, access_count FROM memories WHERE id = ?", (mid,)).fetchone()
        if mem and mem['created_at']:
            try:
                created = datetime.fromisoformat(mem['created_at'])
                age_days = (datetime.utcnow() - created).days
                decay = 0.5 ** (age_days / TIME_DECAY_HALF_LIFE_DAYS)
                scores[mid] *= (0.7 + 0.3 * decay)  # Decay affects 30% of score
            except (ValueError, TypeError):
                pass

            # Importance boost (15% weight)
            scores[mid] += (mem['importance'] or 0.5) * 0.15

            # Access frequency boost (15% weight) — diminishing returns
            access = mem['access_count'] or 0
            scores[mid] += min(0.15, math.log1p(access) * 0.03)

    # --- Pass 5: Graph traversal boost ---
    if boost_graph and scores:
        top_ids = [mid for mid, _ in scores.most_common(limit)]
        graph_boost = Counter()
        for mid in top_ids:
            # Find memories connected to top results
            rels = conn.execute("""
                SELECT target_id, weight FROM relationships WHERE source_id = ?
                UNION
                SELECT source_id, weight FROM relationships WHERE target_id = ?
            """, (mid, mid)).fetchall()
            for rel in rels:
                connected = rel[0]
                if connected in valid_ids:
                    graph_boost[connected] += rel[1] * 0.05  # Small boost

        for mid, boost in graph_boost.items():
            scores[mid] += min(boost, 0.15)  # Cap graph boost

    # --- Final: Sort and return top results ---
    top = scores.most_common(limit)
    results = []
    for mid, score in top:
        mem = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
        if mem:
            # Update access count
            conn.execute("""
                UPDATE memories SET access_count = access_count + 1,
                last_accessed = ? WHERE id = ?
            """, (now, mid))
            results.append({
                "id": mem['id'],
                "type": mem['type'],
                "content": mem['content'],
                "context": mem['context'],
                "confidence": mem['confidence'],
                "importance": mem['importance'],
                "created_at": mem['created_at'],
                "valid_until": mem['valid_until'],
                "tags": json.loads(mem['tags'] or '[]'),
                "related_files": json.loads(mem['related_files'] or '[]'),
                "access_count": (mem['access_count'] or 0) + 1,
                "score": round(score, 4),
            })

    conn.commit()
    return results


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def store_memory(conn, memory_type, content, context="", tags=None, files=None,
                 confidence=1.0, importance=0.5, session_id="", cycle=None):
    """Store a new memory with deduplication and conflict detection."""
    if memory_type not in MEMORY_TYPES:
        return {"error": f"Unknown type '{memory_type}'. Valid: {MEMORY_TYPES}"}

    c_hash = content_hash(content)
    now = datetime.utcnow().isoformat()

    # --- Deduplication: check for near-identical content ---
    existing = conn.execute(
        "SELECT id, content FROM memories WHERE content_hash = ? AND valid_until IS NULL",
        (c_hash,)
    ).fetchone()
    if existing:
        # Exact duplicate — boost confidence instead of storing again
        conn.execute("""
            UPDATE memories SET confidence = MIN(confidence + 0.1, 1.0),
            access_count = access_count + 1, last_accessed = ? WHERE id = ?
        """, (now, existing['id']))
        conn.commit()
        return {"status": "deduplicated", "existing_id": existing['id'],
                "message": "Near-identical memory exists. Confidence boosted."}

    # Semantic dedup — check TF-IDF similarity against existing memories
    similar = cosine_similarity(conn, f"{content} {context}", limit=3)
    for sim_id, sim_score in similar.items():
        if sim_score >= DEDUP_SIMILARITY_THRESHOLD:
            sim_mem = conn.execute("SELECT id, content, type FROM memories WHERE id = ?", (sim_id,)).fetchone()
            if sim_mem and sim_mem['type'] == memory_type:
                # Very similar — update existing instead
                conn.execute("""
                    UPDATE memories SET confidence = MIN(confidence + 0.1, 1.0),
                    access_count = access_count + 1, last_accessed = ? WHERE id = ?
                """, (now, sim_id))
                conn.commit()
                return {"status": "deduplicated_semantic", "existing_id": sim_id,
                        "similarity": round(sim_score, 3),
                        "message": f"Semantically similar memory exists (sim={sim_score:.2f}). Confidence boosted."}

    # --- Conflict detection: check for contradictions ---
    conflicts = []
    if memory_type in ("decision", "architecture", "preference"):
        # For decision-type memories, check if we have an existing one about the same topic
        candidates = cosine_similarity(conn, content, limit=5)
        for cand_id, cand_score in candidates.items():
            if cand_score > 0.5:  # Topically related
                cand = conn.execute(
                    "SELECT id, content, type FROM memories WHERE id = ? AND type = ? AND valid_until IS NULL",
                    (cand_id, memory_type)
                ).fetchone()
                if cand:
                    conflicts.append({"id": cand['id'], "content": cand['content'],
                                      "similarity": round(cand_score, 3)})

    # --- Store the memory ---
    mem_id = f"M{uuid.uuid4().hex[:8].upper()}"
    tags_json = json.dumps(tags or [])
    files_json = json.dumps(files or [])

    conn.execute("""
        INSERT INTO memories (id, type, content, context, source_session, source_cycle,
            confidence, importance, access_count, last_accessed, created_at, valid_from,
            tags, related_files, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
    """, (mem_id, memory_type, content, context, session_id, cycle,
          confidence, importance, now, now, now, tags_json, files_json, c_hash))

    # Index for TF-IDF
    index_single_memory(conn, mem_id, f"{content} {context}")

    # Auto-create contradiction relationships
    for conflict in conflicts:
        conn.execute("""
            INSERT OR IGNORE INTO relationships (source_id, target_id, relation, weight, created_at)
            VALUES (?, ?, 'contradicts', 1.0, ?)
        """, (mem_id, conflict['id'], now))

    conn.commit()

    result = {"status": "stored", "id": mem_id, "type": memory_type}
    if conflicts:
        result["conflicts"] = conflicts
        result["warning"] = f"Found {len(conflicts)} potentially conflicting memories. Consider invalidating old ones."
    return result


# ---------------------------------------------------------------------------
# Invalidate (temporal fact management, from Zep)
# ---------------------------------------------------------------------------

def invalidate_memory(conn, memory_id, superseded_by=None, reason=""):
    """Mark a memory as no longer valid (temporal invalidation)."""
    now = datetime.utcnow().isoformat()
    mem = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not mem:
        return {"error": f"Memory {memory_id} not found"}
    if mem['valid_until']:
        return {"error": f"Memory {memory_id} already invalidated"}

    conn.execute("""
        UPDATE memories SET valid_until = ?, invalidated_by = ? WHERE id = ?
    """, (now, superseded_by or reason, memory_id))

    if superseded_by:
        conn.execute("""
            INSERT OR IGNORE INTO relationships (source_id, target_id, relation, weight, created_at)
            VALUES (?, ?, 'supersedes', 1.0, ?)
        """, (superseded_by, memory_id, now))

    conn.commit()
    return {"status": "invalidated", "id": memory_id, "superseded_by": superseded_by}


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

def add_relationship(conn, source_id, target_id, relation, weight=1.0):
    """Create a typed relationship between two memories."""
    if relation not in RELATION_TYPES:
        return {"error": f"Unknown relation '{relation}'. Valid: {RELATION_TYPES}"}

    # Verify both exist
    for mid in (source_id, target_id):
        if not conn.execute("SELECT 1 FROM memories WHERE id = ?", (mid,)).fetchone():
            return {"error": f"Memory {mid} not found"}

    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO relationships (source_id, target_id, relation, weight, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (source_id, target_id, relation, weight, now))
    conn.commit()
    return {"status": "related", "source": source_id, "target": target_id, "relation": relation}


def get_related(conn, memory_id, relation=None):
    """Get all memories related to a given memory."""
    if relation:
        rows = conn.execute("""
            SELECT m.*, r.relation, r.weight
            FROM relationships r JOIN memories m ON m.id = r.target_id
            WHERE r.source_id = ? AND r.relation = ?
            UNION
            SELECT m.*, r.relation, r.weight
            FROM relationships r JOIN memories m ON m.id = r.source_id
            WHERE r.target_id = ? AND r.relation = ?
        """, (memory_id, relation, memory_id, relation)).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.*, r.relation, r.weight
            FROM relationships r JOIN memories m ON m.id = r.target_id
            WHERE r.source_id = ?
            UNION
            SELECT m.*, r.relation, r.weight
            FROM relationships r JOIN memories m ON m.id = r.source_id
            WHERE r.target_id = ?
        """, (memory_id, memory_id)).fetchall()

    return [{"id": r['id'], "type": r['type'], "content": r['content'],
             "relation": r['relation'], "weight": r['weight']} for r in rows]


# ---------------------------------------------------------------------------
# Session checkpoints (from OMEGA + Letta)
# ---------------------------------------------------------------------------

def save_checkpoint(conn, goal="", task="", strategy="", cycle=0, fitness=0.0,
                    working_state=None, files=None, session_id=None):
    """Save a session checkpoint for resume capability."""
    cp_id = f"CP{uuid.uuid4().hex[:8].upper()}"
    sess_id = session_id or f"S{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    now = datetime.utcnow().isoformat()

    conn.execute("""
        INSERT INTO checkpoints (id, session_id, goal, current_task, active_strategy,
            cycle_number, fitness, working_state, files_in_progress, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cp_id, sess_id, goal, task, strategy, cycle, fitness,
          json.dumps(working_state or {}), json.dumps(files or []), now))
    conn.commit()
    return {"status": "checkpoint_saved", "id": cp_id, "session_id": sess_id}


def load_checkpoint(conn, session_id=None):
    """Load the most recent checkpoint, optionally for a specific session."""
    if session_id:
        row = conn.execute("""
            SELECT * FROM checkpoints WHERE session_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (session_id,)).fetchone()
    else:
        row = conn.execute("""
            SELECT * FROM checkpoints ORDER BY created_at DESC LIMIT 1
        """).fetchone()

    if not row:
        return {"status": "no_checkpoint", "message": "No checkpoint found"}

    return {
        "status": "checkpoint_loaded",
        "id": row['id'],
        "session_id": row['session_id'],
        "goal": row['goal'],
        "current_task": row['current_task'],
        "active_strategy": row['active_strategy'],
        "cycle_number": row['cycle_number'],
        "fitness": row['fitness'],
        "working_state": json.loads(row['working_state'] or '{}'),
        "files_in_progress": json.loads(row['files_in_progress'] or '[]'),
        "created_at": row['created_at'],
    }


# ---------------------------------------------------------------------------
# Core memory (from Letta — always in context, like RAM)
# ---------------------------------------------------------------------------

def get_core_memory(conn, limit=CORE_MEMORY_LIMIT):
    """
    Get the most important active memories — the 'core' that should always
    be in the agent's context window. Ranked by importance * confidence * recency.
    """
    now = datetime.utcnow()
    rows = conn.execute("""
        SELECT * FROM memories
        WHERE valid_until IS NULL
        ORDER BY importance DESC, confidence DESC, created_at DESC
        LIMIT ?
    """, (limit * 2,)).fetchall()  # Fetch extra to re-rank

    scored = []
    for row in rows:
        try:
            created = datetime.fromisoformat(row['created_at'])
            age_days = max((now - created).days, 1)
            recency = 0.5 ** (age_days / TIME_DECAY_HALF_LIFE_DAYS)
        except (ValueError, TypeError):
            recency = 0.5

        score = (row['importance'] or 0.5) * (row['confidence'] or 0.5) * (0.5 + 0.5 * recency)
        scored.append((score, row))

    scored.sort(key=lambda x: -x[0])
    results = []
    for score, row in scored[:limit]:
        results.append({
            "id": row['id'],
            "type": row['type'],
            "content": row['content'],
            "confidence": row['confidence'],
            "importance": row['importance'],
            "tags": json.loads(row['tags'] or '[]'),
        })

    return results


def refresh_core_memory_file(conn):
    """Write core memory to a human-readable markdown file for CLAUDE.md injection."""
    core = get_core_memory(conn)
    if not core:
        return {"status": "empty", "message": "No memories to write"}

    lines = [
        "# Core Memory — Auto-Generated",
        "",
        "> This file is auto-generated by the Cortex memory engine.",
        "> It contains the most important active memories for the current session.",
        "> Do NOT edit manually — changes will be overwritten.",
        "",
    ]

    # Group by type
    by_type = {}
    for mem in core:
        by_type.setdefault(mem['type'], []).append(mem)

    type_order = ["decision", "architecture", "warning", "bug-fix", "pattern",
                  "procedure", "preference", "insight", "debug", "goal-outcome"]

    for mtype in type_order:
        mems = by_type.get(mtype, [])
        if not mems:
            continue
        lines.append(f"## {mtype.replace('-', ' ').title()}s")
        lines.append("")
        for mem in mems:
            conf_bar = "+" * int(mem['confidence'] * 5)
            tags = " ".join(f"`{t}`" for t in mem['tags']) if mem['tags'] else ""
            lines.append(f"- [{conf_bar}] {mem['content']} {tags}")
        lines.append("")

    output_path = os.path.join("evolution", "cortex", "core-memory.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    return {"status": "refreshed", "path": output_path, "count": len(core)}


# ---------------------------------------------------------------------------
# Consolidation (from Mem0 — incremental maintenance)
# ---------------------------------------------------------------------------

def consolidate(conn):
    """
    Memory maintenance:
      1. Decay confidence of old, unused memories
      2. Merge highly similar memories
      3. Detect and flag contradictions
      4. Rebuild TF-IDF index
    """
    now = datetime.utcnow()
    stats = {"decayed": 0, "merged": 0, "contradictions_found": 0, "gc_candidates": 0}

    # --- 1. Confidence decay for old, unused memories ---
    rows = conn.execute("""
        SELECT id, created_at, last_accessed, confidence, access_count
        FROM memories WHERE valid_until IS NULL
    """).fetchall()

    for row in rows:
        try:
            last_used = datetime.fromisoformat(row['last_accessed'] or row['created_at'])
            days_unused = (now - last_used).days
        except (ValueError, TypeError):
            days_unused = 30

        if days_unused > 60 and (row['access_count'] or 0) < 2:
            new_conf = max(0.1, (row['confidence'] or 1.0) * 0.95)
            conn.execute("UPDATE memories SET confidence = ? WHERE id = ?", (new_conf, row['id']))
            stats["decayed"] += 1

    # --- 2. Find merge candidates (highly similar active memories) ---
    active = conn.execute("""
        SELECT id, content, context, type FROM memories
        WHERE valid_until IS NULL ORDER BY created_at DESC
    """).fetchall()

    merged_ids = set()
    for i, mem in enumerate(active):
        if mem['id'] in merged_ids:
            continue
        similar = cosine_similarity(conn, f"{mem['content']} {mem['context']}", limit=5)
        for sim_id, sim_score in similar.items():
            if sim_id == mem['id'] or sim_id in merged_ids:
                continue
            if sim_score >= 0.90:  # Very similar
                sim_mem = conn.execute("SELECT type FROM memories WHERE id = ?", (sim_id,)).fetchone()
                if sim_mem and sim_mem['type'] == mem['type']:
                    # Keep the newer one, invalidate older
                    invalidate_memory(conn, sim_id, superseded_by=mem['id'], reason="consolidated_merge")
                    merged_ids.add(sim_id)
                    stats["merged"] += 1

    # --- 3. Rebuild TF-IDF index ---
    rebuild_idf(conn)

    # --- 4. Count GC candidates ---
    gc = conn.execute("""
        SELECT COUNT(*) FROM memories
        WHERE valid_until IS NOT NULL
        AND confidence < 0.2
        AND access_count < 2
    """).fetchone()[0]
    stats["gc_candidates"] = gc

    conn.commit()
    return stats


# ---------------------------------------------------------------------------
# Garbage collection
# ---------------------------------------------------------------------------

def garbage_collect(conn):
    """Remove invalidated low-value memories and their relationships."""
    # Only GC memories that are: invalidated AND low confidence AND rarely accessed
    candidates = conn.execute("""
        SELECT id FROM memories
        WHERE valid_until IS NOT NULL
        AND confidence < 0.3
        AND access_count < 3
        AND julianday('now') - julianday(valid_until) > 30
    """).fetchall()

    deleted = 0
    for row in candidates:
        mid = row['id']
        conn.execute("DELETE FROM tfidf_vectors WHERE memory_id = ?", (mid,))
        conn.execute("DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (mid, mid))
        conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
        deleted += 1

    # Clean old checkpoints (keep last 10)
    conn.execute("""
        DELETE FROM checkpoints WHERE id NOT IN (
            SELECT id FROM checkpoints ORDER BY created_at DESC LIMIT 10
        )
    """)

    conn.commit()
    return {"deleted": deleted}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats(conn):
    """Memory system statistics."""
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM memories WHERE valid_until IS NULL").fetchone()[0]
    expired = total - active
    relationships = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    checkpoints = conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
    vocab_size = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]

    type_counts = {}
    for row in conn.execute("SELECT type, COUNT(*) as c FROM memories WHERE valid_until IS NULL GROUP BY type").fetchall():
        type_counts[row['type']] = row['c']

    relation_counts = {}
    for row in conn.execute("SELECT relation, COUNT(*) as c FROM relationships GROUP BY relation").fetchall():
        relation_counts[row['relation']] = row['c']

    avg_confidence = conn.execute(
        "SELECT AVG(confidence) FROM memories WHERE valid_until IS NULL"
    ).fetchone()[0] or 0

    avg_importance = conn.execute(
        "SELECT AVG(importance) FROM memories WHERE valid_until IS NULL"
    ).fetchone()[0] or 0

    most_accessed = []
    for row in conn.execute("""
        SELECT id, type, content, access_count FROM memories
        WHERE valid_until IS NULL ORDER BY access_count DESC LIMIT 5
    """).fetchall():
        most_accessed.append({"id": row['id'], "type": row['type'],
                              "content": row['content'][:80], "accesses": row['access_count']})

    return {
        "total_memories": total,
        "active_memories": active,
        "expired_memories": expired,
        "relationships": relationships,
        "checkpoints": checkpoints,
        "vocabulary_size": vocab_size,
        "by_type": type_counts,
        "by_relation": relation_counts,
        "avg_confidence": round(avg_confidence, 3),
        "avg_importance": round(avg_importance, 3),
        "most_accessed": most_accessed,
    }


# ---------------------------------------------------------------------------
# Export (human-readable + JSON)
# ---------------------------------------------------------------------------

def export_all(conn):
    """Export all memories as JSON."""
    memories = []
    for row in conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall():
        memories.append({k: row[k] for k in row.keys()})

    rels = []
    for row in conn.execute("SELECT * FROM relationships").fetchall():
        rels.append({k: row[k] for k in row.keys()})

    cps = []
    for row in conn.execute("SELECT * FROM checkpoints ORDER BY created_at DESC").fetchall():
        cps.append({k: row[k] for k in row.keys()})

    return {"memories": memories, "relationships": rels, "checkpoints": cps}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: memory.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1]
    conn = get_db()

    try:
        if cmd == "store":
            # memory.py store <type> <content> [--context X] [--tags a,b] [--files a,b]
            # [--confidence N] [--importance N] [--session X] [--cycle N]
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: memory.py store <type> <content> [options]"}))
                sys.exit(1)

            mtype = sys.argv[2]
            content = sys.argv[3]
            kwargs = _parse_kwargs(sys.argv[4:])

            result = store_memory(
                conn, mtype, content,
                context=kwargs.get('context', ''),
                tags=kwargs.get('tags', '').split(',') if kwargs.get('tags') else None,
                files=kwargs.get('files', '').split(',') if kwargs.get('files') else None,
                confidence=float(kwargs.get('confidence', 1.0)),
                importance=float(kwargs.get('importance', 0.5)),
                session_id=kwargs.get('session', ''),
                cycle=int(kwargs['cycle']) if kwargs.get('cycle') else None,
            )
            print(json.dumps(result, indent=2))

        elif cmd == "recall":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: memory.py recall <query> [--type X] [--limit N]"}))
                sys.exit(1)

            query = sys.argv[2]
            kwargs = _parse_kwargs(sys.argv[3:])

            results = hybrid_recall(
                conn, query,
                memory_type=kwargs.get('type'),
                limit=int(kwargs.get('limit', DEFAULT_RECALL_LIMIT)),
                include_expired=kwargs.get('include-expired', 'false').lower() == 'true',
            )
            print(json.dumps({"count": len(results), "memories": results}, indent=2))

        elif cmd == "invalidate":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: memory.py invalidate <id> [--reason X] [--superseded-by X]"}))
                sys.exit(1)

            mem_id = sys.argv[2]
            kwargs = _parse_kwargs(sys.argv[3:])
            result = invalidate_memory(conn, mem_id,
                                       superseded_by=kwargs.get('superseded-by'),
                                       reason=kwargs.get('reason', ''))
            print(json.dumps(result, indent=2))

        elif cmd == "relate":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: memory.py relate <id1> <id2> <relation> [--weight N]"}))
                sys.exit(1)

            kwargs = _parse_kwargs(sys.argv[5:])
            result = add_relationship(conn, sys.argv[2], sys.argv[3], sys.argv[4],
                                      weight=float(kwargs.get('weight', 1.0)))
            print(json.dumps(result, indent=2))

        elif cmd == "related":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: memory.py related <id> [--relation X]"}))
                sys.exit(1)

            kwargs = _parse_kwargs(sys.argv[3:])
            results = get_related(conn, sys.argv[2], relation=kwargs.get('relation'))
            print(json.dumps({"count": len(results), "related": results}, indent=2))

        elif cmd == "checkpoint":
            kwargs = _parse_kwargs(sys.argv[2:])
            result = save_checkpoint(
                conn,
                goal=kwargs.get('goal', ''),
                task=kwargs.get('task', ''),
                strategy=kwargs.get('strategy', ''),
                cycle=int(kwargs.get('cycle', 0)),
                fitness=float(kwargs.get('fitness', 0.0)),
                working_state=json.loads(kwargs['state']) if kwargs.get('state') else None,
                files=kwargs.get('files', '').split(',') if kwargs.get('files') else None,
                session_id=kwargs.get('session'),
            )
            print(json.dumps(result, indent=2))

        elif cmd == "resume":
            kwargs = _parse_kwargs(sys.argv[2:])
            result = load_checkpoint(conn, session_id=kwargs.get('session'))
            print(json.dumps(result, indent=2))

        elif cmd == "core":
            kwargs = _parse_kwargs(sys.argv[2:])
            if kwargs.get('refresh', 'false').lower() == 'true':
                result = refresh_core_memory_file(conn)
                print(json.dumps(result, indent=2))
            else:
                core = get_core_memory(conn)
                print(json.dumps({"count": len(core), "core": core}, indent=2))

        elif cmd == "consolidate":
            result = consolidate(conn)
            print(json.dumps(result, indent=2))

        elif cmd == "gc":
            result = garbage_collect(conn)
            print(json.dumps(result, indent=2))

        elif cmd == "stats":
            result = get_stats(conn)
            print(json.dumps(result, indent=2))

        elif cmd == "export":
            result = export_all(conn)
            print(json.dumps(result, indent=2))

        elif cmd == "rebuild-index":
            rebuild_idf(conn)
            print(json.dumps({"status": "index_rebuilt"}))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}",
                              "commands": ["store", "recall", "invalidate", "relate", "related",
                                           "checkpoint", "resume", "core", "consolidate",
                                           "gc", "stats", "export", "rebuild-index"]}))
            sys.exit(1)

    finally:
        conn.close()


def _parse_kwargs(args):
    """Parse --key value pairs from argv."""
    kwargs = {}
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                kwargs[key] = 'true'
                i += 1
        else:
            i += 1
    return kwargs


if __name__ == '__main__':
    main()
