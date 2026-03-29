import asyncio
import logging
import time
from typing import Optional, Tuple

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def _find_first_playing_video(page: Page) -> Optional[Tuple[int, int]]:
    frames = page.frames
    for frame_index, frame in enumerate(frames):
        try:
            playing_index = await frame.evaluate(
                """
                () => {
                  const videos = Array.from(document.querySelectorAll("video"));
                  for (let i = 0; i < videos.length; i += 1) {
                    const v = videos[i];
                    const isPlaying = !v.paused && !v.ended && v.currentTime > 0;
                    if (isPlaying) {
                      return i;
                    }
                  }
                  return -1;
                }
                """
            )
            if isinstance(playing_index, int) and playing_index >= 0:
                return frame_index, playing_index
        except Exception:
            continue
    return None


async def _is_video_ended(page: Page, frame_index: int, video_index: int) -> Optional[bool]:
    frames = page.frames
    if frame_index >= len(frames):
        return None

    frame = frames[frame_index]
    try:
        status = await frame.evaluate(
            """
            ({ idx }) => {
              const videos = Array.from(document.querySelectorAll("video"));
              if (idx < 0 || idx >= videos.length) {
                return null;
              }
              const v = videos[idx];
              return {
                ended: Boolean(v.ended),
                paused: Boolean(v.paused),
                currentTime: Number(v.currentTime || 0)
              };
            }
            """,
            {"idx": video_index}
        )
    except Exception:
        return None

    if status is None:
        return None
    return bool(status.get("ended", False))


async def wait_for_video(page: Page, timeout: int = 3600) -> None:
    deadline = time.monotonic() + timeout
    target: Optional[Tuple[int, int]] = None

    # 先定位“正在播放”的视频，再持续轮询该视频的 ended 状态。
    while time.monotonic() < deadline:
        if target is None:
            target = await _find_first_playing_video(page)
            if target:
                logger.info("检测到正在播放的视频，frame=%s, video=%s", target[0], target[1])
            else:
                logger.debug("尚未检测到正在播放的视频，继续轮询")
        else:
            ended = await _is_video_ended(page, target[0], target[1])
            if ended is None:
                logger.warning("目标视频不可访问或页面已更新，重新搜索视频")
                target = None
            elif ended:
                logger.info("检测到视频播放结束")
                return

        await asyncio.sleep(1)

    raise TimeoutError(f"等待视频播放结束超时（>{timeout}秒）")


async def wait_for_video_if_started(
    page: Page,
    start_timeout: int = 8,
    end_timeout: int = 3600,
    poll_interval: float = 1.0
) -> bool:
    deadline = time.monotonic() + max(0, start_timeout)
    while time.monotonic() < deadline:
        target = await _find_first_playing_video(page)
        if target:
            logger.info("检测到点击后视频已开始播放，进入播放完成等待")
            await wait_for_video(page, timeout=end_timeout)
            return True
        await asyncio.sleep(max(0.1, poll_interval))
    return False
