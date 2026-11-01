// ===== UVA10364 数据生成器 · 全相等序列 =====
//
// 与模板的唯一差别：N = 1000000，且 ALL_SAME = true。
// 目的：制造「所有元素完全相等」的退化数据。这类数据专杀两类错误：
//       1) 排序后仍认为元素互异，或去重逻辑把相等的数当成不同数；
//       2) 早剪枝/贪心在第一组元素上就退化，递归深度或被除数直接爆掉。
//
// 注意上界：这里是 10000000（比另外两个变体的 1000000 大一个数量级），
// 按第 2 周任务单原文取 10000000，不是笔误——每个数会多占一个字节。
//
// 三条硬规则见 gen_template.cpp 顶部注释，本文件同样适用。
#include <bits/stdc++.h>
using namespace std;

// ======== 变体配置块 ========
static const int  N        = 1000000;   // 序列长度
static const int  VMIN     = 1;         // 元素下界
static const int  VMAX     = 10000000;  // 元素上界（任务单原文就是这个量级）
static const bool ALL_SAME = true;      // 全体元素等于同一个随机值
// ===========================

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    freopen("UVA10364.in", "w", stdout);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(VMIN, VMAX);
    const int fixed = dist(rng);  // 这一个值会被写满 1000000 遍

    cout << 1 << '\n';
    cout << N << '\n';
    for (int i = 0; i < N; ++i) {
        int v = ALL_SAME ? fixed : dist(rng);
        cout << v << (i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
