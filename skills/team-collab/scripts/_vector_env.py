#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_vector_env.py —— 语义记忆三兄弟(build_memory_index.py / query_memory.py / memory_daemon.py)
共用的两件小事：定位仓库根、确保 chromadb+sentence-transformers 可用。不是 skill 入口，不单独运行。

抽出来是因为三份脚本原样复制了这两段——改一处漏两处最容易漂移（见 CONTRIBUTING「保持自包含」精神：
仓库外路径不硬编码，同类逻辑不三处重复）。
"""
import os, subprocess, sys

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")   # 关掉 chromadb 遥测噪声（否则 stderr 混入、2>&1 时污染 --json）


def resolve_repo(person=None, explicit=None):
    """稳健定位仓库根：显式 --repo/$TC_REPO ＞ 从 cwd 上溯找 团队协作记录/智能体工作日志[/person] ＞
    脚本上溯4级(scripts/team-collab/skills/.claude/<repo>)。这样无论用**全局**还是**项目本地**装的
    脚本路径调用，只要 cwd 在仓库内（或传 --repo）都能找对库——修过一个真实的坑：全局副本上溯4级
    会解析到用户主目录而不是当前仓库，cwd 却明明在仓库里。"""
    cand = explicit or os.environ.get("TC_REPO")
    if cand:
        return os.path.abspath(cand)
    d = os.path.abspath(os.getcwd())
    while True:
        wl = os.path.join(d, "团队协作记录", "智能体工作日志")
        if (person and os.path.isdir(os.path.join(wl, person))) or (not person and os.path.isdir(wl)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def clear_orphan_hnsw(vec_dir):
    """chromadb（本机版本）有时写 index_metadata.pickle 却不落 hnsw *.bin → 加载/查询时报
    'Cannot open header file'。删掉**无对应 .bin** 的孤儿 pickle → 下次据 sqlite 重建索引、恢复可查。
    有 .bin（合法索引）则不动。build/query/daemon 打开 collection 前调用，令语义召回稳。"""
    import glob
    for seg in glob.glob(os.path.join(vec_dir, "*")):
        if not os.path.isdir(seg):
            continue
        pk = os.path.join(seg, "index_metadata.pickle")
        if os.path.exists(pk) and not glob.glob(os.path.join(seg, "*.bin")):
            try:
                os.remove(pk)
            except OSError:
                pass


def _probe(cmd):
    """cmd（如 ["python3"]）能不能 import chromadb+sentence_transformers？不产生副作用，只探测。"""
    try:
        r = subprocess.run(cmd + ["-c", "import chromadb, sentence_transformers"],
                           capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False


def safe_console(logpath=None):
    """让本进程的 stdout/stderr **永不因控制台编码或无控制台而崩**——中文/emoji 在非 UTF-8 控制台
    （如 Windows 默认 GBK）上 print 会 UnicodeEncodeError；无控制台运行（pythonw / 计划任务 / 某些
    自启方式）时 sys.stdout 干脆是 None。策略：有流就 reconfigure 成 utf-8+errors=replace；没有就转写
    到 logpath（没给 logpath 就转成内存缓冲，至少不崩）。在任何 print 之前调用一次即可。"""
    def _fix(s):
        if s is None:
            if logpath:
                try:
                    return open(logpath, "a", encoding="utf-8")
                except Exception:
                    pass
            import io
            return io.StringIO()
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        return s
    sys.stdout = _fix(sys.stdout)
    sys.stderr = _fix(sys.stderr)


def ensure_vector_stack(script_path):
    """当前解释器缺 chromadb/sentence-transformers 时，探测几个通用候选解释器、找到能用的就重新
    exec 本脚本（透传所有参数）。候选顺序：$TC_VECTOR_PYTHON（显式指定）→ python3 → python →
    （仅 Windows）py -3.12 / py -3（Windows 官方 launcher，很多机器把装了这些包的环境放在某个具体
    版本号下，比默认 `python` 新）。全部探测失败才报错——不要求用户必须叫某个特定路径。"""
    try:
        import chromadb, sentence_transformers  # noqa: F401
        return
    except ImportError:
        pass
    # 一段可直接粘贴的「建独立 venv 装依赖」命令（按平台）——两处失败提示复用，别让用户自己想
    # （见 team-collab/references/install-and-build-issues.md#1.4）。
    if os.name == "nt":
        _venv_tip = ("  ③ 建独立 venv（推荐）：\n"
                     "     py -3.12 -m venv %USERPROFILE%\\.venvs\\tc-vector\n"
                     "     %USERPROFILE%\\.venvs\\tc-vector\\Scripts\\pip install chromadb sentence-transformers\n"
                     "     set TC_VECTOR_PYTHON=%USERPROFILE%\\.venvs\\tc-vector\\Scripts\\python.exe")
    else:
        _venv_tip = ("  ③ 建独立 venv（推荐，跨项目复用、不污染仓库）：\n"
                     "     python3 -m venv ~/.venvs/tc-vector\n"
                     "     ~/.venvs/tc-vector/bin/pip install chromadb sentence-transformers\n"
                     "     export TC_VECTOR_PYTHON=~/.venvs/tc-vector/bin/python")
    if os.environ.get("_TC_MEM_REEXEC"):
        sys.exit("✗ 当前解释器缺 chromadb / sentence-transformers。任选其一：\n"
                 "  ① 当前解释器 `pip install chromadb sentence-transformers`；\n"
                 "  ② 设 TC_VECTOR_PYTHON 指向已装好它们的解释器；\n"
                 + _venv_tip)

    candidates = []
    if os.environ.get("TC_VECTOR_PYTHON"):
        candidates.append([os.environ["TC_VECTOR_PYTHON"]])
    candidates.append(["python3"])
    candidates.append(["python"])
    if os.name == "nt":
        candidates.append(["py", "-3.12"])
        candidates.append(["py", "-3"])

    env = {**os.environ, "_TC_MEM_REEXEC": "1", "PYTHONIOENCODING": "utf-8"}
    for cmd in candidates:
        if _probe(cmd):
            print(f"  （当前解释器无 chromadb，转到 `{' '.join(cmd)}` 运行）", flush=True)
            sys.exit(subprocess.run(cmd + [script_path, *sys.argv[1:]], env=env).returncode)
    sys.exit("✗ 找不到装了 chromadb/sentence-transformers 的 Python。任选其一：\n"
             "  ① 当前解释器 `pip install chromadb sentence-transformers`；\n"
             "  ② 设环境变量 TC_VECTOR_PYTHON 指向一个已装好它们的解释器（如某 conda 环境的 python）；\n"
             + _venv_tip)
