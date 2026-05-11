SYSTEM_PROMPT = """你是DataForge-AI-Powered-One-Stop-Data-Analysis-Platform-Introduction的专业助手。你的任务是帮助用户分析数据、生成可视化图表、提炼关键结论、清洗和预处理数据。

你可以使用以下工具来完成任务：
- analyze_data: 执行数据分析（基础统计、趋势、对比、关联等）
- generate_chart: 生成可视化图表
- summarize: 提炼关键结论和建议
- preprocess_data: 数据清洗与预处理，支持以下操作：
  - auto_clean: 一键自动清洗（去重+填充缺失值）
  - fill_missing: 填充缺失值（mean/median/mode/drop）
  - fill_forward/fill_backward: 前向/后向填充
  - fill_value: 用指定值填充
  - drop_duplicates: 去除重复值
  - deduplicate_subset: 按指定列去重
  - remove_outliers: 去除异常值（iqr/zscore）
  - trim_whitespace: 去除首尾空白
  - standardize_case: 大小写标准化（lower/upper/title）
  - convert_dtype: 类型转换（int/float/str/datetime）
  - rename_columns: 重命名列
  - drop_columns: 删除列
  - drop_rows: 按条件删除行

当用户上传数据后，你会收到数据的基本信息（列名、数据类型、预览数据）。
根据用户的自然语言指令，选择合适的工具来完成任务。

回复规则：
1. 用简洁直白的中文回复
2. 分析完成后，自动推荐合适的图表类型
3. 提炼核心结论时，用要点形式列出
4. 如果用户指令不明确，主动询问具体需求
5. 如果用户要求清洗数据，直接调用 preprocess_data 工具执行"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "对数据执行分析操作，包括基础统计、趋势分析、对比分析、关联分析、异常检测等",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["basic_stats", "trend", "compare", "correlation", "anomaly", "distribution"],
                        "description": "分析类型",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要分析的列名",
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组列名（用于对比分析）",
                    },
                },
                "required": ["analysis_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "生成可视化图表",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["line", "bar", "pie", "scatter", "radar", "heatmap", "box", "area", "china_map", "world_map"],
                        "description": "图表类型",
                    },
                    "x_column": {"type": "string", "description": "X轴列名"},
                    "y_column": {"type": "string", "description": "Y轴列名"},
                    "group_by": {"type": "string", "description": "分组/颜色列名"},
                    "title": {"type": "string", "description": "图表标题"},
                },
                "required": ["chart_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "基于分析结果提炼关键结论、问题和建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "总结关注的重点方向",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preprocess_data",
            "description": "数据预处理与清洗：填充缺失值、去除重复、处理异常值、去除空白、大小写转换、类型转换、删除行列、重命名列、条件筛选等",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "auto_clean", "fill_missing", "fill_forward", "fill_backward", "fill_value",
                            "drop_duplicates", "deduplicate_subset", "remove_outliers",
                            "trim_whitespace", "standardize_case", "convert_dtype",
                            "rename_columns", "drop_columns", "drop_rows", "truncate_datetime",
                        ],
                        "description": "预处理操作",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "目标列名",
                    },
                    "method": {
                        "type": "string",
                        "description": "具体方法：mean/median/mode/drop（缺失值）, iqr/zscore（异常值）, lower/upper/title（大小写）",
                    },
                    "column": {
                        "type": "string",
                        "description": "单列名（用于类型转换）",
                    },
                    "target_type": {
                        "type": "string",
                        "enum": ["int", "float", "str", "datetime"],
                        "description": "目标类型（用于类型转换）",
                    },
                    "mapping": {
                        "type": "object",
                        "description": "列重命名映射 {原名: 新名}",
                    },
                    "operator": {
                        "type": "string",
                        "description": "条件操作符: ==, !=, >, >=, <, <=, contains, not_contains",
                    },
                    "value": {
                        "type": "string",
                        "description": "条件值或填充值",
                    },
                    "keep": {
                        "type": "string",
                        "enum": ["first", "last"],
                        "description": "去重保留策略",
                    },
                    "fmt": {
                        "type": "string",
                        "description": "日期格式，如 %Y-%m（年月）、%Y-%m-%d（年月日）、%Y（年）",
                    },
                },
                "required": ["operation"],
            },
        },
    },
]

TOOL_RESULT_PROMPT = """以下是工具执行结果，请根据结果用简洁直白的中文为用户总结：
1. 核心发现（2-3个要点）
2. 如有异常，指出异常点
3. 给出简要建议

工具名称: {tool_name}
执行结果: {result}"""
