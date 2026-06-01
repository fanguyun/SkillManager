# Pake - 网页转桌面应用打包工具

## 描述
这是一个使用 Pake 将网页 URL 打包成轻量级桌面应用的 skill。Pake 基于 Rust Tauri 框架，可以将任意网页转换为跨平台桌面应用（Windows/macOS/Linux），体积小巧（通常只有 5M），性能优异。

## 工作流程

当用户调用此 skill 时，你需要：

### 1. 环境检查
首先检查系统环境：
- 检查是否安装了 Rust（版本 >= 1.85）
- 检查是否安装了 Node.js（版本 >= 22）
- 如果未安装，提供安装指南

### 2. 安装 Pake
如果系统中没有 Pake，使用以下命令安装：

```bash
# macOS/Linux
npm install -g pake-cli

# Windows
npm install -g pake-cli
```

或使用 Cargo 安装：
```bash
cargo install pake-cli
```

### 3. 收集打包信息
询问用户以下信息（如果未提供）：
- **URL**: 要打包的网页地址（必填）
- **应用名称**: 桌面应用的名称（可选，默认从 URL 提取）
- **图标**: 应用图标路径或 URL（可选，支持 .icns, .ico, .png）
- **窗口大小**: 默认窗口大小，格式如 "1200,800"（可选）
- **是否全屏**: 是否默认全屏（可选）
- **平台**: 目标平台，如 macos, windows, linux（可选，默认当前平台）

### 4. 执行打包命令
根据收集的信息构建 Pake 命令，例如：

```bash
# 基础命令
pake https://example.com --name "MyApp"

# 完整配置示例
pake https://example.com \
  --name "MyApp" \
  --icon ./icon.png \
  --width 1200 \
  --height 800 \
  --fullscreen false \
  --user-agent "Mozilla/5.0..."
```

### 5. 常用参数说明
- `--name <NAME>`: 应用名称
- `--icon <ICON>`: 图标路径（.icns/.ico/.png）
- `--width <WIDTH>`: 窗口宽度（默认 1200）
- `--height <HEIGHT>`: 窗口高度（默认 780）
- `--fullscreen`: 是否全屏
- `--transparent`: 是否透明窗口
- `--resize`: 是否允许调整窗口大小
- `--multi-arch`: 是否构建多架构版本（Apple Silicon）
- `--targets <TARGETS>`: 指定构建目标，如 "deb,appimage"（Linux）
- `--user-agent <UA>`: 自定义 User Agent
- `--show-menu`: 是否显示菜单栏
- `--system-tray`: 是否启用系统托盘

### 6. 输出说明
- 打包完成后，应用程序会生成在当前目录的 `output` 文件夹中
- macOS: .app 或 .dmg
- Windows: .exe 或 .msi
- Linux: .deb, .appimage 等

### 7. 最佳实践
1. **图标准备**:
   - macOS 推荐使用 .icns 格式（1024x1024）
   - Windows 推荐使用 .ico 格式（256x256）
   - 通用可使用 .png 格式

2. **应用命名**: 使用清晰、简洁的名称，避免特殊字符

3. **窗口尺寸**: 根据目标网页的设计选择合适的默认尺寸

4. **跨平台构建**: 如需在不同平台构建，需要在对应的操作系统上执行

5. **测试**: 打包完成后建议测试应用的功能完整性

### 8. 常见问题处理
- 如果遇到权限问题，可能需要使用 `sudo` 或管理员权限
- 如果构建失败，检查 Rust 和 Node.js 版本是否符合要求
- 如果图标未生效，确保图标文件路径正确且格式支持

## 示例对话流程

**用户**: 帮我把 https://chat.openai.com 打包成桌面应用

**助手**:
1. 检查环境（Rust, Node.js, Pake）
2. 如果 Pake 未安装，执行安装
3. 询问应用名称、图标等配置（或使用默认值）
4. 执行打包命令
5. 提示打包进度和结果
6. 告知输出文件位置

## 参考资源
- Pake GitHub: https://github.com/tw93/Pake
- Pake 文档: https://github.com/tw93/Pake/blob/main/README_CN.md
- PakePlus（扩展版本）: https://github.com/Sjj1024/PakePlus

## 注意事项
- 确保有网络连接以下载依赖
- 首次构建可能需要较长时间下载 Rust 依赖
- 打包的应用大小取决于目标网页的复杂度
- 某些网站可能有反爬虫机制，可能需要自定义 User Agent
