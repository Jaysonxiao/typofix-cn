# Typofix CN Windows 7 离线部署说明

本文用于构建和发布 Windows 7 SP1 x64 离线版本。目标电脑不需要安装 Python、Node.js 或任何 Python 依赖，也不需要联网。

## 1. 构建环境

推荐使用 Windows 7 SP1 x64 虚拟机完成最终构建和验证。构建机可以临时联网，目标运行机不需要联网。

建议配置：

- Windows 7 SP1 64 位
- 至少 4 GB 内存
- 至少 10 GB 可用磁盘
- Python 3.8.10 x64
- PowerShell 5.1
- 可选：Git、7-Zip

本项目的 Win7 构建依赖已经固定在 packaging/win7/requirements.txt，其中使用 FP32 ONNX，不做量化。

## 2. 获取代码

可以直接从远端获取发布分支：

~~~powershell
git clone -b win7-deploy https://github.com/Jaysonxiao/typofix-cn.git C:\work\typofix-cn
cd C:\work\typofix-cn
~~~

如果 Win7 上的 Git 不方便使用，也可以在 Windows 11 下载 win7-deploy 分支 ZIP 后复制到虚拟机。

## 3. 打包前完整目录结构

在执行 build.ps1 之前，项目目录至少应整理成下面的结构：

~~~text
typofix-cn/
├─ backend/
│  └─ src/
│     └─ typofix_cn/
├─ cli/
│  └─ src/
│     └─ typofix_cli/
├─ frontend/
│  └─ dist/
│     ├─ index.html                 必须存在
│     └─ assets/                    前端 JS、CSS 等静态资源
├─ data/
│  ├─ models/
│  │  └─ macbert4csc-base-chinese/
│  │     └─ onnx/
│  │        ├─ model.onnx           必须存在，FP32 模型
│  │        └─ tokenizer.json       必须存在
│  └─ confusions/
│     └─ default.txt               可选，首次启动会自动创建默认文件
├─ packaging/
│  └─ win7/
│     ├─ build.ps1
│     ├─ requirements.txt
│     ├─ typofix_win7.spec
│     ├─ test_profile.py
│     ├─ test_release.ps1
│     └─ .venv-win7/               执行 venv 命令后生成
├─ pyproject.toml
├─ uv.lock
└─ README.md
~~~

其中，backend、cli 和 packaging/win7 来自 win7-deploy 分支；frontend/dist 和 data/models/macbert4csc-base-chinese/onnx 通常需要从 Windows 11 的开发目录复制过来。frontend/dist 下除了 index.html 之外，assets 目录也必须完整复制，否则程序页面会缺少样式或脚本。

## 4. 准备前端文件

构建前必须存在：

~~~text
frontend\dist\index.html
~~~

如果 Windows 11 上已经生成了 frontend\dist，直接把整个目录复制到构建机即可。

如需重新构建前端，在有 Node.js 的构建环境中执行：

~~~powershell
cd frontend
npm install
npm run build
cd ..
~~~

目标 Windows 7 电脑不需要安装 Node.js。

## 5. 准备 ONNX 模型

将 FP32 ONNX 模型放到以下位置：

~~~text
data\models\macbert4csc-base-chinese\onnx\model.onnx
data\models\macbert4csc-base-chinese\onnx\tokenizer.json
~~~

至少必须存在这两个文件。模型目录不要重命名，最终发布包会按这个路径加载模型。

## 6. 创建 Python 3.8 构建环境

在项目根目录执行：

~~~powershell
py -3.8 -m venv packaging\win7\.venv-win7
packaging\win7\.venv-win7\Scripts\python.exe --version
~~~

输出应为 Python 3.8.x。

## 7. 构建 EXE

执行：

~~~powershell
powershell.exe -ExecutionPolicy Bypass -File packaging\win7\build.ps1
~~~

该脚本会安装固定版本依赖并调用 PyInstaller 生成 onedir 包。构建结果位于：

~~~text
dist\TypofixCN
~~~

必须保留整个目录，不能只复制 TypofixCN.exe。目录中包含运行库、前端文件、ONNX 模型和数据目录。

## 8. 发布前验证

在项目根目录执行：

~~~powershell
powershell.exe -ExecutionPolicy Bypass -File packaging\win7\test_release.ps1 -Offline
~~~

验证内容包括：

- EXE 是否正常启动
- 本地健康接口是否正常
- DOCX 是否可以上传
- MacBERT 是否可以完成纠错
- JSON 和 HTML 报告是否生成
- 日志中是否出现模型下载或外部网络访问

看到以下输出才可以进入发布步骤：

~~~text
Release smoke passed: <job-id>
~~~

## 9. 压缩发布包

确认验证通过后执行：

~~~powershell
Compress-Archive -Path .\dist\TypofixCN -DestinationPath .\TypofixCN-win7-x64.zip -Force
~~~

也可以使用 7-Zip 压缩整个 dist\TypofixCN 目录。

当前使用 FP32 模型，发布包预计约 550～600 MiB，模型本身约 452 MiB，这是正常的。包体中不包含 PyTorch、Transformers 或重复的 PyTorch 权重。

## 10. Windows 7 目标机运行

1. 将 TypofixCN-win7-x64.zip 复制到目标电脑。
2. 解压到可写目录，例如 D:\TypofixCN。
3. 不要解压到 C:\Program Files，避免 Windows 7 权限问题。
4. 双击 TypofixCN.exe。
5. 程序会打开浏览器访问：

   ~~~text
   http://127.0.0.1:8000
   ~~~

如果浏览器没有自动打开，可以手动访问该地址。程序只监听本机回环地址，不提供局域网访问。

运行数据和报告保存位置：

~~~text
data\jobs
~~~

日志位置：

~~~text
logs\typofix.log
~~~

## 11. 常见注意事项

- 不能只发送 TypofixCN.exe，必须发送整个 TypofixCN 文件夹。
- 不要删除、移动或重命名 data\models\macbert4csc-base-chinese\onnx。
- 目标机首次运行不会下载模型，也不会访问 Hugging Face。
- 默认端口为 8000。如果该端口被其他程序占用，程序可能无法启动。
- 当前 Windows 11 + Python 3.12 生成的 dist 只能作为开发测试包；Windows 7 正式包应使用本说明中的 Python 3.8 环境重新构建。
