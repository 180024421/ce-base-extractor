# 故障排查

## 附加进程失败 / 无法打开进程

- 以**管理员身份**运行 CE 与本工具（部分模拟器需要）
- 多开时用 `--list-processes` 或 GUI「选进程」确认 PID
- 确认 preset 与模拟器匹配（雷电=ldplayer，MuMu=mumu）

## 模块未找到 (libil2cpp.so)

- 游戏需已启动并加载 so；在 CE 中确认模块列表可见
- 模块名大小写不敏感，支持模糊匹配
- 32/64 位指针宽度：Android 模拟器内游戏 so 通常用 **8**（64 位）

## 指针链断裂

- 游戏更新后偏移失效，需重新 CE 扫描
- 交叉验证 + 重启验证过滤不稳定链
- 检查 `max_depth` / `max_single_offset` 是否过严

## 重启验证数值变化

- 默认以「链可读」为稳定；金币/HP 变化是正常的
- 若需数值不变，CLI 使用 `verify --require-value-match`

## 大 SQLite 很慢

- 使用交叉验证前先缩小 CE 扫描范围
- 降低 CE 指针扫描 max level / max offsets
- GUI 提取时会显示进度条，请耐心等待

## Frida 找不到 Android 模块

- PC 侧 attach `dnplayer.exe` 可能看不到 `libil2cpp.so`
- 使用 `frida-ps` 找到 Android 子进程再 attach
- 或改用导出的 Python 脚本通过 Windows ReadProcessMemory 读取

## 打包 EXE 后配置丢失

- `config.default.json` 已通过 PyInstaller `--add-data` 打入
- 用户配置保存在 `%USERPROFILE%\Documents\ce-exports\user_config.json`
