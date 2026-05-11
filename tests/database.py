import sqlite3

def get_conn():
    conn = sqlite3.connect('tests.db')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name TEXT NOT NULL,
            environment TEXT NOT NULL,
            distance REAL NOT NULL,
            packet_size INTEGER NOT NULL,
            number_of_packets INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS iterations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            iteration INTEGER NOT NULL,
            throughput REAL NOT NULL,
            jitter_ms REAL,
            packet_loss_iperf REAL,
            packet_loss_ping REAL,
            rtt_ms REAL,
            duration REAL NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS averages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL UNIQUE,
            throughput REAL NOT NULL,
            jitter_ms REAL,
            packet_loss_iperf REAL,
            packet_loss_ping REAL,
            rtt_ms REAL,
            duration REAL NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    conn.commit()
    return conn

def insert_test(conn, args):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tests (test_name, environment, distance, packet_size, number_of_packets)
        VALUES (?, ?, ?, ?, ?)
    """, (args.test_name, args.environment, args.distance, args.packet_size, args.number_of_packets))
    conn.commit()
    return cursor.lastrowid

def insert_iteration(conn, test_id, iteration, throughput, jitter_ms, packet_loss_iperf, packet_loss_ping, rtt_ms, duration):
    conn.execute("""
        INSERT INTO iterations (test_id, iteration, throughput, jitter_ms, packet_loss_iperf, packet_loss_ping, rtt_ms, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_id, iteration, throughput, jitter_ms, packet_loss_iperf, packet_loss_ping, rtt_ms, duration))
    conn.commit()

def insert_averages(conn, test_id):
    conn.execute("""
        INSERT OR REPLACE INTO averages (test_id, throughput, jitter_ms, packet_loss_iperf, packet_loss_ping, rtt_ms, duration)
        SELECT test_id,
               AVG(throughput),
               AVG(jitter_ms),
               AVG(packet_loss_iperf),
               AVG(packet_loss_ping),
               AVG(rtt_ms),
               AVG(duration)
        FROM iterations
        WHERE test_id = ?
        GROUP BY test_id
    """, (test_id,))
    conn.commit()

def get_averages(conn, test_id):
    row = conn.execute("""
        SELECT throughput, jitter_ms, packet_loss_iperf, packet_loss_ping, rtt_ms, duration FROM averages WHERE test_id = ?
    """, (test_id,)).fetchone()
    return {"throughput": row[0], "jitter_ms": row[1], "packet_loss_iperf": row[2], "packet_loss_ping": row[3], "rtt_ms": row[4], "duration": row[5]}