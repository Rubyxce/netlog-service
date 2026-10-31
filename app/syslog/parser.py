import re
from datetime import datetime


FACILITY = {
    0: "kern", 1: "user", 3: "daemon", 4: "auth",
    16: "local0", 17: "local1", 18: "local2", 19: "local3",
    20: "local4", 21: "local5", 22: "local6", 23: "local7",
}

SEVERITY = {
    0: "Emergency", 1: "Alert", 2: "Critical", 3: "Error",
    4: "Warning", 5: "Notice", 6: "Informational", 7: "Debug",
}

# 有损映射
LEVEL = {
    0: "ERROR", 1: "ERROR", 2: "ERROR", 3: "ERROR",
    4: "WARNING", 5: "INFO", 6: "INFO", 7: "DEBUG",
}

PRI_RE = re.compile(r"<(\d{1,3})>")


def parse(raw):

    # UDP 的 recvfrom 返回值是 bytes,不是str,需要解码成字符串
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    # 用 match 抓PRI
    m = PRI_RE.match(raw)
    if not m:
        return {"ok": False, "reason": "missing PRI prefix"}

    pri = int(m.group(1))
    if pri > 191:
        return {"ok": False, "reason": f"PRI out of range:{pri}"}

    body = raw[m.end():]
    facility_id = pri // 8
    severity_id = pri % 8

    base = {
        "ok": True,
        "pri": pri,
        "facility": FACILITY.get(facility_id,"unknown"),
        "severity": severity_id,
        "severity_name": SEVERITY.get(severity_id,"unknown"),
        "level":LEVEL[severity_id],
    }

    # 区分切片
    # 先判断是不是 RFC 5424
    if body.startswith("1 "):
        parts = body.split(" ",6)
        base.update({
            "rfc":5424,
            "host":parts[2] if len(parts) > 2 else "",
            "ts":parts[1] if len(parts) > 1 else "",
            "message":parts[6] if len(parts) > 6 else "",
        })

        return base

    # RFC 3164
    parts = body.split(" ",4)
    if len(parts) < 5:
        return {"ok": False, "reason": "incomplete header"}

    # 补年份
    ts_raw = " ".join(parts[0:3])

    try:
        dt = datetime.strptime(
            f"{datetime.now().year} {ts_raw}", "%Y %b %d %H:%M:%S"
        )
    except ValueError:
        return {"ok": False, "reason": f"bad timestamp:{ts_raw}"}

    base.update({
        "rfc":3164,
        "host":parts[3],
        "ts":dt.strftime("%Y-%m-%d %H:%M:%S"),
        "message":parts[4],
    })

    return base