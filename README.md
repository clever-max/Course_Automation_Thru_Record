# Course Automation Through Record v1.1

![版本](https://img.shields.io/badge/版本-v1.1-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![浏览器](https://img.shields.io/badge/浏览器-Chrome/Edge-orange)
![许可证](https://img.shields.io/badge/许可证-MIT-lightgrey)

**Course Automation Through Record** 是一个完整的网课自动化学习解决方案，包含智能录制和自动化回放功能。通过浏览器扩展录制操作，使用桌面应用程序自动执行，帮助用户高效完成网课学习任务。

---
[下载最新版本（当前v1.1）](https://github.com/clever-max/Course_Automation_Thru_Record/releases/)
## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🎯 **智能录制** | 自动捕获点击、输入等用户操作，生成标准JSON脚本 |
| 🔄 **自动化回放** | 精确重现录制操作，支持跨域iframe和动态页面 |
| 🎥 **视频检测** | 自动等待视频播放开始和结束，支持长时间视频 |
| 🛠️ **智能修复** | XPath自动修复系统，解决页面DOM变化问题 |
| 🌐 **跨域支持** | 增强的跨域iframe检测机制，支持复杂网课平台 |
| 🖥️ **图形界面** | 直观易用的GUI控制面板，实时日志监控 |

---

## 🚀 快速开始

### 第一步：安装浏览器扩展

下载extension.zip，并解压到一个你能找到的目录
[Chrome/Edge浏览器离线安装插件全攻略](https://blog.csdn.net/chouchoubuchou/article/details/146294436)

### 第二步：运行桌面应用程序

1. 下载最新版本应用程序：`Course_Automation_Thru_Record_v1.1.exe`
2. 双击运行应用程序
3. 按照界面指引配置和使用

> 💡 **提示**：应用程序已打包为独立exe文件，无需安装Python环境

---

## 📋 使用指南

### 录制网课操作

1. **打开扩展**：点击浏览器工具栏中的网课录制助手图标
2. **开始录制**：点击"开始录制"按钮，状态显示"录制中..."
3. **执行操作**：在网课页面正常操作（点击、输入、导航等）
4. **停止录制**：完成操作后点击"停止录制"，自动下载JSON脚本

### 回放录制脚本

1. **打开应用程序**：运行 `Course_Automation_Thru_Record_v1.1.exe`
2. **选择脚本**：点击"浏览..."选择录制好的JSON文件
3. **配置参数**：
   - **浏览器**：选择Edge或Chromium
   - **错误处理**：出错时停止或跳过
   - **视频超时**：调整视频等待时间（默认：开始8秒，结束2小时）
4. **开始回放**：点击"▶ 开始回放"按钮
5. **登录处理**：如需登录，手动登录后点击"登录完成，开始回放"

---

## 🔧 高级功能

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

---

## 📊 录制文件格式

```json
{
  "action": "click",
  "xpath": "/html/body[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[2]/ul[1]/li[1]/div[1]/div[1]/div[2]/a[1]",
  "value": null,
  "url": "https://mooc2-ans.xuexitong.com/...",
  "iframePath": ["__cross_origin_iframe__"],
  "time": 1268
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `action` | string | 操作类型：`click`、`type` |
| `xpath` | string | 元素定位路径（XPath格式） |
| `value` | string/null | 输入值（仅`type`操作） |
| `url` | string | 操作时的页面URL |
| `iframePath` | array | iframe层级路径，支持跨域标记 |
| `time` | number | 相对于录制开始的时间（毫秒） |

---

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
- 确保XPath智能修复功能已开启（默认开启）
- 增加慢动作延迟时间（配置面板调整）
- 检查录制文件质量

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

---

## 🛠️ 技术架构

### 系统组件
- **浏览器扩展**：基于Chrome Extension API，负责操作录制
- **回放引擎**：基于Playwright，提供浏览器自动化能力
- **GUI界面**：基于PySide6，提供用户友好的控制面板
- **智能修复模块**：XPath修复、跨域iframe检测等核心算法

### 文件结构
```
项目目录/
├── Course_Automation_Thru_Record_v1.1.exe    # 桌面应用程序
├── ActionRecord_for_Chromium.crx             # 浏览器扩展文件
├── project/                                  # 项目源码
│   ├── extension/                            # 扩展源代码
│   ├── playback/                            # 回放引擎源码
│   └── *.json                               # 示例录制文件
└── WEBSITE_DOCUMENTATION.md                 # 本文档
```

### 技术栈
- **前端**：Chrome Extension API、HTML/CSS/JavaScript
- **后端**：Python 3.9+、Playwright、PySide6
- **打包工具**：PyInstaller（生成独立exe文件）

---

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

---

## 🔄 更新日志

### v1.1 (当前版本)
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

---

## 📚 使用案例

### 案例1：网课视频批量学习
1. **录制阶段**：登录平台 → 点击课程 → 播放视频 → 返回列表
2. **回放阶段**：加载脚本 → 自动完成所有操作 → 循环处理多门课程

### 案例2：表单自动填写
1. **录制阶段**：导航到表单 → 填写各字段 → 提交
2. **回放阶段**：批量处理多个表单任务 → 无头模式高效执行

### 案例3：数据采集自动化
1. **录制阶段**：登录系统 → 查询数据 → 导出结果
2. **回放阶段**：定时执行采集任务 → 自动保存结果

---

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

---

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

---

## 🌟 致谢

感谢以下开源项目的支持：
- [Playwright](https://playwright.dev/) - 强大的浏览器自动化库
- [PySide6](https://www.qt.io/qt-for-python) - Python GUI框架
- [Chrome Extension API](https://developer.chrome.com/docs/extensions/) - 浏览器扩展开发

---

**最后更新**：2026年3月29日  
**版本**：Course Automation Through Record v1.1  
**文档状态**：✅ 完整可用

> 💡 **提示**：本工具仅用于合法学习目的，请遵守相关平台的使用条款和服务协议。

[返回顶部](#course-automation-through-record-v11)
