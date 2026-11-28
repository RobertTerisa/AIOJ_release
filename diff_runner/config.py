WORKSPACE_CONFIG_NAME = "aioj.workspace.json"

# 用户程序 TLE 熔断阈值：--tle-policy stop 时，收集到 5 组用户 TLE 后停止后续用例。
# 题解 TLE / 参考RE 不受此阈值影响，会立即熔断。
USER_TLE_CIRCUIT_BREAKER_LIMIT = 5

# 对拍所需题目文件缺失时的退出码。单独占一个值，是因为 2 已经表示
# “对拍完成但存在非 AC”，调用方（LLM / shell）需要把两者区分开。
INPUT_MISSING_EXIT_CODE = 3
