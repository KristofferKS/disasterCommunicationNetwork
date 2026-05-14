import sqlite3

con = sqlite3.connect('temp.db')
cur = con.cursor()



cursor = cur.execute(
"""
SELECT DISTINCT distance FROM tests 
WHERE environment = 'Urban'
ORDER BY distance
"""
)

#cursor = cur.execute(
#"""
#UPDATE tests
#SET distance = round(distance, -1)
#WHERE environment = 'Urban'
#"""
#)


for row in cursor:
    print(row)



#
#distances = [99, 130, 140, 141, 142, 150]
#
#for distance in distances:
#    print("Available distances in tests:")
#    for drow in cur.execute("select id, distance from tests where environment = 'Urban' AND distance = ? order by distance;", (distance,)):
#        print(drow)
#        pass
#

#    cursor = cur.execute(
#        """
#    DELETE FROM iterations
#    WHERE test_id IN (
#    SELECT id FROM tests WHERE environment = 'Urban' AND distance = ?)
#        """
#    , (distance,))
#
#    cursor = cur.execute(
#        """
#    DELETE FROM averages
#    WHERE test_id IN (
#    SELECT id FROM tests WHERE environment = 'Urban' AND distance = ?)
#        """
#    , (distance,))
#
#    cursor = cur.execute(
#        """DELETE FROM tests WHERE environment = 'Urban' AND distance = ?
#        """,
#        (distance,)
#    )

#distance = 400
#cursor = cur.execute(
#    """
#    update tests set test_name = ? where environment = 'LoS' and distance = ? and test_name = 'Test_05_12_1';
#    """,
#    (f'LoS Dock {distance}', distance)
#)

#cursor = cur.execute(
#    """
#DELETE FROM tests WHERE environment = 'Urban' AND distance = ?
#    """,
#    (distance,)
#)

# 99, 130, 140, 141, 142, 150

con.commit()
print(f"Updated {cursor.rowcount} rows.")

con.close()
