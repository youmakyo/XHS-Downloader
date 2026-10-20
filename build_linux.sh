#!/usr/bin/env bash
#
# 在 Linux 上构建 XHS-Downloader 可执行程序（cx_Freeze 打包）。
#
# 用法：
#   ./build_linux.sh              # 构建到 dist/XHS-Downloader
#   ./build_linux.sh --archive    # 构建并额外生成 tar.gz 压缩包
#
# 产物：
#   dist/XHS-Downloader/XHS-Downloader   可执行程序（GUI / TUI / CLI / API / MCP）
#
# 运行环境要求：
#   - GUI 模式需要 GTK3 + WebKit2GTK 4.1（Debian/Ubuntu: libgtk-3-0 libwebkit2gtk-4.1-0；
#     Arch: gtk3 webkit2gtk-4.1）
#   - TUI / CLI / API / MCP 模式不依赖任何图形库
#
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

PYTHON_VERSION=3.12
OUTPUT_DIR="dist/XHS-Downloader"

echo "==> 准备 Python ${PYTHON_VERSION}"
uv python install "${PYTHON_VERSION}"

echo "==> 安装运行时依赖（排除开发依赖）"
uv sync --frozen --no-dev --no-install-project --python "${PYTHON_VERSION}"

echo "==> 安装构建与 GUI 后端依赖（cx_Freeze、PyGObject）"
# PyGObject 提供 pywebview 的 GTK 后端所需的 gi 模块，仅 Linux 打包需要；
# 不写入 pyproject.toml，避免影响 Windows / macOS 构建。
uv pip install cx_Freeze pygobject

echo "==> 打包可执行程序"
# --no-sync 避免 uv run 依据 lockfile 反向同步、移除上一步临时安装的依赖
uv run --no-sync python setup.py build_exe --build-exe "${OUTPUT_DIR}"

# 打包过程中可能残留上一次运行的运行时数据
rm -rf "${OUTPUT_DIR}/Volume"

echo "==> 验证可执行文件"
"${OUTPUT_DIR}/XHS-Downloader" --version

if [[ "${1:-}" == "--archive" ]]; then
    VERSION=$(uv run --no-sync python -c "from source.module import __VERSION__; print(__VERSION__.replace('.stable', '').replace('.beta', ''))")
    ARCHIVE="dist/XHS-Downloader_${VERSION}_Linux_$(uname -m).tar.gz"
    echo "==> 生成压缩包 ${ARCHIVE}"
    tar -czf "${ARCHIVE}" -C dist XHS-Downloader
fi

echo "==> 构建完成：${OUTPUT_DIR}"
echo "    GUI 模式：./${OUTPUT_DIR}/XHS-Downloader"
