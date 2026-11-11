"""第 4 周 CLI 生成器验收：覆盖 Readme 5.4 检查清单与 5.2 错误码表。

只读仓库里的 exe，产物全部落在本目录 out/ 下，不写仓库。
"""
import hashlib
import os
import subprocess
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
# 产物写到系统临时目录，避免把测试数据混进仓库
OUT = os.path.join(tempfile.gettempdir(), "aioj_week4_out")


def find_repo():
    """向上找包含 generator/cpp 的仓库根目录，避免把本机绝对路径写进仓库。"""
    p = BASE
    while True:
        if os.path.isdir(os.path.join(p, "generator", "cpp")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            raise SystemExit("找不到仓库根目录（应包含 generator/cpp）")
        p = parent


BIN = os.path.join(find_repo(), "generator", "bin", "sequence")
os.makedirs(OUT, exist_ok=True)

results = []


def run(exe, args, cwd=None, timeout=60):
    cmd = [os.path.join(BIN, exe + ".exe")] + args
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd or OUT, capture_output=True, timeout=timeout)
    return p, (time.perf_counter() - t0) * 1000.0


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def read_lines(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw


def parse(path):
    raw = read_lines(path)
    text = raw.decode("utf-8")
    lines = text.split("\n")
    assert lines[-1] == "", "文件必须以换行结尾"
    return [ln.split() for ln in lines[:-1]], raw


def nums(path):
    ls, raw = parse(path)
    assert len(ls) == 1
    return [int(x) for x in ls[0]], raw


# ---------- 1. 基本形状 ----------
f = os.path.join(OUT, "a.in")
p, _ = run("seq_increasing", ["--seed", "123", "--out", "a.in", "--array", "5,1,9"])
v, raw = nums(f)
check("递增: 退出码 0", p.returncode == 0, p.stderr.decode()[:120])
check("递增: 5 个元素", len(v) == 5, str(v))
check("递增: 严格单调", all(v[i] < v[i + 1] for i in range(len(v) - 1)), str(v))
check("递增: 落在 [1,9]", min(v) >= 1 and max(v) <= 9, str(v))
check("递增: 无 CR 字节", b"\r" not in raw, "")

# ---------- 2. 边界 ----------
p, _ = run("seq_increasing", ["--seed", "1", "--out", "b.in", "--array", "0,1,9"])
raw = read_lines(os.path.join(OUT, "b.in"))
check("长度 0: 空行且退出码 0", p.returncode == 0 and raw == b"\n", repr(raw))

p, _ = run("seq_increasing", ["--seed", "1", "--out", "c.in", "--array", "1,7,7"])
v, _ = nums(os.path.join(OUT, "c.in"))
check("长度 1 且 min=max: 输出 7", p.returncode == 0 and v == [7], str(v))

p, _ = run("seq_increasing", ["--seed", "9", "--out", "d.in", "--array", "5,1,1000000000"])
v, _ = nums(os.path.join(OUT, "d.in"))
check("大值 1e9: 正常", p.returncode == 0 and max(v) <= 10**9, str(v))

p, _ = run("seq_increasing", ["--seed", "5", "--out", "e.in", "--array", "1000000,1,1000000"])
v, _ = nums(os.path.join(OUT, "e.in"))
check("满规模 1e6: 个数正确", len(v) == 1_000_000, str(len(v)))
check(
    "满规模 1e6: 只能取 1..1e6 紧排列",
    v[0] == 1 and v[-1] == 1_000_000 and all(b - a == 1 for a, b in zip(v, v[1:])),
    f"{v[0]}..{v[-1]}",
)

# ---------- 3. 多 array 与追加 ----------
p, _ = run("seq_decreasing", ["--seed", "7", "--out", "f.in", "--array", "3,1,100", "--array", "4,200,300"])
ls, _ = parse(os.path.join(OUT, "f.in"))
check("多 array: 两行", p.returncode == 0 and len(ls) == 2, f"{len(ls)} 行")
check(
    "递减: 两行都严格递减且落在各自区间",
    all(int(b) < int(a) for a, b in zip(ls[0], ls[0][1:]))
    and all(int(b) < int(a) for a, b in zip(ls[1], ls[1][1:]))
    and 1 <= min(map(int, ls[0])) and max(map(int, ls[0])) <= 100
    and 200 <= min(map(int, ls[1])) and max(map(int, ls[1])) <= 300,
    f"{ls}",
)

p, _ = run("seq_increasing", ["--seed", "11", "--out", "g.in", "--array", "3,1,50"])
p, _ = run("seq_increasing", ["--seed", "12", "--out", "g.in", "--append", "--array", "3,1,50"])
ls, _ = parse(os.path.join(OUT, "g.in"))
check("--append: 追加成两行", p.returncode == 0 and len(ls) == 2, f"{len(ls)} 行")

# ---------- 4. 确定性 ----------
for exe in ("seq_increasing", "seq_decreasing"):
    for out in ("h1.in", "h2.in"):
        run(exe, ["--seed", "2026", "--out", out, "--array", "200,1,1000000"])
    b1 = read_lines(os.path.join(OUT, "h1.in"))
    b2 = read_lines(os.path.join(OUT, "h2.in"))
    check(f"{exe}: 同 seed 逐字节一致", hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest(), "")

run("seq_increasing", ["--seed", "2026", "--out", "h3.in", "--array", "200,1,1000000"])
run("seq_increasing", ["--seed", "2027", "--out", "h4.in", "--array", "200,1,1000000"])
check(
    "不同 seed 输出不同",
    read_lines(os.path.join(OUT, "h3.in")) != read_lines(os.path.join(OUT, "h4.in")),
    "",
)

# ---------- 5. 性能 ----------
t_best = None
for _ in range(3):
    p, ms = run("seq_increasing", ["--seed", "3", "--out", "i.in", "--array", "1000000,1,1000000000"])
    t_best = ms if t_best is None else min(t_best, ms)
check("1e6 元素耗时 < 1s", t_best < 1000, f"最快 {t_best:.0f} ms")

for name, exe in (("递增", "seq_increasing"), ("递减", "seq_decreasing")):
    p, ms = run(exe, ["--seed", "4", "--out", "j.in", "--array", "1000000,1,50000000"])
    v, _ = nums(os.path.join(OUT, "j.in"))
    ok = all(b > a for a, b in zip(v, v[1:])) if name == "递增" else all(b < a for a, b in zip(v, v[1:]))
    check(f"{name} 1e6 严格单调", p.returncode == 0 and ok, f"{ms:.0f} ms")

# ---------- 6. 错误码表 ----------
ERR = [
    ("缺少 --seed", "seq_increasing", ["--out", "err.in", "--array", "3,1,9"]),
    ("缺少 --array", "seq_increasing", ["--seed", "1", "--out", "err.in"]),
    ("缺少 --out", "seq_increasing", ["--seed", "1", "--array", "3,1,9"]),
    ("--array 格式错", "seq_increasing", ["--seed", "1", "--out", "err.in", "--array", "3,1"]),
    ("最小值 > 最大值", "seq_increasing", ["--seed", "1", "--out", "err.in", "--array", "3,9,1"]),
    ("未识别参数", "seq_increasing", ["--seed", "1", "--out", "err.in", "--array", "3,1,9", "--foo"]),
    ("区间容纳不下", "seq_increasing", ["--seed", "1", "--out", "err.in", "--array", "5,1,3"]),
]
for label, exe, args in ERR:
    p, _ = run(exe, args)
    check(
        f"错误码: {label}",
        p.returncode != 0 and p.stderr.strip() != b"",
        f"exit={p.returncode}, stderr={p.stderr.decode('utf-8', 'replace').strip()[:80]}",
    )

# ---------- 汇总 ----------
print(f"{'检查项':<36} 结果")
print("-" * 70)
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"{name:<36} {'PASS' if ok else 'FAIL'}   {detail}")
print("-" * 70)
print(f"共 {len(results)} 项，失败 {bad} 项")
