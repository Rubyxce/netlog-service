# 接入真实设备

把交换机 / Linux 主机的 syslog 发到本服务。以 VMware 里的 Ubuntu 22.04 为例。

## 0. 先看怎么工作的

```
设备 (rsyslog / 交换机)
        │  UDP 514 或 1514
        ▼
宿主机 receiver.py  ──▶  logs.db
        ▲
        │  必须监听 0.0.0.0，不能是 127.0.0.1
        │
   防火墙放行 UDP 1514
```

三个环节缺一不可：**设备发得出 → 网络到得了 → 宿主机收得下**。

## 1. 查宿主机 IP

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match 'VMnet' }
```

```
InterfaceAlias                IPAddress
VMware Network Adapter VMnet8 192.168.20.1    ← NAT 模式
VMware Network Adapter VMnet1 192.168.10.1    ← 仅主机模式
```

VM 用哪种网络模式就取哪个地址。后面用 `<宿主机IP>` 代指。

## 2. 确认网络通

在 VM 里：

```bash
ping -c 3 192.168.20.1
```

**ping 不通就先解决网络模式**（VM 设置 → 网络适配器 → 桥接 / NAT / 仅主机），后面都白搭。

> `ping` 走 ICMP，syslog 走 UDP，是两套规则。ping 通不代表 UDP 能到，但 ping 不通基本可以放弃。

## 3. 配置 rsyslog 转发

在 VM 里：

```bash
# @ = UDP，@@ = TCP；1514 是 receiver 的端口，不是标准 514
echo '*.* @192.168.20.1:1514' | sudo tee /etc/rsyslog.d/50-forward.conf

sudo systemctl restart rsyslog
sudo systemctl status rsyslog --no-pager
```

## 4. 启动接收器

宿主机，项目根目录：

```powershell
.\.venv\Scripts\python.exe -m app.syslog.receiver
```

成功时输出：

```
syslog 接收器启动，监听 0.0.0.0:1514
```

这是**独立进程**，和 `uvicorn` 并行跑，两者共用 `logs.db`。

## 5. 验证

VM 里手动发一条：

```bash
logger -n 192.168.20.1 -P 1514 -d "hello from vm"
```

宿主机上查：

```powershell
curl.exe -H "Authorization: Bearer <你的token>" "http://127.0.0.1:8000/logs?q=hello&n=3"
```

能看到 `hello from vm` 就通了。

也可以直接看数据库：

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3;c=sqlite3.connect('logs.db');print(c.execute('SELECT id,ts,device,level,substr(message,1,50) FROM logs ORDER BY id DESC LIMIT 5').fetchall())"
```

## 网络设备（非 Linux）

Cisco：

```
logging host 192.168.20.1
logging trap informational
```

华为 / 华三：

```
info-center enable
info-center loghost 192.168.20.1
```

注意：多数设备默认往 **UDP 514** 发。要么把设备端口改成 1514，要么改 `receiver.py` 里的 `PORT`
（Linux 上用 514 需要 root）。

## 收不到日志时的排查顺序

按这个顺序查，能覆盖 95% 的情况：

### ① 接收器在监听吗

```powershell
Get-NetUDPEndpoint -LocalPort 1514
```

没有输出说明 receiver 没启动。

### ② 防火墙放行了吗

```powershell
Get-NetFirewallProfile | Select-Object Name, Enabled
```

`Public` 默认是开的。如果 VM 网络被识别成「公用」，UDP 包会被丢。

**Windows 上 Block 规则优先于 Allow 规则**——某些软件会把 `python.exe` 的入站连接全禁掉，
这时加多少 Allow 都没用：

```powershell
Get-NetFirewallRule -PolicyStore ActiveStore | Where-Object {
  $_.Action -eq "Block" -and $_.Direction -eq "Inbound" -and $_.Enabled -eq "True"
} | Select-Object DisplayName, Profile
```

有拦 python 的规则就禁用：

```powershell
Disable-NetFirewallRule -DisplayName "python.exe"
```

### ③ 设备真的发出去了吗

在 VM 里抓包：

```bash
sudo tcpdump -i any -n udp port 1514
```

有包说明设备侧正常，问题在宿主机；没包说明 rsyslog 配置没生效。

### ④ 报文解析失败了吗

receiver 会把坏包记日志：

```
坏包 from ('192.168.20.135', 514): 时间格式错误
```

常见原因：

| 原因 | 现象 |
|---|---|
| 缺 `<PRI>` 前缀 | 部分设备发的是纯文本 |
| PRI 越界 | 值不在 0-191 内 |
| 时间格式不认 | 非 RFC 3164 / 5424 |

## 几个容易踩的细节

**RFC 3164 的日期是 `Mmm dd`，1-9 号用两个空格补齐**

```
<134>Nov  1 09:05:00 sw1 message      ← 注意 Nov 和 1 之间是两个空格
```

解析器必须用 `split(None, 4)`：按**任意空白**切分。
用 `split(" ", 4)` 会切出空字符串，拼出的时间戳缺时分秒，导致**每月 1-9 号的日志全部被丢弃**。

**重复报文是正常的**

rsyslog 断线重连、设备重试都会重复投递。`message_id = "syslog:" + sha256(报文)` 保证只入库一次，
重复的计入「重复」计数，不是错误。

**syslog 不会持续刷屏**

只有系统产生事件（启动、登录、服务启停、cron）才发一条。开机那一波可能有几百条，之后长时间为零——
这是正常的，不代表链路断了。想造数据用 `simulate.py`。
