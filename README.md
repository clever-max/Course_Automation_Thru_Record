# Course Automation Through Record v2.1

!\[版本]\(https\://img.shields.io/badge/版本-v2.0-blue null)
!\[Python]\(https\://img.shields.io/badge/Python-3.9%2B-green null)
!\[浏览器]\(https\://img.shields.io/badge/浏览器-Chrome/Edge-orange null)
!\[许可证]\(https\://img.shields.io/badge/许可证-MIT-lightgrey null)

**Course Automation Through Record** 是一个完整的网课自动化学习解决方案，包含智能录制和自动化回放功能。通过浏览器扩展录制操作，使用桌面应用程序自动执行，帮助用户高效完成网课学习任务。

> 🎉 **v2.0 重大更新**：引入智能混合定位策略，大幅提升录制稳定性和回放成功率！

***

**点击下方链接下载必要文件**
**[下载最新版本（当前v2.1）](https://github.com/clever-max/Course_Automation_Thru_Record/releases/)**

## ✨ 核心特性

| 特性                  | 描述                        | v2.0 改进           |
| ------------------- | ------------------------- | ----------------- |
| 🎯 **智能录制**         | 自动捕获点击、输入等用户操作，生成标准JSON脚本 | ✅ 混合策略定位系统        |
| 🔄 **自动化回放**        | 精确重现录制操作，支持跨域iframe和动态页面  | ✅ 智能 selector 优先级 |
| 🎥 **视频检测**         | 自动等待视频播放开始和结束，支持长时间视频     | ✅ 更准确的视频识别        |
| 🛠️ **智能修复**        | XPath自动修复系统，解决页面DOM变化问题   | ✅ 多层级修复策略         |
| 🌐 **跨域支持**         | 增强的跨域iframe检测机制，支持复杂网课平台  | ✅ 自动域名识别          |
| 🖥️ **图形界面**        | 直观易用的GUI控制面板，实时日志监控       | ✅ 更详细的日志输出        |
| 📝 **语义定位**         | 基于文本内容的智能定位               | 🆕 **v2.0 新增**    |
| 🎨 **CSS Selector** | 支持CSS选择器定位                | 🆕 **v2.0 新增**    |

***

## 🚀 快速开始

### 环境要求

- **操作系统**: Windows 10/11
- **Python**: 3.9 或更高版本
- **浏览器**: Chrome 或 Edge (最新版本)

### 安装步骤

#### 第一步：安装浏览器扩展

**在顶部Releases下载extension.zip**，并解压到一个你能找到的目录
[Chrome/Edge浏览器离线安装插件全攻略](https://blog.csdn.net/chouchoubuchou/article/details/146294436)

#### 第二步：运行桌面应用程序

1. 下载最新版本应用程序：`Course_Automation_Thru_Record_v2.0.exe`
2. 双击运行应用程序
3. 按照界面指引配置和使用

> 💡 **提示**：应用程序已打包为独立exe文件，无需安装Python环境

#### 第三步：从源码运行（开发者）

```bash
# 克隆项目
cd playback

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
python -m playwright install chromium

# 运行回放引擎
python main.py --script path/to/recording.json --browser edge
```

***

## 📋 使用指南

### 录制网课操作

1. **打开扩展**：点击浏览器工具栏中的网课录制助手图标
2. **开始录制**：点击"开始录制"按钮，状态显示"录制中..."
3. **执行操作**：在网课页面正常操作（点击、输入、导航等）
4. **停止录制**：完成操作后点击"停止录制"，自动下载JSON脚本

### 回放录制脚本

1. **打开应用程序**：运行 `Course_Automation_Thru_Record_v2.0.exe`
2. **选择脚本**：点击"浏览..."选择录制好的JSON文件
3. **配置参数**：
   - **浏览器**：选择Edge或Chromium
   - **错误处理**：出错时停止或跳过
   - **视频超时**：调整视频等待时间（默认：开始8秒，结束2小时）
4. **开始回放**：点击"▶ 开始回放"按钮
5. **登录处理**：如需登录，手动登录后点击"登录完成，开始回放"

### 命令行使用

```bash
python main.py \
  --script D:\recordings\course.json \
  --browser edge \
  --on-error skip \
  --auto-wait-video-after-click \
  --video-start-timeout 10 \
  --video-end-timeout 7200
```

***

## 🔧 高级功能

### 混合策略定位系统（v2.0 新特性）

v2.0 引入了智能混合定位策略，按以下优先级尝试定位元素：

| 优先级 | 定位方式             | 示例                                                  |  稳定性  |
| :-: | ---------------- | --------------------------------------------------- | :---: |
|  1  | **ID / data-id** | `//*[@id="contentFocus"]`                           | ⭐⭐⭐⭐⭐ |
|  2  | **文本内容**         | `//span[contains(text(), "1.1")]`                   | ⭐⭐⭐⭐⭐ |
|  3  | **ARIA 属性**      | `//*[@aria-label="播放视频"]`                           |  ⭐⭐⭐⭐ |
|  4  | *data-* 属性\*     | `//*[@data-cid="12345"]`                            |  ⭐⭐⭐⭐ |
|  5  | **CSS 类名**       | `//button[contains(@class, "vjs-big-play-button")]` |  ⭐⭐⭐⭐ |
|  6  | **相对路径**         | `//*[@id="list"]//div[2]//a`                        |  ⭐⭐⭐  |
|  7  | **完整 XPath**     | `/html/body/div[1]/div[2]...`                       |   ⭐⭐  |

### 学习通特殊优化

针对学习通平台，v2.0 做了以下特殊优化：

- **章节号识别**：自动识别 "1.1", "2.3" 等章节编号
- **视频播放按钮**：自动识别 `vjs-big-play-button` 类
- **返回按钮**：自动识别 `icon-BackIcon` 类

### 跨域iframe智能处理

**问题**：网课平台常使用跨域iframe嵌入视频播放器，传统工具无法录制。

**解决方案**：

- 录制时自动检测并标记跨域iframe为 `__cross_origin_iframe__`
- 回放时使用增强算法（最长等待10秒+多重定位策略）
- 智能比较域名差异，支持复杂iframe嵌套

### XPath智能修复系统

**问题**：页面DOM结构变化导致录制时的元素定位失效。

**自动修复规则**：

1. `div[2]` → `div[2]/a[1]` （添加缺失的链接元素）
2. `div[2]/a` → `div[2]/a[1]` （添加缺失的索引）
3. `/html/body[1]/div[1]` → `//body//div[1]` （路径简化）

### 视频播放智能等待

**工作流程**：

```
点击视频播放 → 等待开始（最长8秒） → 监测播放状态 → 等待结束（最长2小时） → 继续后续操作
```

***

## 📊 录制文件格式

### v2.0 新格式（推荐）

```json
{
  "action": "click",
  "xpath": "//span[contains(text(), '1.1')]",
  "cssSelector": null,
  "selectorType": "chapter",
  "selectorPriority": 2,
  "selectors": [
    {
      "type": "chapter",
      "priority": 2,
      "xpath": "//span[contains(text(), '1.1')]",
      "css": null
    },
    {
      "type": "class",
      "priority": 5,
      "xpath": "//span[contains(@class, 'catalog')]",
      "css": "span.catalog"
    },
    {
      "type": "xpath-full",
      "priority": 7,
      "xpath": "/html/body/div[1]/div[1]/div[2]/div[2]/div[2]/div[2]/ul/li[1]/div/div/div[2]/a[1]",
      "css": null
    }
  ],
  "value": null,
  "url": "https://mooc2-ans.xuexitong.com/...",
  "iframePath": ["__cross_origin_iframe__"],
  "readySelector": null,
  "time": 1268
}
```

### 字段说明

| 字段                 | 类型          | 说明                     |
| ------------------ | ----------- | ---------------------- |
| `action`           | string      | 操作类型：`click`、`type`    |
| `xpath`            | string      | 主要元素定位路径（XPath格式）      |
| `cssSelector`      | string      | CSS选择器（如有）             |
| `selectorType`     | string      | 主selector类型            |
| `selectorPriority` | number      | 主selector优先级           |
| `selectors`        | array       | 所有候选selector列表（按优先级排序） |
| `value`            | string/null | 输入值（仅`type`操作）         |
| `url`              | string      | 操作时的页面URL              |
| `iframePath`       | array       | iframe层级路径，支持跨域标记      |
| `readySelector`    | string      | 就绪状态检测selector         |
| `time`             | number      | 相对于录制开始的时间（毫秒）         |

### 兼容旧格式

v2.0 完全兼容 v1.x 的录制文件格式：

```json
{
  "action": "click",
  "xpath": "/html/body/div[1]/div[1]/div[2]/div[2]/div[2]/div[2]/ul[1]/li[1]/div[1]/div[1]/div[2]/a[1]",
  "value": null,
  "url": "https://mooc2-ans.xuexitong.com/...",
  "iframePath": ["__cross_origin_iframe__"],
  "time": 1268
}
```

***

## ⚠️ 常见问题

### Q1：录制时操作未被捕获

**可能原因**：扩展未正确启用或页面使用复杂JavaScript框架
**解决方案**：

- 检查扩展是否已启用（chrome://extensions/）
- 刷新页面后重试
- 确认操作在普通HTML元素上执行

### Q2：回放时元素定位失败

**可能原因**：页面DOM结构变化或iframe加载问题
**解决方案**：

- v2.0 会自动尝试多种定位策略，通常无需干预
- 增加慢动作延迟时间（配置面板调整）
- 检查录制文件质量，优先使用 v2.0 新格式

### Q3：应用程序无法启动

**可能原因**：防病毒软件拦截或运行时依赖缺失
**解决方案**：

- 以管理员身份运行
- 添加到杀毒软件白名单
- 确保系统已安装.NET Framework最新版本

### Q4：跨域iframe操作失败

**可能原因**：iframe加载时间不足或网络问题
**解决方案**：

- 系统已内置10秒等待机制，通常无需调整
- 确保网络连接稳定
- 手动验证iframe在浏览器中可正常访问

***

## 🛠️ 技术架构

### 系统组件

- **浏览器扩展**：基于Chrome Extension API，负责操作录制
- **回放引擎**：基于Playwright，提供浏览器自动化能力
- **GUI界面**：基于PySide6，提供用户友好的控制面板
- **智能修复模块**：XPath修复、跨域iframe检测等核心算法

### 文件结构

```
项目目录/
├── Course_Automation_Thru_Record_v2.0.exe    # 桌面应用程序
├── ActionRecord_for_Chromium.crx             # 浏览器扩展文件
├── project/                                  # 项目源码
│   ├── extension/                            # 扩展源代码
│   │   ├── manifest.json                     # 扩展配置
│   │   ├── content.js                        # 内容脚本（智能定位）
│   │   ├── background.js                     # 后台脚本
│   │   ├── popup.html                        # 弹出界面
│   │   └── popup.js                          # 弹出界面逻辑
│   ├── playback/                            # 回放引擎源码
│   │   ├── main.py                          # 命令行入口
│   │   ├── engine.py                        # 核心引擎（v2.0）
│   │   ├── gui.py                           # GUI界面
│   │   ├── video_detector.py                # 视频检测
│   │   ├── utils.py                         # 工具函数
│   │   └── requirements.txt                 # Python依赖
│   └── *.json                               # 示例录制文件
└── README.md                                # 本文档
```

### 技术栈

- **前端**：Chrome Extension API、HTML/CSS/JavaScript (ES6+)
- **后端**：Python 3.9+、Playwright、PySide6
- **打包工具**：PyInstaller（生成独立exe文件）

***

## 📈 性能优化建议

### 录制优化

1. **操作清晰**：每个操作之间保持明显间隔（0.5-1秒）
2. **避免快速操作**：录制时不要过快点击，给扩展处理时间
3. **验证录制**：停止后检查JSON文件，确认操作完整记录
4. **文件命名**：使用有意义的名称，便于后续管理

### 回放优化

1. **参数调整**：
   - 网络良好：慢动作延迟0-500ms
   - 网络一般：慢动作延迟500-1000ms
   - 页面复杂：增加视频超时时间
2. **批量处理**：
   - 使用无头模式节省系统资源
   - 创建脚本库复用常用操作序列
   - 结合任务计划程序实现定时执行

### 资源管理

- **CPU/内存**：单个实例约占用100-300MB内存
- **网络**：需要稳定网络连接，建议宽带环境
- **存储**：录制文件通常1-10KB，视频检测可能产生临时文件

***

## 🔄 更新日志

### v2.0 (当前版本) - 2026年4月

- ✅ **混合策略定位系统**：ID、文本、CSS、XPath 多层级定位
- ✅ **智能优先级排序**：自动选择最稳定的定位方式
- ✅ **学习通特殊优化**：章节号、播放按钮、返回按钮自动识别
- ✅ **CSS Selector 支持**：性能更好的定位方式
- ✅ **语义化定位**：基于文本内容的智能定位
- ✅ **向后兼容**：完全兼容 v1.x 录制文件
- ✅ **增强日志输出**：更详细的执行过程记录
- ✅ **代码重构**：更清晰、更易维护的架构

### v1.1

- ✅ **跨域iframe增强检测**：增加等待机制和多重定位策略
- ✅ **XPath智能修复系统**：自动修复常见XPath格式问题
- ✅ **视频播放智能等待**：改进视频开始和结束检测
- ✅ **GUI界面优化**：更直观的用户界面和实时日志
- ✅ **错误处理增强**：更完善的异常处理机制
- ✅ **独立可执行文件**：无需Python环境，开箱即用

### v1.0

- 🎯 基础录制和回放功能
- 🎯 基本视频检测支持
- 🎯 图形用户界面框架

***

## 🤝 贡献与支持

### 问题反馈

遇到问题时，请提供以下信息：

1. 操作系统版本（Windows 10/11）
2. 浏览器类型和版本（Chrome/Edge版本）
3. 录制文件片段（JSON内容）
4. 应用程序日志输出
5. 具体操作步骤描述

### 功能建议

如有新功能需求或改进建议，欢迎提出：

- 支持更多浏览器类型
- 增强录制精度
- 优化回放性能
- 添加更多自动化场景

### 技术交流

- **项目类型**：个人开源项目
- **主要技术**：Python、Playwright、Chrome Extension
- **适用场景**：网课学习、自动化测试、数据采集

***

## 📄 许可证

本项目采用 MIT 许可证。

```
MIT License

Copyright (c) 2026 Course Automation Through Record

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

***

## 🌟 致谢

感谢以下开源项目的支持：

- [Playwright](https://playwright.dev/) - 强大的浏览器自动化库
- [PySide6](https://www.qt.io/qt-for-python) - Python GUI框架
- [Chrome Extension API](https://developer.chrome.com/docs/extensions/) - 浏览器扩展开发

***

**最后更新**：2026年4月3日\
**版本**：Course Automation Through Record v2.0\
**文档状态**：✅ 完整可用

> 💡 **提示**：本工具仅用于合法学习目的，请遵守相关平台的使用条款和服务协议。

[返回顶部](#course-automation-through-record-v20)
