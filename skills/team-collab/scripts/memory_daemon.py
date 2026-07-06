#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""memory_daemon.py —— 常驻检索服务：模型+库只加载一次，之后每次召回毫秒级返回。

冷查询慢在"每次新进程都要 import chromadb/torch + 加载模型"(~15s)；本 daemon 启动时把这些一次性做完、
常驻监听 127.0.0.1 的一个端口，`query_memory.py` 把问题发来即秒回，跳过冷启动。底层库被
`build_memory_index.py` 重嵌后（chroma.sqlite3 mtime 变化）会自动重开 collection（模型不重载）。

用法（用装了 chromadb 的解释器——缺包时自动探测 python3/python/py 等候选，见 _vector_env.py）：
  python3 memory_daemon.py --person Alice            # 前台启动（Ctrl-C 停）
  python3 memory_daemon.py --person Alice --status   # 查是否在跑
  python3 memory_daemon.py --person Alice --stop     # 停

后台常驻：不用管，`query_memory.py` 在 daemon 没开时会自动把它拉起来（下次即秒回）。若想让它**开机就启**
（不必等第一次冷查询触发），按你的系统加一条自启项，指向本脚本 + `--person Alice --repo <仓库绝对路径>`：
  - **Windows**：任务计划程序（可视化界面）或 `schtasks /Create`（需管理员），或写入
    `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 注册表项（不需要管理员）；用 `pythonw.exe`
    （而非 `python.exe`）静默启动、不弹控制台窗口。
  - **macOS/Linux**：写一个 launchd plist（macOS）或 systemd user unit（Linux），`ExecStart` 指向
    `python3 .../memory_daemon.py --person Alice --repo <仓库绝对路径>`。
不管哪种方式，都用**绝对路径**（自启时 cwd 未定义，`resolve_repo()` 的 cwd 上溯派不上用场）。
"""
import argparse, hashlib, json, os, socket, socketserver, sys, threading
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _vector_env as ve
EMBED_MODEL = os.environ.get("TC_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
COLLECTION  = os.environ.get("TC_MEM_COLLECTION", "worklog_memory")

def vec_dir_for(person, repo):
    return os.path.join(repo, "团队协作记录", "智能体工作日志", person, "记忆向量库")

def port_for(vec_dir):
    env = os.environ.get("TC_MEM_DAEMON_PORT")
    if env:
        return int(env)
    h = int(hashlib.sha1(os.path.abspath(vec_dir).encode("utf-8")).hexdigest(), 16)
    return 49200 + (h % 15000)          # 每个 person/repo 一个稳定端口，互不撞

def portfile(vec_dir):
    return os.path.join(vec_dir, ".daemon.json")

def ping(port, timeout=1.5):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.sendall(b'{"cmd":"ping"}\n'); s.settimeout(timeout)
        ok = json.loads(s.recv(4096).decode().strip()).get("ok") is True
        s.close(); return ok
    except Exception:
        return False

# ───────────────────── 常驻状态：模型只加载一次；库变了自动重开 ─────────────────────
class State:
    def __init__(self, vec_dir, person):
        self.vec_dir = vec_dir; self.person = person
        self.lock = threading.Lock()
        self.ef = None; self.client = None; self.col = None; self.mtime = None

    def _sqlite(self):
        return os.path.join(self.vec_dir, "chroma.sqlite3")

    def _open(self):
        import chromadb
        ve.clear_orphan_hnsw(self.vec_dir)   # 清孤儿 pickle → 据 sqlite 重建索引，避免 'Cannot open header file'
        self.client = chromadb.PersistentClient(path=self.vec_dir)
        self.col = self.client.get_collection(COLLECTION, embedding_function=self.ef)
        self.mtime = os.path.getmtime(self._sqlite()) if os.path.exists(self._sqlite()) else None

    def load(self):
        from chromadb.utils import embedding_functions
        dev = os.environ.get("TC_MEM_DAEMON_DEVICE", "cpu")   # 常驻默认 CPU：不占显存，暖状态下单条查询也快
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL, device=dev)
        self._open()

    def query(self, q, k, kind, context=0):
        import query_memory as qm
        with self.lock:
            m = os.path.getmtime(self._sqlite()) if os.path.exists(self._sqlite()) else None
            if m != self.mtime:                # 库被重嵌过 → 重开 collection（模型不重载）
                self._open()
            return qm.search_and_format(self.col, q, k, kind, self.person, context)

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def make_handler(state, server):
    class H(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                line = self.rfile.readline().decode("utf-8").strip()
                req = json.loads(line) if line else {}
            except Exception as e:
                self.wfile.write((json.dumps({"error": f"bad request: {e}"}) + "\n").encode()); return
            cmd = req.get("cmd", "query")
            if cmd == "ping":
                self.wfile.write(b'{"ok": true}\n')
            elif cmd == "stop":
                self.wfile.write(b'{"ok": true, "stopping": true}\n')
                threading.Thread(target=server.shutdown, daemon=True).start()
            elif cmd == "query":
                try:
                    hits = state.query(req.get("query", ""), int(req.get("k", 6)), req.get("kind"), int(req.get("context", 0)))
                    self.wfile.write((json.dumps({"hits": hits}, ensure_ascii=False) + "\n").encode())
                except Exception as e:
                    self.wfile.write((json.dumps({"error": str(e)}, ensure_ascii=False) + "\n").encode())
            else:
                self.wfile.write((json.dumps({"error": f"unknown cmd {cmd}"}) + "\n").encode())
    return H

def main():
    ap = argparse.ArgumentParser(description="常驻记忆检索 daemon")
    ap.add_argument("--person", required=True)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--repo", help="仓库根（默认从 cwd 上溯自动找；登录项启动建议显式传入）")
    args = ap.parse_args()
    vd = vec_dir_for(args.person, ve.resolve_repo(args.person, args.repo))
    port = port_for(vd)
    ve.safe_console(os.path.join(vd, ".daemon.log"))   # 无控制台(pythonw/自启)→写日志；GBK 控制台→utf-8+replace

    if args.status:
        up = ping(port)
        print(f"记忆 daemon: {'RUNNING' if up else 'not running'} · 127.0.0.1:{port} · {vd}")
        return 0 if up else 1
    if args.stop:
        if ping(port):
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=2)
                s.sendall(b'{"cmd":"stop"}\n'); s.recv(1024); s.close()
                print("✓ 已停止")
            except Exception as e:
                print(f"停止时出错：{e}")
        else:
            print("daemon 未在运行")
        try: os.remove(portfile(vd))
        except OSError: pass
        return 0

    # 启动
    if not os.path.exists(os.path.join(vd, "chroma.sqlite3")):
        sys.exit(f"✗ 无记忆向量库：{vd}\n  先跑 build_memory_index.py --person {args.person}。")
    if ping(port):
        print(f"daemon 已在运行（127.0.0.1:{port}），无需重复启动。"); return 0
    ve.ensure_vector_stack(os.path.abspath(__file__))
    print(f"· 加载模型 {EMBED_MODEL} + 打开库 …", flush=True)
    state = State(vd, args.person); state.load()
    server = Server(("127.0.0.1", port), None)
    server.RequestHandlerClass = make_handler(state, server)
    json.dump({"port": port, "pid": os.getpid(), "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "collection": COLLECTION, "model": EMBED_MODEL},
              open(portfile(vd), "w", encoding="utf-8"), ensure_ascii=False)
    try: os.remove(os.path.join(vd, ".daemon.starting"))   # 就绪，清掉「防惊群」启动锁
    except OSError: pass
    print(f"✓ 记忆 daemon 就绪 · 127.0.0.1:{port} · {state.col.count()} 块常驻 · Ctrl-C 停", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for _f in (portfile(vd), os.path.join(vd, ".daemon.starting")):
            try: os.remove(_f)
            except OSError: pass
        print("daemon 已退出")

if __name__ == "__main__":
    main()
