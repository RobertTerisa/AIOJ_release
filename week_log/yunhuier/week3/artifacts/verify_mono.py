"""第 3 周递增/递减生成器验收：跑 3 次录最慢，校验单调性、步长与值域。"""
import os
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(BASE, "bin")

# (exe 名, 是否递增)
VARIANTS = [("gen_increasing", True), ("gen_decreasing", False)]

for name, up in VARIANTS:
    outdir = os.path.join(BASE, "out", name)
    os.makedirs(outdir, exist_ok=True)
    target = os.path.join(outdir, "UVA10364.in")
    if os.path.exists(target):
        os.remove(target)

    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        proc = subprocess.run([os.path.join(BIN, name + ".exe")], cwd=outdir)
        times.append((time.perf_counter() - t0) * 1000.0)
        if proc.returncode != 0:
            raise SystemExit(f"{name} 运行失败 rc={proc.returncode}")

    tok = open(target, "r", encoding="ascii").read().split()
    t_case, n = int(tok[0]), int(tok[1])
    a = [int(x) for x in tok[2:]]

    steps = [a[i + 1] - a[i] for i in range(len(a) - 1)]
    if up:
        mono = all(s > 0 for s in steps)
    else:
        mono = all(s < 0 for s in steps)
    step_abs = [abs(s) for s in steps]

    checks = {
        "T==1": t_case == 1,
        "n==10^6": n == 1_000_000,
        "元素个数==n": len(a) == n,
        "严格单调": mono,
        "步长∈[1,100]": min(step_abs) >= 1 and max(step_abs) <= 100,
        "无元素<1": min(a) >= 1,
        "1s内": max(times) < 1000.0,
    }
    print(f"== {name} ({'递增' if up else '递减'})")
    print(f"   耗时(ms) 三次: {[round(t,1) for t in times]}  最慢 {round(max(times),1)}")
    print(f"   文件 {os.path.getsize(target)} B, 个数 {len(a)}, min {min(a)}, max {max(a)}")
    print(f"   首项 {a[0]}, 末项 {a[-1]}, 步长范围 [{min(step_abs)},{max(step_abs)}]")
    print(f"   判定 {'PASS' if all(checks.values()) else 'FAIL: ' + str([k for k,v in checks.items() if not v])}")
