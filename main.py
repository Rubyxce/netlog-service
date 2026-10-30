# 先从 fastapi模块 导入 FastAPI工具
import sqlite3

from fastapi import FastAPI,HTTPException

from pydantic import BaseModel

# 创建一个 FastAPI 应用实例，变量名叫 app
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}



@app.get("/logs")
def get_logs(device:str = None, level:str = None, n : int = 10,page : int = 1):
    """按设备以及级别查询，并加入了分页和翻页功能"""
    sql = "SELECT * FROM logs"
    # 建立一个参数列表
    params = []
    # 建立一个条件列表
    conditions = []

    if device is not None:
        """如果device不为空，在条件列表里加入device的查询条件
        并将device加入参数列表"""
        conditions.append("device = ?")
        params.append(device)

    if level is not None:
        """原理同上"""
        conditions.append("level = ?")
        params.append(level)

    if conditions:
        """如果查询条件列表不为空，则把条件拼接进基础sql语句里"""
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

    # 这里是分页功能设计部分
    offset =  (page - 1) * n
    sql += " LIMIT ? OFFSET ?"
    params.append(n)
    params.append(offset)

    # 连接数据库
    conn = sqlite3.connect("logs.db")

    # 让每行能按列名取值,比如 row["device"] 也能取到“sw1” ,效果跟 row[0] 一样
    conn.row_factory = sqlite3.Row
    # 取游标，用execute执行拼接好的sql语句
    cur = conn.cursor()
    cur.execute(sql, params)

    #把本次查询命中的所有行一次性拿出来，装成一个列表
    response = cur.fetchall()

    #关闭连接
    conn.close()

    # 循环遍历response里的 sqlite3.row对象，并将其转换成Python原生字典，组成一个新列表
    data = [dict(row) for row in response]

    return {
        "data": data,
        "page": page,
        "size": n
    }

@app.get("/stats")
def get_stats(device:str = None, level:str = None):
    conn = sqlite3.connect("logs.db")
    cur = conn.cursor()

    # 先拿各级别数据的条数
    cur.execute("""SELECT level ,COUNT(*) AS cnt FROM logs
        GROUP BY level
    """)
    rows_level = cur.fetchall()
    dict_level = {level: cnt for level, cnt in rows_level}

    # 再拿各设备数据的条数
    cur.execute("""SELECT device,COUNT(*) AS cnt FROM logs
                GROUP BY device""")
    rows_device = cur.fetchall()
    dict_device = {device: cnt for device, cnt in rows_device}

    conn.close()
    # 把两个类别的字典组成一个大字典
    dict_levanddev = {"by_level": dict_level, "by_device": dict_device}

    return dict_levanddev

# 定义一个数据形状，确保用户插入的数据符合要求
class LogItem(BaseModel):
    device: str
    level: str
    message: str
    ts: str

@app.post("/logs")
def post_logs(logs:list[LogItem]):
    """把用LogItem类得到的 Pydantic的对象 转换成普通字典 并插入数据库logs.db"""
    # 先检测输入的数值是否符合本数据库的标准,不符合直接抛异常，错误数据不会进入数据库
    allow_level = {"ERROR","WARNING","INFO","DEBUG"}
    errors = []

    # enumerate拿到下标idx，标记是上传列表里第几条出错
    for idx, item in enumerate(logs):
        # 单条里面多条校验
        if item.level not in allow_level:
            errors.append(f"第{idx}条：level非法：{item.level}")
        if item.device.strip() == "":
            errors.append(f"第{idx}条：device不能为空")
        if item.message.strip() == "":
            errors.append(f"第{idx}条：message不能为空")
        if item.ts.strip() == "":
            errors.append(f"第{idx}条：ts不能为空")

    # 全部检查完之后统一判断
    if errors:
        raise HTTPException(status_code=400, detail=" | ".join(errors))

    # 先建立一个空列表用于存放将要被转换的数据
    insert_data = []

    for item in logs:
        """用 for循环 从logs里面取出单个item 将其转换为普通字典
        按建表时的字段顺序 拼成元组"""
        d = item.model_dump()
        row_tuple = (d["device"],d["level"],d["message"],d["ts"])
        insert_data.append(row_tuple)

    conn = sqlite3.connect("logs.db")
    cur = conn.cursor()
    cur.executemany("""INSERT INTO logs(device,level,message,ts)
                VALUES (?,?,?,?)""",
                    insert_data)

    # 插入操作后要提交到数据库
    conn.commit()

    # cur.rowcount 是游标自带的属性：上一次 execute /executemany 操作，影响到多少行
    insert_num = cur.rowcount
    # 关闭连接
    conn.close()

    return {"inserted": insert_num}

@app.get("/logs/{log_id}")
def get_logs_by_id(log_id:int = 0):
    conn = sqlite3.connect("logs.db")
    cur = conn.cursor()
    cur.execute("""SELECT * FROM logs WHERE id = ?""", (log_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Log not found")
    else:
        return {"log":row}



