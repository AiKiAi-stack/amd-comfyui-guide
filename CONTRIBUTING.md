# 贡献实测

新案例请提供显卡/架构、VRAM/RAM、操作系统与驱动、Python/torch/HIP、ComfyUI及插件提交、模型来源/revision/SHA、输入、提示词、API图、真实输出、执行状态与目视结论。

说明 CPU/GPU 编码和 VAE、动态显存、锁页内存、分辨率、seed/steps/CFG/sampler/scheduler。耗时写明是否包含服务启动和模型冷加载；单次实验不能证明一般性能。

失败也欢迎提交：保留最小重现图、错误栈和噪声图。先清理用户名、令牌、Cookie、私密URL、照片与图片元数据，再运行 `python scripts/verify_publication.py`。不要上传模型、环境或整段原始服务日志。

这是教程初稿。全新安装验证、UI工作流版本和跨卡复现实测是优先方向；每项改动应能对应可观察结果。
