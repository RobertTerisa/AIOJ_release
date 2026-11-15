// AIOJ 序列生成器 · 随机小序列（CLI 版）
//
// 规格来源：generator/Readme.md 第 5 节「C++ 生成器参数规格」
// 用法：
//   seq_random_small.exe --seed 123 --out a.in --append --array 5000,1,1000000
//
// 与第 2 周 gen_random_small 的对应关系：那一版把 N=5000、值域 [1,1e6] 写死在源码里，
// 同时自己写 T 和 n；本版只写 content（每行一个数组），规模与值域全部由 --array 给出，
// T 和 n 交由路由器按 spec 写。
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
            uniform_int_distribution<i64> dist(s.lo, s.hi);
            for (i64 i = 0; i < s.len; ++i) {
                if (i) out << ' ';
                out << dist(rng);
            }
            out << '\n';
        }

        if (!out) throw runtime_error("写入失败: " + args.out);
        return 0;
    } catch (const exception& e) {
        cerr << "[seq_random_small] " << e.what() << '\n';
        return 1;
    }
}
