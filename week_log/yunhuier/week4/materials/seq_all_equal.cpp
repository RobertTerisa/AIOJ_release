// AIOJ 序列生成器 · 全相等序列（CLI 版）
//
// 规格来源：generator/Readme.md 第 5 节「C++ 生成器参数规格」
// 用法：
//   seq_all_equal.exe --seed 123 --out a.in --append --array 1000000,1,10000000
//
// 与第 2 周 gen_all_equal 的对应关系：那一版把 N=1e6、值域 [1,1e7] 写死，并自己写 T/n；
// 本版只写 content，每个 --array 先在该区间里随机抽一个值，再把它写满「长度」遍。
// 这类退化数据专杀两类错误：把相等的数当互异（去重/剪枝逻辑），以及贪心在第一项就退化。
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
            uniform_int_distribution<i64> dist(s.lo, s.hi);
            const i64 fixed = dist(rng);   // 这一个值会被写满「长度」遍
            for (i64 i = 0; i < s.len; ++i) {
                if (i) out << ' ';
                out << fixed;
            }
            out << '\n';
        }

        if (!out) throw runtime_error("写入失败: " + args.out);
        return 0;
    } catch (const exception& e) {
        cerr << "[seq_all_equal] " << e.what() << '\n';
        return 1;
    }
}
