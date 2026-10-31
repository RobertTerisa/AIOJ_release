// ===== UVA10364 数据生成器 · 模板 =====
//
// 作用：把一组数据写进当前目录的 UVA10364.in。
// 后面三个变体（random_small / random_large / all_equal）都从这里改出来，
// 只有「变体配置块」和元素取值范围不同，其余一律不动。
//
// 三条硬规则（做不到就会白跑）：
//   1) 用 cout 输出大文件必须先关同步流，否则 1e6 个数跑不进 1 秒；
//   2) 调试信息一律走 cerr —— cout 已经被 freopen 重定向进数据文件，
//      任何一句 cout 调试都会写进 .in，整份数据直接作废；
//   3) 随机种子取时钟 —— 写死种子会导致每次生成的数据完全一样。
#include <bits/stdc++.h>
using namespace std;

// ======== 变体配置块：换变体只改这四行 ========
static const int  N        = 10;       // 序列长度
static const int  VMIN     = 1;        // 元素下界（闭区间）
static const int  VMAX     = 1000000;  // 元素上界（闭区间）
static const bool ALL_SAME = false;    // true = 所有元素取同一个随机值
// ============================================

int main() {
    // 规则 1：关同步流 + 解绑 cin，cout 的吞吐量能提升一个量级
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // 之后所有写向 stdout 的内容都进文件，控制台上什么都看不到
    freopen("UVA10364.in", "w", stdout);

    // 规则 3：用高精度时钟做种子，避免同一秒内多次运行拿到同一组数据
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(VMIN, VMAX);
    const int fixed = dist(rng);  // ALL_SAME 为真时，全体元素都等于它

    // UVA10364 的输入格式：第一行 T（组数），每组第一行 n，第二行 n 个数
    cout << 1 << '\n';   // T = 1，单组数据
    cout << N << '\n';   // 这一组有 N 个数
    for (int i = 0; i < N; ++i) {
        int v = ALL_SAME ? fixed : dist(rng);
        // 行末用 '\n' 不用 endl：endl 每次都 flush，10^6 次会慢一个量级
        cout << v << (i + 1 == N ? '\n' : ' ');
    }
    return 0;
}
