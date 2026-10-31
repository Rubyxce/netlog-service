# 导入sqlite3模块
import sqlite3
# 这里是导入标准库datetime，用来生成真实合法时间的
from datetime import datetime,timedelta

import uuid


# 连接logs.db数据库
conn = sqlite3.connect("logs.db")

# 取游标，并赋值给cur
cur = conn.cursor()

# 在插入数据之前，我们要先在数据库分几个不同的列来存放不同数据
cur.execute(
        """CREATE TABLE IF NOT EXISTS logs(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id  TEXT    NOT NULL,
        device      TEXT    NOT NULL,
        level       TEXT    NOT NULL,
        message     TEXT,
        ts          TEXT
        )
        """
    )

# 加唯一索引确保数据不会因为客户端超时重试而重复，达成幂等
cur.execute(
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_logs_message_id 
        ON logs(message_id)"""
)


# 因为我们没有真实数据，所以可以用 在数据池轮换取用数据并组合的方式 伪造10000组数据
device_list = ["sw1","sw2","sw3","sw4"]
level_list = ["ERROR","WARNING","INFO","DEBUG"]
message_list = ["interface down","bgp peer timeout","cpu high","ospf up"]
base_time = datetime.now()
# 数据池做好了，我们现在要创建10000条数据
# 先定义一个列表batch 用来存放轮换的数据组合成的元组
batch_data = []

# 我们想要在数据池里选出不同组合的数据，可以用到for range 来实现轮换
for i in range(10000):
    dev = device_list[i % len(device_list)]
    lev = level_list[i % len(level_list)]
    msg = message_list[i % len(message_list)]
    ts = base_time + timedelta(seconds=i)
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    random_logs = (str(uuid.uuid4()),dev,lev,msg,ts_str)
    batch_data.append(random_logs)

# 10000条数据造好了，我们现在要用cur.executemany()进行多行插入操作
cur.executemany("INSERT INTO logs(message_id,device,level,message,ts) "
                "VALUES (?,?,?,?,?)"
                , batch_data)

conn.commit()
conn.close()


