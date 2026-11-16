// AIOJ 序列生成器 · 严格递减
//
// 规格来源：generator/Readme.md 第 5 节「C++ 生成器参数规格」
// 用法：
//   seq_decreasing.exe --seed 123 --out a.in --append --array 10,1,60
//
// 只写 content 值：不写 T、不写 n、不写控制头（那些由路由写）。
// 每个 --array 输出一行，恰好「长度」个整数，严格递减且落在 [min, max]。
#include "../common.h"

// 单步最大减量，与递增版对称
static const i64 STEP_MAX = 100;

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
            if (s.len == 0) {
                out << '\n';
                continue;
            }

            // 严格递减 n 个整数，同样要求跨度至少 n-1
            const i64 span = s.hi - s.lo;
            if (span < s.len - 1)
                throw runtime_error("区间容纳不下严格递减序列：需要跨度至少 " +
                                    to_string(s.len - 1) + "，实际只有 " +
                                    to_string(span));

            // 起点要给后面每个元素留出至少 -1 的空间
            const i64 start_lo = s.lo + (s.len - 1);
            uniform_int_distribution<i64> start_dist(start_lo, s.hi);
            i64 cur = start_dist(rng);

            out << cur;
            for (i64 i = 1; i < s.len; ++i) {
                const i64 remain = s.len - 1 - i;
                const i64 slack = (cur - s.lo) - remain;   // 这一步最多能减多少
                const i64 cap = min<i64>(STEP_MAX, slack);
                if (cap < 1) throw runtime_error("内部错误：步长上界计算出 " + to_string(cap));
                uniform_int_distribution<i64> step_dist(1, cap);
                cur -= step_dist(rng);
                out << ' ' << cur;
            }
            out << '\n';
        }

        if (!out) throw runtime_error("写入失败: " + args.out);
        return 0;
    } catch (const exception& e) {
        cerr << "[seq_decreasing] " << e.what() << '\n';
        return 1;
    }
}
