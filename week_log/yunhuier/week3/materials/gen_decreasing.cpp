// ===== UVA10364 数据生成器 · 严格递减序列 =====
//
// 生成规则（第 3 周任务单原文）：
//     A[i] = A[i-1] - rand(1, 100)，要求 A[i-1] > A[i]
//     终点落在 1，所以整条序列落在 [1, 1 + N*均值] 内，严格递减。
//
// 为什么不能“从 10^6 往下减”：
//     N=10^6 项、每项至少减 1，总跨度下限就是 10^6；按 rand(1,100) 的均值 50.5，
//     跨度约 5.05×10^7。若从 10^6 起减，减到第 2×10^4 项就变成负数了。
//     正确做法是先定“终点 = 1”，起点 = 1 + 全部步长之和，
//     这样递减序列的值域与递增序列完全对称，都落在 [1, 5.05×10^7]。
//
// 实现细节：步长之和要先知道，才能定起点，所以扫两遍。
//     两遍用同一个种子重建随机数发生器，保证第二遍拿到的步长序列与第一遍一致，
//     于是 next(seed) 固定时结果是确定的，而不用为 10^6 个步长开一个数组。
#include <bits/stdc++.h>
using namespace std;

// ======== 本变体的常量 ========
static const int       N        = 1000000;  // 序列长度，与“随机大”一致
static const long long END      = 1;        // 终点，保证所有元素 >= 1
static const int       STEP_MIN = 1;        // 步长下界（闭区间）
static const int       STEP_MAX = 100;      // 步长上界（闭区间）
// ==============================

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    freopen("UVA10364.in", "w", stdout);

    const long long seed = static_cast<long long>(
        chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> step_dist(STEP_MIN, STEP_MAX);

    // 第一遍：只累加总跨度，不输出
    long long span = 0;
    {
        mt19937_64 rng(seed);
        for (int i = 0; i < N; ++i) span += step_dist(rng);
    }

    cout << 1 << '\n';  // T = 1
    cout << N << '\n';  // 本组 n

    // 第二遍：同一个种子重建发生器，得到与第一遍完全相同的步长序列
    mt19937_64 rng(seed);
    long long cur = END + span;  // 起点 = 终点 + 总跨度，绝不小于 1
    for (int i = 0; i < N; ++i) {
        cur -= step_dist(rng);  // 每步至少 -1，所以严格递减
        cout << cur << (i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
