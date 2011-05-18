#!/usr/bin/env python
import yapc.core as core
import yapc.log.output as output
import yapc.log.sqlite as sqlite
import os
import time

server = core.core()
output.set_mode("VDBG")

filename="testing.sqlite"
try:
    os.remove(filename)
except OSError:
    pass

db = sqlite.DB(server, filename)
server.run(runbg=True)

db.add_table(sqlite.Table("Test1", ["col1", "col2"]))
db.add_table(sqlite.Table("Test2", ["col12", "col22"]))
db.create_tables()
db.tables["Test1"].add_row((1.0,2.0))
db.tables["Test1"].add_row((2.0,2.0))
db.tables["Test1"].add_row((3.0,2.0))
db.tables["Test2"].add_row(("3.0",20))
db.flush()

for row in db.tables["Test1"].select():
    print row
for row in db.tables["Test2"].select():
    print row

time.sleep(1)
server.cleanup()
