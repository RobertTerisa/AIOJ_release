// AIOJ 序列生成器 · 两段式（双峰）随机序列
//
// 规格来源：第 5 周任务单 + generator/Readme.md 第 5 节（CLI 契合同第 4 周）
// 用法：
//   seq_bimodal.exe --seed 123 --out a.in --append --array 1000000,1,1000000
//
// 构造方法（任务单原文）：
//   1. 区间1 = [i_max - (i_max-i_min)*3/10, i_max]（上 30%）
//      区间2 = [i_min, i_min + (i_max-i_min)*3/10]（下 30%）
//   2. 先掷布尔：0 取区间1，1 取区间2
//   3. 在选中的区间里取随机数
//   4. 区间范围不够时静默退化成普通随机
//
// 这类数据为什么要造：中间 40% 永远取不到值，所以「排序后二分找中位数」
// 「按平均值切分」「默认数据均匀分布」的解法会被逼出真实复杂度；
// 同时两段各自内部仍然随机，不会退化成常量序列。
#include "../common.h"

struct ArraySpec {
    i64 len;
    i64 lo;
    i64 hi;
};

static ArraySpec parse_array(const string& raw) {
    i64 len = 0, lo = 0, hi = 0;
    char tail = 0;
    if (sscanf(raw.c_str(), "%lld,%lld,%lld%c", &len, &lo, &hi, &tail) != 3)
        throw runtime_error("--array 格式错误，应为 长度,最小值,最大值：" + raw);
    if (len < 0) throw runtime_error("--array 长度不能为负：" + raw);
    if (lo > hi) throw runtime_error("--array 区间非法（最小值 > 最大值）：" + raw);
    return ArraySpec{len, lo, hi};
}

int main(int argc, char** argv) {
    try {
        // --seed 是必填项，但 parse_common 对缺省值不报错，所以先自己扫一遍
        bool has_seed = false;
        for (int i = 1; i < argc; ++i)
            if (string(argv[i]) == "--seed") has_seed = true;
        if (!has_seed) throw runtime_error("缺少 --seed");

        Args args = parse_common(argc, argv);

        vector<ArraySpec> specs;
        for (size_t i = 0; i < args.rest.size(); ++i) {
            const string& k = args.rest[i];
            if (k != "--array") throw runtime_error("未识别参数: " + k);
            if (i + 1 >= args.rest.size()) throw runtime_error("--array 缺少参数值");
            specs.push_back(parse_array(args.rest[++i]));
        }
        if (specs.empty()) throw runtime_error("至少需要一个 --array");

        ofstream out = open_out(args);
        mt19937_64 rng = make_rng(args.seed);

        for (const ArraySpec& s : specs) {
            if (s.len == 0) {   // 长度 0 仍占一行
                out << '\n';
                continue;
            }

            const i64 span = s.hi - s.lo;
            // 每段宽度 = span*3/10。span 在 1e9 量级，乘 3 不会溢出 64 位；
            // 若调用方给出接近 i64 上限的跨度，这里按文档约定由参数合法性兜住。
            const i64 band = span * 3 / 10;

            // 任务单第 4 条：区间范围不够时静默退化成普通随机。
            // 判据：每段宽度取整后不足 1，说明子区间只剩一个点（span ≤ 3），
            // 两边都只能输出端点，序列会退化成「只取两端」，失去随机意义。
            const bool degraded = (band < 1);

            uniform_int_distribution<int> coin(0, 1);
            uniform_int_distribution<i64> whole(s.lo, s.hi);
            uniform_int_distribution<i64> high_band(s.hi - band, s.hi);   // 区间1
            uniform_int_distribution<i64> low_band(s.lo, s.lo + band);    // 区间2

            for (i64 i = 0; i < s.len; ++i) {
                i64 v;
                if (degraded) {
                    v = whole(rng);
                } else if (coin(rng) == 0) {
                    v = high_band(rng);   // 布尔 0 → 区间1
                } else {
                    v = low_band(rng);    // 布尔 1 → 区间2
                }
                if (i) out << ' ';
                out << v;
            }
            out << '\n';
        }

        if (!out) throw runtime_error("写入失败: " + args.out);
        return 0;
    } catch (const exception& e) {
        cerr << "[seq_bimodal] " << e.what() << '\n';
        return 1;
    }
}
