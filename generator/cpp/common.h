// AIOJ 数据生成器公共头（规格见 generator/Readme.md 第 5 节「C++ 生成器参数规格」）
// 约定见 9.1：每个模式一个独立 exe，放 generator/bin/<kind>/<exe>；
// 公共参数 --seed / --out / --append；只追加 content，不写控制变量、不写 JSON。
#pragma once
#include <bits/stdc++.h>
using namespace std;
using i64 = long long;

struct Args {
    i64 seed = 0;
    string out;
    bool append = false;
    vector<string> rest;   // 未识别的参数按顺序保留
};

inline Args parse_common(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        string k = argv[i];
        auto next = [&]() -> string {
            if (i + 1 >= argc) throw runtime_error("缺少参数值: " + k);
            return argv[++i];
        };
        if (k == "--seed") a.seed = stoll(next());
        else if (k == "--out") a.out = next();
        else if (k == "--append") a.append = true;
        else a.rest.push_back(k);
    }
    if (a.out.empty()) throw runtime_error("缺少 --out");
    return a;
}

inline ofstream open_out(const Args& a) {
    // 二进制模式：Windows 上文本模式会把 LF 翻成 CRLF，
    // 导致 .in 与路由写入的内容行尾不一致（9.1 要求统一为 LF）。
    ofstream f(a.out, (a.append ? ios::app : ios::trunc) | ios::binary);
    if (!f) throw runtime_error("无法写 " + a.out);
    return f;
}

inline mt19937_64 make_rng(i64 seed) {
    return mt19937_64((uint64_t)seed);
}
