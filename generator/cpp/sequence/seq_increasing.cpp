// AIOJ 序列生成器 · 严格递增
//
// 规格来源：generator/Readme.md 第 5 节「C++ 生成器参数规格」
// 用法：
//   seq_increasing.exe --seed 123 --out a.in --append --array 10,1,60
//
// 只写 content 值：不写 T、不写 n、不写控制头（那些由路由写）。
// 每个 --array 输出一行，恰好「长度」个整数，严格递增且落在 [min, max]。
#include "../common.h"

// 单步最大增量。沿用第 3 周任务单的 rand(1, 100)；
// CLI 规格里 --array 只给 长度/最小值/最大值，步长上限不对外开放，所以写死在这里。
static const i64 STEP_MAX = 100;

struct ArraySpec {
    i64 len;
    i64 lo;
    i64 hi;
};

// 解析 "长度,最小值,最大值"，必须是恰好三段整数
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
            // 长度 0：仍要占一行（Readme 5.2「每个 --array 输出一行」）
            if (s.len == 0) {
                out << '\n';
                continue;
            }

            // 严格递增 n 个整数，至少需要 hi-lo >= n-1（每步至少 +1）
            const i64 span = s.hi - s.lo;
            if (span < s.len - 1)
                throw runtime_error("区间容纳不下严格递增序列：需要跨度至少 " +
                                    to_string(s.len - 1) + "，实际只有 " +
                                    to_string(span));

            // 起点要给后面每个元素留出至少 +1 的空间
            const i64 start_hi = s.hi - (s.len - 1);
            uniform_int_distribution<i64> start_dist(s.lo, start_hi);
            i64 cur = start_dist(rng);

            out << cur;
            for (i64 i = 1; i < s.len; ++i) {
                const i64 remain = s.len - 1 - i;          // 这一步之后还剩几个元素
                const i64 slack = (s.hi - cur) - remain;   // 这一步最多能加多少
                // 动态收缩：既不超过 STEP_MAX，也保证后面每个元素还有位置放
                const i64 cap = min<i64>(STEP_MAX, slack);
                if (cap < 1) throw runtime_error("内部错误：步长上界计算出 " + to_string(cap));
                uniform_int_distribution<i64> step_dist(1, cap);
                cur += step_dist(rng);
                out << ' ' << cur;
            }
            out << '\n';
        }

        if (!out) throw runtime_error("写入失败: " + args.out);
        return 0;
    } catch (const exception& e) {
        cerr << "[seq_increasing] " << e.what() << '\n';
        return 1;
    }
}
