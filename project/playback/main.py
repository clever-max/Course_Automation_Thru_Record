import argparse
import asyncio
import logging

from engine import PlaybackEngine
from utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="自动化网课学习助手 - Python 回放引擎")
    parser.add_argument("--script", required=True, help="录制脚本 JSON 文件路径")
    parser.add_argument("--browser", choices=["edge", "chromium"], default="edge", help="浏览器类型，默认 edge")
    parser.add_argument("--headless", action="store_true", help="以无头模式运行浏览器")
    parser.add_argument(
        "--wait-enter",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="启动后等待手动登录，并在终端按回车后开始回放（默认开启）"
    )
    parser.add_argument(
        "--use-step-url",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="是否使用脚本中的 url 字段强制导航（默认关闭，按页面点击自然跳转）"
    )
    parser.add_argument(
        "--auto-wait-video-after-click",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="点击后自动检测并等待视频播放结束（默认开启）"
    )
    parser.add_argument("--video-start-timeout", type=int, default=8, help="点击后等待视频开始播放的超时秒数")
    parser.add_argument("--video-end-timeout", type=int, default=7200, help="检测到播放后等待视频结束的超时秒数")
    parser.add_argument("--slow-mo", type=int, default=0, help="每个动作额外延时（毫秒）")
    parser.add_argument(
        "--on-error",
        choices=["stop", "skip"],
        default="stop",
        help="步骤执行失败时的策略：stop=终止，skip=跳过"
    )
    parser.add_argument("--log-level", default="INFO", help="日志级别，如 DEBUG/INFO/WARNING")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    engine = PlaybackEngine(
        script_path=args.script,
        headless=args.headless,
        slow_mo=args.slow_mo,
        on_error=args.on_error,
        browser=args.browser,
        wait_for_enter=args.wait_enter,
        use_step_url=args.use_step_url,
        auto_wait_video_after_click=args.auto_wait_video_after_click,
        video_start_timeout=args.video_start_timeout,
        video_end_timeout=args.video_end_timeout
    )
    await engine.run()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("用户中断执行")


if __name__ == "__main__":
    main()
