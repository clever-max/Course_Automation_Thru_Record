"""
Course Automation Playback Engine v2.0
支持混合策略定位系统（ID、文本、CSS、XPath）
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from playwright.async_api import Locator, Page, Playwright, TimeoutError as PlaywrightTimeoutError, async_playwright

from video_detector import wait_for_video, wait_for_video_if_started

logger = logging.getLogger(__name__)


class PlaybackEngine:
    """
    网课自动化回放引擎 v2.0
    支持智能混合定位策略，优先使用最稳定的 selector
    """

    def __init__(
        self,
        script_path: str,
        headless: bool = False,
        slow_mo: int = 0,
        on_error: str = "stop",
        browser: str = "edge",
        wait_for_enter: bool = True,
        use_step_url: bool = False,
        auto_wait_video_after_click: bool = True,
        video_start_timeout: int = 8,
        video_end_timeout: int = 7200,
        wait_for_start_signal: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        self.script_path = Path(script_path)
        self.headless = headless
        self.slow_mo = slow_mo
        self.on_error = on_error
        self.browser = browser
        self.wait_for_enter = wait_for_enter and not headless
        self.use_step_url = use_step_url
        self.auto_wait_video_after_click = auto_wait_video_after_click
        self.video_start_timeout = max(1, video_start_timeout)
        self.video_end_timeout = max(1, video_end_timeout)
        self.wait_for_start_signal = wait_for_start_signal

        # 超时配置
        self.default_timeout_ms = 10_000
        self.retry_timeout_ms = 30_000
        self.iframe_wait_ms = 5_000

    def load_script(self) -> List[Dict[str, Any]]:
        """加载录制脚本"""
        if not self.script_path.exists():
            raise FileNotFoundError(f"脚本文件不存在: {self.script_path}")

        with self.script_path.open("r", encoding="utf-8") as file:
            steps = json.load(file)

        if not isinstance(steps, list):
            raise ValueError("脚本格式错误：根节点应为数组")

        steps.sort(key=lambda item: int(item.get("time", 0)))
        return [self._sanitize_step(step) for step in steps]

    async def run(self) -> None:
        """运行回放"""
        steps = self.load_script()
        logger.info("加载脚本成功，共 %s 条动作", len(steps))

        async with async_playwright() as playwright:
            browser = await self._launch_browser(playwright)
            context = None
            try:
                context = await browser.new_context()
                page = await context.new_page()

                if self.wait_for_enter:
                    await self._wait_for_manual_login(page, steps)

                start = time.monotonic()

                for index, step in enumerate(steps, start=1):
                    try:
                        await self._wait_until_step_time(step, start)
                        await self._execute_step(page, step, index, len(steps))
                    except Exception as error:
                        logger.exception("第 %s 步执行失败: %s", index, error)
                        if self.on_error == "skip":
                            logger.warning("按配置跳过失败步骤，继续执行后续步骤")
                            continue
                        raise
            finally:
                if context is not None:
                    await context.close()
                await browser.close()
        logger.info("回放完成")

    async def _launch_browser(self, playwright: Playwright):
        """启动浏览器"""
        if self.browser == "edge":
            return await playwright.chromium.launch(
                channel="msedge",
                headless=self.headless,
                slow_mo=self.slow_mo
            )
        return await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )

    async def _wait_for_manual_login(self, page: Page, steps: List[Dict[str, Any]]) -> None:
        """等待手动登录"""
        first_url = self._get_first_url(steps)
        if first_url:
            logger.info("登录准备：先打开首个页面 %s", first_url)
            await page.goto(first_url, wait_until="domcontentloaded")
        logger.info("请在已打开的浏览器窗口中完成登录")
        if self.wait_for_start_signal:
            await self.wait_for_start_signal()
        else:
            await asyncio.to_thread(input, "登录完成后按回车开始回放...")

    def _get_first_url(self, steps: List[Dict[str, Any]]) -> Optional[str]:
        """获取第一个URL"""
        for step in steps:
            url = self._normalize_url(step.get("url"))
            if url:
                return url
        return None

    def _normalize_url(self, raw_url: Any) -> Optional[str]:
        """标准化URL"""
        if not isinstance(raw_url, str):
            return None
        return raw_url.strip().strip("`").strip() or None

    def _is_video_url(self, url: str) -> bool:
        """检查是否为视频URL"""
        return "ananas/modules/video/index.html" in url.lower()

    def _sanitize_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """清理和标准化步骤数据"""
        sanitized = dict(step)
        url = self._normalize_url(sanitized.get("url")) or ""
        if url:
            sanitized["url"] = url

        # 处理 iframePath
        iframe_path = sanitized.get("iframePath", [])
        if isinstance(iframe_path, list):
            cleaned_path = [item for item in iframe_path if isinstance(item, str)]
            sanitized["iframePath"] = cleaned_path

        # 视频播放按钮特殊处理
        if sanitized.get("action") == "click" and self._is_video_url(url):
            sanitized["xpath"] = "//button[contains(@class, 'vjs-big-play-button')]"
            sanitized["cssSelector"] = ".vjs-big-play-button"
            sanitized["selectorType"] = "video-button"

        # 兼容旧格式：selector -> xpath
        if "selector" in sanitized and "xpath" not in sanitized:
            sanitized["xpath"] = sanitized.pop("selector")

        return sanitized

    async def _wait_until_step_time(self, step: Dict[str, Any], start_time: float) -> None:
        """等待到步骤执行时间"""
        target_seconds = max(0, int(step.get("time", 0))) / 1000
        elapsed = time.monotonic() - start_time
        wait_seconds = target_seconds - elapsed
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    async def _wait_for_ready_selector(self, page: Page, step: Dict[str, Any], index: int, total: int) -> None:
        """等待就绪标志"""
        ready_selector = step.get("readySelector")
        if ready_selector:
            logger.info("步骤 %s/%s: 等待就绪标志: %s", index, total, ready_selector)
            try:
                iframe_path = step.get("iframePath", [])
                frame_locator = await self._resolve_iframe_path(page, iframe_path)
                
                if frame_locator:
                    locator = frame_locator.locator(f"xpath={ready_selector}")
                else:
                    locator = page.locator(f"xpath={ready_selector}")
                    
                await locator.first.wait_for(
                    state="visible", timeout=10000
                )
                logger.info("步骤 %s/%s: 就绪标志已出现", index, total)
            except PlaywrightTimeoutError:
                logger.warning("步骤 %s/%s: 就绪标志等待超时，继续执行", index, total)

    async def _execute_step(self, page: Page, step: Dict[str, Any], index: int, total: int) -> None:
        """执行单个步骤"""
        action = step.get("action")
        url = self._normalize_url(step.get("url"))

        # URL 处理
        if url and page.url != url:
            if self.use_step_url:
                logger.info("步骤 %s/%s: 导航到 %s", index, total, url)
                await page.goto(url, wait_until="domcontentloaded")
            else:
                logger.info("步骤 %s/%s: 检测到URL变化，等待页面加载: %s", index, total, url)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

        await self._wait_for_ready_selector(page, step, index, total)

        logger.info(
            "步骤 %s/%s: 执行动作 %s, selector=%s, type=%s",
            index, total, action,
            step.get("xpath", "N/A"),
            step.get("selectorType", "unknown")
        )

        if action == "click":
            locators = await self._build_candidate_locators(page, step)
            logger.info("步骤 %s/%s: 构建了 %s 个定位器", index, total, len(locators))
            await self._safe_wait_then_click(locators)
            await self._wait_video_after_click_if_needed(page, step, index, total)
            return

        if action == "type":
            locators = await self._build_candidate_locators(page, step)
            value = step.get("value", "")
            await self._safe_wait_then_fill(locators, str(value))
            return

        if action == "scroll":
            delta_x = int(step.get("delta_x", 0))
            delta_y = int(step.get("delta_y", 600))
            await page.mouse.wheel(delta_x, delta_y)
            return

        if action == "wait":
            duration_ms = int(step.get("duration", step.get("ms", 1000)))
            await asyncio.sleep(max(0, duration_ms) / 1000)
            return

        if action == "wait_for_video":
            timeout = int(step.get("timeout", 3600))
            await wait_for_video(page, timeout=timeout)
            return

        raise ValueError(f"不支持的动作类型: {action}")

    async def _wait_video_after_click_if_needed(
        self, page: Page, step: Dict[str, Any], index: int, total: int
    ) -> None:
        """点击后等待视频"""
        if not self.auto_wait_video_after_click:
            return
        if not self._is_video_related_click(step, page.url):
            return

        logger.info("步骤 %s/%s: 检测到可能的视频播放点击，开始等待视频", index, total)
        started = await wait_for_video_if_started(
            page,
            start_timeout=self.video_start_timeout,
            end_timeout=self.video_end_timeout
        )
        if started:
            logger.info("步骤 %s/%s: 视频播放结束，继续执行后续步骤", index, total)
        else:
            logger.info("步骤 %s/%s: 未检测到视频开始播放，继续执行后续步骤", index, total)

    def _is_video_related_click(self, step: Dict[str, Any], current_url: str) -> bool:
        """检查是否为视频相关点击"""
        selector_type = step.get("selectorType", "").lower()
        xpath = step.get("xpath", "").lower() if isinstance(step.get("xpath"), str) else ""
        step_url = self._normalize_url(step.get("url")) or ""
        url_text = f"{current_url} {step_url}".lower()

        keywords = ("video", "play", "vjs", "ananas", "播放器", "播放")
        return (
            selector_type in ("video-button", "chapter") or
            any(keyword in xpath for keyword in keywords) or
            any(keyword in url_text for keyword in keywords)
        )

    async def _build_candidate_locators(self, page: Page, step: Dict[str, Any]) -> List[Locator]:
        """
        构建候选定位器列表
        优先使用新的 smartSelectors 格式，兼容旧格式
        """
        candidates: List[Locator] = []
        iframe_path = step.get("iframePath", [])

        # 获取所有 selector（按优先级排序）
        selectors = self._extract_selectors(step)

        logger.info(
            "构建定位器: 主selector=%s, 备用selectors=%s, iframePath=%s",
            selectors[0] if selectors else "N/A",
            selectors[1:] if len(selectors) > 1 else [],
            iframe_path
        )

        # 处理 iframe
        frame_locator = await self._resolve_iframe_path(page, iframe_path)

        # 构建定位器
        for selector_info in selectors:
            locator = self._create_locator(
                page, frame_locator, selector_info
            )
            if locator:
                candidates.append(locator)

        # 视频播放按钮兜底
        step_url = self._normalize_url(step.get("url")) or ""
        if self._is_video_url(step_url):
            video_xpath = "//button[contains(@class, 'vjs-big-play-button')]"
            if frame_locator:
                candidates.append(frame_locator.locator(f"xpath={video_xpath}"))
            else:
                candidates.append(page.locator(f"xpath={video_xpath}"))
            logger.info("添加视频播放按钮定位器")

        return candidates

    def _extract_selectors(self, step: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从步骤中提取所有 selector
        返回按优先级排序的 selector 列表
        """
        selectors = []

        # 1. 新的 smartSelectors 格式（v2.0）
        smart_selectors = step.get("selectors", [])
        if isinstance(smart_selectors, list) and smart_selectors:
            for sel in smart_selectors:
                if isinstance(sel, dict):
                    selectors.append({
                        "type": sel.get("type", "unknown"),
                        "priority": sel.get("priority", 99),
                        "xpath": sel.get("xpath"),
                        "css": sel.get("css")
                    })

        # 2. 如果没有 smartSelectors，使用旧格式
        if not selectors:
            # 优先使用 cssSelector
            css_selector = step.get("cssSelector")
            if css_selector:
                selectors.append({
                    "type": step.get("selectorType", "css"),
                    "priority": step.get("selectorPriority", 5),
                    "xpath": None,
                    "css": css_selector
                })

            # 然后使用 xpath
            xpath = step.get("xpath")
            if xpath:
                selectors.append({
                    "type": step.get("selectorType", "xpath"),
                    "priority": step.get("selectorPriority", 7),
                    "xpath": xpath,
                    "css": None
                })

        # 3. 智能修复 XPath
        # BUG修复：使用副本遍历，避免在遍历时修改列表导致无限循环
        original_selectors = selectors.copy()
        for sel in original_selectors:
            if sel.get("xpath"):
                fixed_xpaths = self._fix_xpath_if_needed(sel["xpath"])
                for fixed in fixed_xpaths[1:]:  # 跳过第一个（原始值）
                    selectors.append({
                        "type": f"{sel['type']}-fixed",
                        "priority": sel["priority"] + 0.5,
                        "xpath": fixed,
                        "css": None
                    })
        # 按优先级排序
        selectors.sort(key=lambda x: x.get("priority", 99))

        return selectors

    def _create_locator(
        self,
        page: Page,
        frame_locator: Optional[Any],
        selector_info: Dict[str, Any]
    ) -> Optional[Locator]:
        """创建单个定位器"""
        css = selector_info.get("css")
        xpath = selector_info.get("xpath")

        # 优先使用 CSS Selector（性能更好）
        if css:
            try:
                if frame_locator:
                    return frame_locator.locator(f"css={css}")
                else:
                    return page.locator(f"css={css}")
            except Exception as e:
                logger.debug("CSS selector 创建失败: %s", e)

        # 使用 XPath
        if xpath:
            try:
                if frame_locator:
                    return frame_locator.locator(f"xpath={xpath}")
                else:
                    return page.locator(f"xpath={xpath}")
            except Exception as e:
                logger.debug("XPath 创建失败: %s", e)

        return None

    async def _resolve_iframe_path(
        self, page: Page, iframe_path: List[str]
    ) -> Optional[Any]:
        """解析 iframe 路径"""
        if not isinstance(iframe_path, list) or not iframe_path:
            return None

        frame_locator = None
        frame_path_valid = True

        for i, frame_xpath in enumerate(iframe_path):
            if not isinstance(frame_xpath, str) or not frame_xpath.strip():
                frame_path_valid = False
                logger.warning("iframe路径第 %s 项无效: %s", i, frame_xpath)
                break

            # 处理特殊标记
            if frame_xpath.startswith("__"):
                if frame_xpath == "__cross_origin_iframe__":
                    frame_locator = await self._handle_cross_origin_iframe(page)
                    if frame_locator is None:
                        frame_path_valid = False
                        break
                    continue
                else:
                    logger.warning("未知的特殊iframe标记: %s", frame_xpath)
                    frame_path_valid = False
                    break

            # 正常 iframe 定位
            try:
                if frame_locator is None:
                    await page.locator(f"xpath={frame_xpath}").first.wait_for(
                        state="attached", timeout=self.iframe_wait_ms
                    )
                else:
                    await frame_locator.locator(f"xpath={frame_xpath}").first.wait_for(
                        state="attached", timeout=self.iframe_wait_ms
                    )
            except PlaywrightTimeoutError as e:
                frame_path_valid = False
                logger.warning("第 %s 层iframe元素等待超时: %s", i + 1, str(e)[:200])
                break

            # 进入下一层
            if frame_locator is None:
                frame_locator = page.frame_locator(f"xpath={frame_xpath}")
            else:
                frame_locator = frame_locator.frame_locator(f"xpath={frame_xpath}")

        return frame_locator if frame_path_valid else None

    async def _handle_cross_origin_iframe(self, page: Page) -> Optional[Any]:
        """处理跨域 iframe"""
        logger.info("检测到跨域iframe标记，尝试定位跨域iframe")

        max_wait_attempts = 5
        for attempt in range(max_wait_attempts):
            logger.info("等待iframe加载 (尝试 %s/%s)...", attempt + 1, max_wait_attempts)

            frames = page.frames
            logger.info("当前检测到 %s 个frames", len(frames))

            if len(frames) > 1:
                for frame_idx, frame in enumerate(frames[1:], start=1):
                    try:
                        frame_url = frame.url
                        logger.info("检查frame[%s]: URL=%s", frame_idx, frame_url[:100] if frame_url else "None")

                        if frame_url and page.url:
                            current_domain = self._extract_domain(page.url)
                            frame_domain = self._extract_domain(frame_url)

                            if current_domain != frame_domain:
                                logger.info("找到跨域iframe: 索引=%s", frame_idx)
                                return page.frame_locator("iframe").nth(frame_idx - 1)
                    except Exception as e:
                        logger.debug("检查frame异常: %s", str(e)[:100])

            # 等待重试
            if attempt < max_wait_attempts - 1:
                await asyncio.sleep(2)

        # 最后尝试：直接查找 iframe 元素
        iframe_count = await page.locator("iframe").count()
        logger.info("直接查找找到 %s 个iframe元素", iframe_count)
        if iframe_count > 0:
            return page.frame_locator("iframe").first

        logger.warning("定位跨域iframe失败")
        return None

    async def _safe_wait_then_click(self, locators: List[Locator]) -> None:
        """安全等待并点击（快速轮询策略）"""
        last_error: Optional[Exception] = None
        
        # 阶段 1: 快速轮询所有定位器
        start_time = time.monotonic()
        timeout_seconds = self.default_timeout_ms / 1000.0
        
        while time.monotonic() - start_time < timeout_seconds:
            for i, locator in enumerate(locators):
                try:
                    # 使用极短超时检查是否可用，只要找到了就点击
                    if await locator.first.is_visible():
                        await locator.first.click(timeout=3000)
                        logger.info("第 %s 个定位器点击成功", i + 1)
                        return
                except Exception as e:
                    last_error = e
            # 没找到，短暂等待后继续轮询
            await asyncio.sleep(0.5)

        # 阶段 2: 如果轮询超时，尝试使用首选定位器进行强力等待（备选容错）
        logger.warning("所有定位器快速轮询超时，尝试使用首个定位器强制等待...")
        if locators:
            try:
                await locators[0].first.wait_for(state="attached", timeout=self.iframe_wait_ms)
                await asyncio.sleep(0.25)
                await locators[0].first.wait_for(state="visible", timeout=self.retry_timeout_ms)
                await locators[0].first.click(timeout=self.retry_timeout_ms)
                logger.info("首个定位器强制等待后点击成功")
                return
            except Exception as e:
                last_error = e
                logger.warning("首个定位器强制等待失败: %s", str(e)[:200])

        raise TimeoutError("元素点击失败：已尝试所有定位策略均超时") from last_error

    async def _safe_wait_then_fill(self, locators: List[Locator], value: str) -> None:
        """安全等待并输入（快速轮询策略）"""
        last_error: Optional[Exception] = None

        start_time = time.monotonic()
        timeout_seconds = self.default_timeout_ms / 1000.0
        
        while time.monotonic() - start_time < timeout_seconds:
            for i, locator in enumerate(locators):
                try:
                    if await locator.first.is_visible():
                        await locator.first.fill(value, timeout=3000)
                        logger.info("第 %s 个定位器输入成功", i + 1)
                        return
                except Exception as e:
                    last_error = e
            await asyncio.sleep(0.5)

        logger.warning("所有定位器快速轮询超时，尝试使用首个定位器强制等待...")
        if locators:
            try:
                await locators[0].first.wait_for(state="attached", timeout=self.iframe_wait_ms)
                await asyncio.sleep(0.25)
                await locators[0].first.wait_for(state="visible", timeout=self.retry_timeout_ms)
                await locators[0].first.fill(value, timeout=self.retry_timeout_ms)
                logger.info("首个定位器强制等待后输入成功")
                return
            except Exception as e:
                last_error = e
                logger.warning("首个定位器强制等待失败: %s", str(e)[:200])

        raise TimeoutError("输入失败：已尝试所有定位策略均超时") from last_error

    def _extract_domain(self, url: str) -> str:
        """从URL中提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _fix_xpath_if_needed(self, xpath: str) -> List[str]:
        """智能修复 XPath"""
        if not isinstance(xpath, str):
            return []

        fixed_paths = [xpath]

        # 修复1: div[2] -> div[2]/a[1]
        if xpath.endswith("/div[2]"):
            fixed = xpath + "/a[1]"
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)

        # 修复2: div[2]/a -> div[2]/a[1]
        elif xpath.endswith("/div[2]/a"):
            fixed = xpath + "[1]"
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)

        # 修复3: div[2]/a[1] -> div[2]/a
        elif xpath.endswith("/div[2]/a[1]"):
            fixed = xpath[:-3]
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)

        # 修复4: 绝对路径简化 - 简化为相对路径，但保持有效语法
        if xpath.startswith("/html/"):
            import re
            # 将 /html/body[1]/ 替换为 //body/
            simplified = re.sub(r'^/html/body\[1\]/', '//body/', xpath)
            # 将 /div[n]/ 替换为 //div[n]/ 保持索引有效
            simplified = re.sub(r'/div\[(\d+)\]/', r'//div[\1]/', simplified)
            if simplified != xpath:
                fixed_paths.append(simplified)
                logger.debug("XPath简化: %s -> %s", xpath, simplified)

        return fixed_paths
