// ===== UVA10364 数据生成器 · 严格递增序列 =====
//
// 生成规则（第 3 周任务单原文）：
//     A[i] = A[i-1] + rand(1, 100)，要求 A[i-1] < A[i]
//     起点取 1，所以整条序列落在 [1, 1 + N*均值] 内，严格递增。
//
// 关于取值范围和 long long：
//     任务单要求“数据范围参考随机大”（N = 10^6）。但 N=10^6 项、每项至少 +1，
//     跨度下限就是 10^6；按 rand(1,100) 的均值 50.5 算，跨度约 5.05×10^7。
//     也就是说，元素不可能同时落在上一周的 [1, 10^6] 里——这两个要求互斥。
//     本实现保留 N=10^6 的规模，把数值上界放宽到约 5.05×10^7，
//     因此累加变量必须用 long long，避免乘法/累加溢出。
//
// 三条硬规则同上一周：关同步流、调试用 cerr、种子取时钟。
#include <bits/stdc++.h>
using namespace std;

// ======== 本变体的常量 ========
static const int       N        = 1000000;  // 序列长度，与“随机大”一致
static const long long START    = 1;        // 起点，保证所有元素 >= 1
static const int       STEP_MIN = 1;        // 步长下界（闭区间）
static const int       STEP_MAX = 100;      // 步长上界（闭区间）
// ==============================

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    freopen("UVA10364.in", "w", stdout);

    // 种子取高精度时钟：同一秒内多次运行也不会生成同一组数据
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> step_dist(STEP_MIN, STEP_MAX);

    cout << 1 << '\n';  // T = 1
    cout << N << '\n';  // 本组 n

    long long cur = START;  // long long：累加后最大约 5.05×10^7，用 int 在更大规模下会溢出
    for (int i = 0; i < N; ++i) {
        cur += step_dist(rng);  // 每步至少 +1，所以严格递增
        cout << cur << (i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
