"""第 4 周补充验收：随机小 / 随机大 / 全相等 三个 CLI 生成器。

只读仓库里的 exe，产物写到系统临时目录，不污染仓库。
"""
import hashlib
import os
import subprocess
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(tempfile.gettempdir(), "aioj_week4_extra")


def find_repo():
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


def run(exe, args, timeout=60):
    p = subprocess.run([os.path.join(BIN, exe + ".exe")] + args, cwd=OUT,
                       capture_output=True, timeout=timeout)
    return p


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def lines_of(fn):
    with open(os.path.join(OUT, fn), "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    assert text.endswith("\n"), "文件必须以换行结尾"
    return [ln.split() for ln in text[:-1].split("\n")], raw


def one(fn):
    ls, raw = lines_of(fn)
    assert len(ls) == 1, f"期望 1 行，实际 {len(ls)} 行"
    return [int(x) for x in ls[0]], raw


# ---------- 随机小 ----------
p = run("seq_random_small", ["--seed", "1", "--out", "s.in", "--array", "5000,1,1000000"])
v, raw = one("s.in")
check("随机小: 退出码 0", p.returncode == 0, p.stderr.decode()[:100])
check("随机小: 5000 个元素", len(v) == 5000, str(len(v)))
check("随机小: 落在 [1,1e6]", min(v) >= 1 and max(v) <= 10**6, f"min {min(v)} max {max(v)}")
check("随机小: 不是常量序列", len(set(v)) > 1, f"不同值 {len(set(v))} 个")
check("随机小: 无 CR 字节", b"\r" not in raw, "")

# ---------- 随机大 ----------
t = []
for _ in range(3):
    t0 = time.perf_counter()
    p = run("seq_random_large", ["--seed", "2", "--out", "l.in", "--array", "1000000,1,1000000"])
    t.append((time.perf_counter() - t0) * 1000)
v, raw = one("l.in")
check("随机大: 退出码 0", p.returncode == 0, p.stderr.decode()[:100])
check("随机大: 1e6 个元素", len(v) == 1000000, str(len(v)))
check("随机大: 落在 [1,1e6]", min(v) >= 1 and max(v) <= 10**6, f"min {min(v)} max {max(v)}")
check("随机大: 耗时 < 1 s", min(t) < 1000, f"最快 {min(t):.0f} ms")

# ---------- 全相等 ----------
t = []
for _ in range(3):
    t0 = time.perf_counter()
    p = run("seq_all_equal", ["--seed", "3", "--out", "e.in", "--array", "1000000,1,10000000"])
    t.append((time.perf_counter() - t0) * 1000)
v, _ = one("e.in")
check("全相等: 退出码 0", p.returncode == 0, p.stderr.decode()[:100])
check("全相等: 1e6 个元素", len(v) == 1000000, str(len(v)))
check("全相等: 只有一个不同值", len(set(v)) == 1, f"不同值 {len(set(v))} 个")
check("全相等: 落在 [1,1e7]", 1 <= v[0] <= 10**7, f"值 {v[0]}")
check("全相等: 耗时 < 1 s", min(t) < 1000, f"最快 {min(t):.0f} ms")

p = run("seq_all_equal", ["--seed", "4", "--out", "e2.in", "--array", "7,42,42"])
v, _ = one("e2.in")
check("全相等: min=max 时等于该值", p.returncode == 0 and set(v) == {42}, str(set(v)))

# ---------- 边界 ----------
for exe in ("seq_random_small", "seq_random_large", "seq_all_equal"):
    p = run(exe, ["--seed", "5", "--out", "z.in", "--array", "0,1,9"])
    raw = None
    with open(os.path.join(OUT, "z.in"), "rb") as f:
        raw = f.read()
    check(f"{exe}: 长度 0 输出空行", p.returncode == 0 and raw == b"\n", repr(raw))

for exe in ("seq_random_small", "seq_random_large", "seq_all_equal"):
    p = run(exe, ["--seed", "6", "--out", "m.in", "--array", "3,1,9", "--array", "4,1,9"])
    ls, _ = lines_of("m.in")
    check(f"{exe}: 多 --array 输出两行", p.returncode == 0 and len(ls) == 2, f"{len(ls)} 行")

# ---------- 确定性 ----------
for exe in ("seq_random_small", "seq_random_large", "seq_all_equal"):
    run(exe, ["--seed", "2026", "--out", "d1.in", "--array", "1000,1,1000000"])
    run(exe, ["--seed", "2026", "--out", "d2.in", "--array", "1000,1,1000000"])
    a = open(os.path.join(OUT, "d1.in"), "rb").read()
    b = open(os.path.join(OUT, "d2.in"), "rb").read()
    check(f"{exe}: 同 seed 逐字节一致", hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), "")
    run(exe, ["--seed", "2027", "--out", "d3.in", "--array", "1000,1,1000000"])
    c = open(os.path.join(OUT, "d3.in"), "rb").read()
    check(f"{exe}: 不同 seed 输出不同", a != c, "")

# ---------- 错误码 ----------
ERR = [
    ("缺少 --seed", ["--out", "x.in", "--array", "3,1,9"]),
    ("缺少 --array", ["--seed", "1", "--out", "x.in"]),
    ("缺少 --out", ["--seed", "1", "--array", "3,1,9"]),
    ("--array 格式错", ["--seed", "1", "--out", "x.in", "--array", "3,1"]),
    ("最小值 > 最大值", ["--seed", "1", "--out", "x.in", "--array", "3,9,1"]),
    ("未识别参数", ["--seed", "1", "--out", "x.in", "--array", "3,1,9", "--nope"]),
]
for exe in ("seq_random_small", "seq_random_large", "seq_all_equal"):
    for label, args in ERR:
        p = run(exe, args)
        check(f"{exe} 错误码: {label}", p.returncode != 0 and p.stderr.strip() != b"",
              f"exit={p.returncode}, {p.stderr.decode('utf-8', 'replace').strip()[:60]}")

# ---------- 汇总 ----------
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"{name:<44} {'PASS' if ok else 'FAIL'}   {detail}")
print("-" * 76)
print(f"共 {len(results)} 项，失败 {bad} 项")
