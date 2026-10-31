from app.syslog.parser import parse


def test_normal_3164():
    raw = "<134>Oct 30 23:00:00 sw1 %LINK-3-UPDOWN: Interface Gi0/1, changed to down"
    r = parse(raw)
    assert r["ok"] is True
    assert r["rfc"] == 3164
    assert r["pri"] == 134
    assert r["facility"] == "local0"
    assert r["severity"] == 6
    assert r["level"] == "INFO"
    assert r["host"] == "sw1"
    assert "LINK-3-UPDOWN" in r["message"]


def test_auth_critical_maps_to_error():
    r = parse("<34>Oct 11 22:14:15 mymachine su: 'su root' failed")
    assert r["facility"] == "auth"
    assert r["severity_name"] == "Critical"
    assert r["level"] == "ERROR"
    assert r["host"] == "mymachine"


def test_local7_notice_maps_to_info():
    r = parse("<189>Oct 30 23:00:01 r1 IFNET/3/PHY_UPDOWN: Physical state changed to down")
    assert r["facility"] == "local7"
    assert r["severity_name"] == "Notice"
    assert r["level"] == "INFO"


def test_rfc5424_recognized():
    r = parse("<34>1 2003-10-11T22:14:15.003Z mymachine su - ID47 - BOM")
    assert r["ok"] is True
    assert r["rfc"] == 5424
    assert r["host"] == "mymachine"


def test_missing_pri_is_rejected():
    r = parse("Oct 30 23:00:00 sw1 no pri here")
    assert r["ok"] is False
    assert "PRI" in r["reason"]


def test_pri_out_of_range_is_rejected():
    r = parse("<999>garbage")
    assert r["ok"] is False
    assert "range" in r["reason"]


def test_bytes_input():
    """UDP 收到的是 bytes，不是 str"""
    r = parse(b"<134>Oct 30 23:00:00 sw1 hello")
    assert r["ok"] is True
    assert r["host"] == "sw1"


