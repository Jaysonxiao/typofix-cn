Typofix CN Windows 7 离线发布说明

目标环境：Windows 7 SP1 64 位。目标电脑不需要安装 Python、Node.js 或任何 Python 依赖，也不需要联网。

使用方式：

1. 将整个 TypofixCN 目录解压到本地磁盘。
2. 双击 TypofixCN.exe。
3. 程序会打开本机浏览器页面，服务只监听 127.0.0.1。
4. 不要单独移动或删除 data/models/macbert4csc-base-chinese/onnx 目录。

模型和运行库均已放在发布目录中。首次启动不会下载任何文件，也不会访问 Hugging Face。

如果程序启动失败，请查看 logs/typofix.log。输入文档、术语库和报告保存在 data 目录中。
