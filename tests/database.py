import sqlite3

conn = sqlite3.connect('tests.db')
cursor = conn.cursor()

cursor.execute("""
    create table if not exists test_results (
        id integer primary key autoincrement,
        test_name text not null,
        throughput real not null,
        environment text not null,
        distance real not null,
        packet_size integer not null,
        number_of_packets integer not null,
        duration real not null
    )
""")

cursor.execute("""
    create table if not exists test (
        id integer primary key autoincrement,
        test_id integer not null,
        throughput real not null
    )
""")

cursor.execute("""
    insert into test_results (test_name, throughput, environment, distance, packet_size, number_of_packets, duration)
    values (?, ?, ?, ?, ?, ?, ?)
""", ('Test 1', 1000000, 'indoor', 10, 1500, 1000, 60))

test_id = cursor.lastrowid

tests = [
    (test_id, 1000000),
    (test_id, 2000000),
    (test_id, 3000000)
]

cursor.executemany("""
    insert into test (test_id, throughput)
    values (?, ?)
""", tests)

conn.commit()