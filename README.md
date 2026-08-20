# Hermes Post Design - Chiyi/Hermes 图像与海报工作流

这是 Chiyi/Hermes 图像与海报工作流项目的实现骨架。

## 当前状态

此项目处于早期开发阶段。目前不能声称完整功能已完成。

## 核心设计

- **Provider**: 固定为 `chiyi`
- **Model**: 固定为 `gpt-image-2`
- **Quality**: 固定为 `high`
- **尺寸接口**: 公共参数 `size="WIDTHxHEIGHT"`（例如 `size="1024x1024"`）

## 平台支持

- **第一阶段验证目标**: Windows
- **设计支持边界**: macOS、Linux
- **第二阶段**: Docker 容器化

## 项目结构

```
src/hermes_post_design/
├── chiyi_core/          # 核心数据模型与类型
│   ├── models.py        # 请求、结果、错误类型定义
│   └── __init__.py
└── __init__.py

tests/
└── core/                # 核心模块测试
    └── test_models.py
```

## 开发

```bash
# 安装依赖
pip install -e .

# 运行测试
pip install -e ".[test]"
pytest
```

## 注意事项

- 本 README 不包含 API Key 或私人路径信息
- 所有敏感配置应通过环境变量或独立配置文件管理