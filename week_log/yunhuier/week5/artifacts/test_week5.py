"""第 5 周验收：两段式（双峰）序列生成器。

只读仓库里的 exe，产物写到系统临时目录，不污染仓库。
"""
import hashlib
import os
import subprocess
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(tempfile.gettempdir(), "aioj_week5")


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


def run(args, timeout=60):
    return subprocess.run([os.path.join(BIN, "seq_bimodal.exe")] + args,
                          cwd=OUT, capture_output=True, timeout=timeout)


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def one(fn):
    with open(os.path.join(OUT, fn), "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    assert text.endswith("\n"), "文件必须以换行结尾"
    lines = [ln.split() for ln in text[:-1].split("\n")]
    assert len(lines) == 1, f"期望 1 行，实际 {len(lines)} 行"
    return [int(x) for x in lines[0]], raw


# ---------- 满量级 + 双峰形状 ----------
LO, HI = 1, 1000001          # span = 1000000，每段宽 300000
SPAN = HI - LO
BAND = SPAN * 3 // 10        # 300000
t = []
for _ in range(3):
    t0 = time.perf_counter()
    p = run(["--seed", "1", "--out", "big.in", "--array", f"1000000,{LO},{HI}"])
    t.append((time.perf_counter() - t0) * 1000)
v, raw = one("big.in")
check("满规模: 退出码 0", p.returncode == 0, p.stderr.decode()[:100])
check("满规模: 1e6 个元素", len(v) == 1000000, str(len(v)))
check("满规模: 无 CR 字节", b"\r" not in raw, "")
check("满规模: 耗时 < 1 s", min(t) < 1000, f"最快 {min(t):.0f} ms")

low = [x for x in v if LO <= x <= LO + BAND]
high = [x for x in v if HI - BAND <= x <= HI]
middle = [x for x in v if LO + BAND < x < HI - BAND]
check("双峰: 所有值都落在两段内", len(low) + len(high) == len(v), f"{len(low)}+{len(high)}={len(low)+len(high)}")
check("双峰: 中间 40% 一个值都没有", len(middle) == 0, f"中间段命中 {len(middle)} 个")
check("双峰: 两段都非空", len(low) > 0 and len(high) > 0, f"下段 {len(low)}，上段 {len(high)}")
ratio = len(high) / len(v)
check("双峰: 两段比例接近 50/50", 0.45 <= ratio <= 0.55, f"上段占比 {ratio:.1%}")
check("双峰: 段内仍然随机（不是常量）", len(set(low)) > 100 and len(set(high)) > 100,
      f"下段 {len(set(low))} 个不同值，上段 {len(set(high))} 个不同值")

# ---------- 退化：span ≤ 3 时静默退化成全区间随机 ----------
p = run(["--seed", "2", "--out", "deg.in", "--array", "20000,1,4"])
v, _ = one("deg.in")
mid_hit = [x for x in v if x in (2, 3)]
check("退化: span=3 时中间值能取到", p.returncode == 0 and len(mid_hit) > 0,
      f"2/3 出现 {len(mid_hit)} 次（共 {len(v)} 个）")
check("退化: 不报错、退出码 0", p.returncode == 0, p.stderr.decode()[:80])

p = run(["--seed", "3", "--out", "flat.in", "--array", "100,7,7"])
v, _ = one("flat.in")
check("退化: min=max 时全等于该值", p.returncode == 0 and set(v) == {7}, str(set(v)))

# 边界：span=4 时 band=1，两段各 2 个点，不应触发退化
p = run(["--seed", "4", "--out", "b4.in", "--array", "20000,1,5"])
v, _ = one("b4.in")
band4 = 4 * 3 // 10   # 1
allowed = set(range(1, 1 + band4 + 1)) | set(range(5 - band4, 6))
check("边界: span=4 仍走双峰（不退化）", p.returncode == 0 and set(v) <= allowed,
      f"取值集合 {sorted(set(v))}，允许 {sorted(allowed)}")

# ---------- 边界与格式 ----------
p = run(["--seed", "5", "--out", "z.in", "--array", "0,1,9"])
with open(os.path.join(OUT, "z.in"), "rb") as f:
    check("长度 0 输出空行", p.returncode == 0 and f.read() == b"\n", "")

p = run(["--seed", "6", "--out", "m.in", "--array", "5,1,100", "--array", "7,1,100"])
with open(os.path.join(OUT, "m.in"), "rb") as f:
    n = len(f.read().decode()[:-1].split("\n"))
check("多 --array 输出两行", p.returncode == 0 and n == 2, f"{n} 行")

# ---------- 确定性 ----------
run(["--seed", "2026", "--out", "d1.in", "--array", "1000,1,1000000"])
run(["--seed", "2026", "--out", "d2.in", "--array", "1000,1,1000000"])
a = open(os.path.join(OUT, "d1.in"), "rb").read()
b = open(os.path.join(OUT, "d2.in"), "rb").read()
check("同 seed 逐字节一致", hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), "")
run(["--seed", "2027", "--out", "d3.in", "--array", "1000,1,1000000"])
c = open(os.path.join(OUT, "d3.in"), "rb").read()
check("不同 seed 输出不同", a != c, "")

# ---------- 错误码 ----------
ERR = [
    ("缺少 --seed", ["--out", "x.in", "--array", "3,1,9"]),
    ("缺少 --array", ["--seed", "1", "--out", "x.in"]),
    ("缺少 --out", ["--seed", "1", "--array", "3,1,9"]),
    ("--array 格式错", ["--seed", "1", "--out", "x.in", "--array", "3,1"]),
    ("最小值 > 最大值", ["--seed", "1", "--out", "x.in", "--array", "3,9,1"]),
    ("未识别参数", ["--seed", "1", "--out", "x.in", "--array", "3,1,9", "--nope"]),
]
for label, args in ERR:
    p = run(args)
    check(f"错误码: {label}", p.returncode != 0 and p.stderr.strip() != b"",
          f"exit={p.returncode}, {p.stderr.decode('utf-8', 'replace').strip()[:60]}")

# ---------- 汇总 ----------
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"{name:<34} {'PASS' if ok else 'FAIL'}   {detail}")
print("-" * 74)
print(f"共 {len(results)} 项，失败 {bad} 项")
