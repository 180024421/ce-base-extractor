"""将底层异常转成可行动的用户提示。"""

from __future__ import annotations

from pathlib import Path

_TROUBLE = Path(__file__).resolve().parents[2] / "docs" / "TROUBLESHOOTING.md"


def troubleshooting_hint() -> str:
    return f"详见排障文档:\n{_TROUBLE}"


def format_user_error(title: str, exc: BaseException, *, context: str = "") -> str:
    msg = str(exc).strip() or exc.__class__.__name__
    tips: list[str] = []
    low = msg.lower()

    if "access" in low or "拒绝" in msg or "denied" in low:
        tips.append("请以管理员身份运行本工具与模拟器/CE")
    if "找不到" in msg or "not found" in low or "no such" in low:
        tips.append("确认模拟器已启动，并在「提取」页点「选进程」核对 PID")
    if "module" in low or "libil2cpp" in low:
        tips.append("确认游戏已进入可玩界面；必要时在高级选项检查模块白名单")
    if "ptrid" in low or "no such table" in low:
        tips.append("SQLite 可能不是 CE 指针扫描导出，请重新 File → Export to sqlite")
    if context == "empty_result":
        tips.append("结果为 0 条：可放宽「最大层级 / 最大偏移」，或改用交叉验证多份 Rescan")
    if context == "cross":
        tips.append("交叉至少需要 2 个文件；稳定率过低时可取消「交叉需全命中」")
    if not tips:
        tips.append("若持续失败，请对照 docs/TROUBLESHOOTING.md")

    body = f"{msg}\n\n建议：\n" + "\n".join(f"• {t}" for t in tips)
    body += f"\n\n{troubleshooting_hint()}"
    return f"{title}\n\n{body}" if title else body


def empty_result_tip(*, had_raw: bool = False) -> str:
    if had_raw:
        return (
            "原始指针很多，但过滤后为 0 条。\n\n"
            "可尝试：\n"
            "• 增大「最大偏移」或「最大层级」\n"
            "• 取消高级选项中过严过滤\n"
            "• 用「交叉验证」页添加 2～3 份 Rescan\n\n"
            + troubleshooting_hint()
        )
    return (
        "未解析到任何指针链。\n\n"
        "请确认文件是 CE 指针扫描导出的 SQLite/PTR，且 ptrid 正确。\n\n"
        + troubleshooting_hint()
    )
