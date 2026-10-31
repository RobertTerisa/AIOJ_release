// ===== UVA10364 数据生成器 · 随机小序列 =====
//
// 与模板的唯一差别：N 从 10 改成 5000。
// 目的：小规模随机数据，用来跑正确性对拍 —— 规模小，答案容易肉眼核对，
//       出问题时也能直接在本地复现。
//
// 三条硬规则见 gen_template.cpp 顶部注释，本文件同样适用。
#include <bits/stdc++.h>
using namespace std;

// ======== 变体配置块 ========
static const int  N        = 5000;      // 序列长度
static const int  VMIN     = 1;         // 元素下界
static const int  VMAX     = 1000000;   // 元素上界
static const bool ALL_SAME = false;     // 随机小序列，元素各不相同
// ===========================

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    freopen("UVA10364.in", "w", stdout);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(VMIN, VMAX);
    const int fixed = dist(rng);

    cout << 1 << '\n';
    cout << N << '\n';
    for (int i = 0; i < N; ++i) {
        int v = ALL_SAME ? fixed : dist(rng);
        cout << v << (i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
