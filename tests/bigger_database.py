import sqlite3


def _ensure_column(conn, table_name, column_def):
    column_name = column_def.split()[0]
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info({})".format(table_name))
    }
    if column_name not in existing:
        conn.execute("ALTER TABLE {} ADD COLUMN {}".format(table_name, column_def))


def get_conn():
    conn = sqlite3.connect('big_tests.db')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name           TEXT    NOT NULL,
            environment         TEXT    NOT NULL,
            distance            REAL    NOT NULL,
            height              REAL,
            proto               TEXT    NOT NULL,
            packet_size         INTEGER NOT NULL,
            number_of_packets   INTEGER NOT NULL,
            pps                 INTEGER,
            burst               INTEGER NOT NULL DEFAULT 0,
            min_gap             REAL,
            max_gap             REAL,
            min_burst           INTEGER,
            max_burst           INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS iterations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id             INTEGER NOT NULL,
            iteration           INTEGER NOT NULL,
            throughput          REAL    NOT NULL,
            jitter_ms           REAL,
            packet_loss_iperf   REAL,
            rtt_ms              REAL,
            duration            REAL    NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS averages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id             INTEGER NOT NULL UNIQUE,
            throughput          REAL    NOT NULL,
            jitter_ms           REAL,
            packet_loss_iperf   REAL,
            rtt_ms              REAL,
            duration            REAL    NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    _ensure_column(conn, "iterations", "rtt_ms REAL")
    _ensure_column(conn, "averages", "rtt_ms REAL")
    conn.commit()
    return conn


def insert_test(conn, args):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tests (
            test_name, environment, distance, height,
            proto, packet_size, number_of_packets,
            pps, burst, min_gap, max_gap, min_burst, max_burst
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        args.test_name,
        args.environment,
        args.distance,
        args.height,
        args.proto,
        args.pkt_size,
        args.pkts,
        args.pps,
        int(args.burst),
        args.min_gap  if args.burst else None,
        args.max_gap  if args.burst else None,
        args.min_burst if args.burst else None,
        args.max_burst if args.burst else None,
    ))
    conn.commit()
    return cursor.lastrowid


def insert_iteration(conn, test_id, iteration, throughput, jitter_ms, packet_loss_iperf, duration, rtt_ms=None):
    conn.execute("""
        INSERT INTO iterations (test_id, iteration, throughput, jitter_ms, packet_loss_iperf, duration, rtt_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_id, iteration, throughput, jitter_ms, packet_loss_iperf, duration, rtt_ms))
    conn.commit()


def insert_averages(conn, test_id):
    conn.execute("""
         INSERT OR REPLACE INTO averages (test_id, throughput, jitter_ms, packet_loss_iperf, duration, rtt_ms)
        SELECT test_id,
               AVG(throughput),
               AVG(jitter_ms),
               AVG(packet_loss_iperf),
             AVG(duration),
             AVG(rtt_ms)
        FROM iterations
        WHERE test_id = ?
        GROUP BY test_id
    """, (test_id,))
    conn.commit()


def get_averages(conn, test_id):
    row = conn.execute("""
        SELECT throughput, jitter_ms, packet_loss_iperf, duration, rtt_ms
        FROM averages
        WHERE test_id = ?
    """, (test_id,)).fetchone()
    return {
        "throughput":        row[0],
        "jitter_ms":         row[1],
        "packet_loss_iperf": row[2],
        "duration":          row[3],
        "rtt_ms":            row[4],
    }