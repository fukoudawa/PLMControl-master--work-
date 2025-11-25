import sqlite3
import json
import csv

db = sqlite3.connect(r"plm_control\Experiments\11-09-2025_.db")
cur = db.cursor()

data = cur.execute("SELECT timestamp_experimental, instruments_values FROM instruments").fetchall()
with open('data.csv', 'w', newline='') as csvfile:
    field_names = ["unix_timestamp", "pressure_1"]
    writer = csv.DictWriter(csvfile, fieldnames=field_names)
    # for row in range(len(data)):
    writer.writeheader()
    writer.writerows([{"unix_timestamp": data[i][0], "pressure_1": json.loads(data[i][1])["pressure_1"]} for i in range(len(data))])

