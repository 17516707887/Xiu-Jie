# 阶段 3 任务拆解步骤
## 任务 1：帮我规划去上海的行程，带 2kg 行李，路程 300km，明天是几号
1. 调用 get_weather，参数：city = 上海
2. 调用 calculate_express_fee，参数：weight=2，distance=300
3. 调用 get_date_info，参数：offset_days=1
4. 整合结果，返回自然语言：上海当前天气：多云，温度 18℃~25℃，湿度 60%，东风 3 级，快递费总计 13.50 元，明天是 2026 年 03 月 04 日 周三。请根据天气和时间安排出行。

## 任务 2：我要去济南出差，带 3kg 文件，路程 500km，后天出发，需要准备什么？
1. 调用 get_weather，参数：city = 济南
2. 调用 calculate_express_fee，参数：weight=3，distance=500
3. 调用 get_date_info，参数：offset_days=2
4. 调用 get_travel_preparation，参数：city = 济南，weight=3，distance=500，travel_date = 后天
5. 整合结果，返回自然语言：济南当前天气：晴，温度 10℃~18℃，湿度 45%，西北风 2 级，快递费总计 18.50 元，后天是 2026 年 03 月 05 日 周四。去济南（后天）的出行建议：携带防晒霜、太阳镜、遮阳帽，建议使用双肩包，长途出行建议准备颈枕、眼罩、充电宝，同时注意晴的天气影响。请提前做好准备。
