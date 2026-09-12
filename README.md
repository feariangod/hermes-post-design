<h1 align="center">Poster Design Skill</h1>

<p align="center">从创意构思、字体设计到海报成稿，让 Agent 沿着同一条创作主线工作。</p>

<p align="center">
  <a href="https://github.com/feariangod/hermes-post-design/actions/workflows/ci.yml?query=branch%3Amain"><img src="https://img.shields.io/badge/CI-view_runs-0969da" alt="CI 构建记录"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-1f883d" alt="代码许可证：MIT"></a>
</p>

<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

<p align="center">
  <a href="#案例预览">案例预览</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#创作流程">创作流程</a> ·
  <a href="#多-agent-支持">多 Agent 支持</a> ·
  <a href="docs/guide.md">完整指南</a>
</p>

面向 **Agents、Codex、Claude 和 Hermes** 的海报设计 Skill，将创意、字体与画面设计串成一条工作流，附带本地渲染、检查与交付工具。

## 案例预览

**现场开造 · AI 线下创作赛 · 概念测试稿**

<p align="center">
  <a href="docs/examples/ai-offline-competition.md"><img src="docs/assets/ai-competition-concept.png" alt="现场开造海报概念稿：立体黑色字形、荧光绿光标与橙色连接件，底部标注日期和待确认信息" width="480"></a>
</p>

> **Concept / 待确认**：这是一张实际案例测试稿，不是真实活动公告。年份、时间和赛制为测试设定，场地与报名待确认。标题是图像字形，不是可编辑字体；其余 12 条文案为可编辑 HTML 文本。

从“9 月 28 日的 AI 线下比赛”出发，把标题做成正在被共同搭建的物件，让字形、光标和构件共同表达“动手创作”。

[查看两轮对比、创作取舍与验证范围](docs/examples/ai-offline-competition.md)

## 快速开始

需要 **Python 3.11–3.13、Node.js 22、Git**，以及能访问本仓库的 GitHub 账号。下面以 macOS / Linux 上的 Codex 为例；[完整指南](docs/guide.md#prepare-the-checkout)包含 Windows、其他宿主、备份与回滚。

**1. 获取源码并准备安装器**

```bash
git clone https://github.com/feariangod/hermes-post-design.git
cd hermes-post-design
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
```

**2. 预览安装路径**

```bash
./.venv/bin/hermes-post-design install-skill --target codex
```

默认是 dry run，不写入文件。确认输出的目标路径后，再执行：

```bash
./.venv/bin/hermes-post-design install-skill --target codex --apply
```

使用其他宿主时，把两条命令里的 `codex` 都替换为 `agents`、`claude` 或 `hermes`，只安装你选择的目标。安装器管理 Skill 文件并备份已有版本，不设置凭据、不修改无关配置，也不发起生图请求。

**3. 开始第一张海报**

让宿主重新加载 Skill 或开启新会话，确认它能发现 `poster-design`，然后告诉它：

> 请使用 poster-design，为 9 月 28 日的 AI 线下比赛设计一张手机传播海报。先明确创意主线，让文案、字体和画面共同表达“动手创作”。时间、场地、报名信息未确认，先做标注清楚的概念稿。需要外部或计费生图时，先说明调用范围和预算。

首次创建海报项目还需要在该项目内安装 Node 依赖、准备字体，并使用可用的 Chrome、Edge 或 Playwright Chromium。Agent 应按[本地运行步骤](docs/guide.md#create-a-poster-project)完成这些准备；安装 Skill 本身不等于项目已可渲染。

## 创作流程

**明确传播任务 → 建立创意主线 → 选择制作方式 → 形成概念稿 → 确认与精修 → 检查交付**

| 环节 | 设计重点 |
| --- | --- |
| 传播任务 | 谁会看到、第一眼看到什么、看完要做什么；已确认事实和待确认信息分开记录。 |
| 创意主线 | 一个与这份 brief 有关的想法，贯穿文案、字体、画面、构图、色彩和材质；克制也可以是设计选择。 |
| 字体表达 | 分别决定标题、正文、数字的角色。标题可以成为主视觉，关键信息保留精确性和可读性。 |
| 概念与精修 | 方向明确时直接做概念稿；构图不确定时再做低成本比较。确认后记录锁定原则与可调整细节。 |
| 实际验收 | 看真实输出和手机预览，分别检查创意是否成立、信息是否正确、技术交付是否达标。 |

### 三种制作方式

| 方式 | 适合的任务 | 处理方法 |
| --- | --- | --- |
| **图像主导** `image-led` | 主视觉驱动、文案较少的活动或情绪表达 | 生成有价值的视觉层，按任务要求校核与排版。 |
| **分层合成** `layered` | 有真实产品、人物、Logo 或频繁修改的信息 | 保留需要忠实还原的原始素材，将背景、图像和可编辑信息分开处理。 |
| **本地排版** `deterministic` | 信息密集、强调修改与稳定渲染的海报 | 使用 HTML/CSS、本地字体与已授权素材，不依赖外部生图服务。 |

有生图工具不代表每张海报都要生图。制作方式由设计需求决定，字体许可、素材来源和事实核对不会因换工具而省略。

## 多 Agent 支持

同一份 [SKILL.md](src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md)承载通用流程，宿主差异集中在[适配说明](src/hermes_post_design/resources/skills/creative/poster-design/references/host-adapters.md)。仓库名保留 `hermes-post-design`，核心 Skill 已不局限于 Hermes。

| 安装目标 | 参数 | 安装内容 |
| --- | --- | --- |
| 通用 Agents 目录 | `--target agents` | 通用 Skill 与本地运行工具 |
| Codex | `--target codex` | 通用 Skill 与本地运行工具 |
| Claude | `--target claude` | 通用 Skill 与本地运行工具 |
| Hermes | `--target hermes` | 通用 Skill、本地运行工具，以及可选启用的 Chiyi Skill / 插件文件 |

**验证边界**：CI 覆盖四种目标的隔离安装与恢复，不代表在四个真实 Agent 中都完成了端到端创作测试。实际生图能力、图像查看能力和外部调用权限，仍需由当前宿主确认。没有生图能力时，可选择本地排版路线；视觉验收能力不足时须报告未验证项。

## 交付与边界

| 阶段 | 意味着什么 |
| --- | --- |
| **Concept** | 供确认的视觉方向，必须保留待确认标识，不能当作已批准的发布稿。 |
| **Publish** | 用户确认后，在批准范围内完成精修，并满足适用的发布检查。 |
| **Release** | 针对印刷、完整源文件等更严格交付，检查最终状态、素材、字体许可和视觉证据。 |

生成 PNG 不等于完成验收，技术检查通过也不等于设计有表现力。生成式标题不自动具备字体级可编辑性，印刷交付也不能只靠手机预览验收。

当前严格 Release 要求全部批准文案使用可见的 DOM / SVG 文本；图像字、路径字及隐藏替代字不能代替这一校验。经核对的图像字仍可按阶段规则用于 Concept 或无需完整可编辑性的 Publish。

外部或计费生图须有明确授权和有界调用预算；视觉确认不等于调用授权。凭据必须留在仓库外，不进入文案、项目配置、命令参数或日志。安装和自动化测试不调用生图服务，但初次安装依赖可能联网。

## 文档与开发

| 入口 | 内容 |
| --- | --- |
| [完整操作指南](docs/guide.md) | 环境准备、四种宿主安装、回滚、本地项目与可选 Chiyi 适配器 |
| [案例记录](docs/examples/ai-offline-competition.md) | 同一主题的两轮对比、字体取舍与实际验证范围 |
| [Skill 入口](src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md) | Agent 读取的创作流程、阶段与门槛 |
| [开发与验证](docs/guide.md#development-and-verification) | Python、Node、打包一致性与安装恢复检查 |

开发时在源码 checkout 内安装测试依赖；每张海报的运行依赖只安装到对应项目。案例展示图位于 `docs/assets/`，不进入安装的 Skill 或 Python wheel。

## 许可证

仓库代码与模板采用 [MIT License](LICENSE)。字体、外部素材与模型输出保留各自适用条款；展示案例不是对第三方权利或商用适用性的保证。
