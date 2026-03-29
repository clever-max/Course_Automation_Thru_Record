import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from playwright.async_api import Locator, Page, Playwright, TimeoutError as PlaywrightTimeoutError, async_playwright

from video_detector import wait_for_video, wait_for_video_if_started

logger = logging.getLogger(__name__)


class PlaybackEngine:
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
        self.default_timeout_ms = 10_000
        self.retry_timeout_ms = 30_000
        self.iframe_wait_ms = 5_000

    def load_script(self) -> List[Dict[str, Any]]:
        if not self.script_path.exists():
            raise FileNotFoundError(f"脚本文件不存在: {self.script_path}")

        with self.script_path.open("r", encoding="utf-8") as file:
            steps = json.load(file)

        if not isinstance(steps, list):
            raise ValueError("脚本格式错误：根节点应为数组")

        steps.sort(key=lambda item: int(item.get("time", 0)))
        return [self._sanitize_step(step) for step in steps]

    async def run(self) -> None:
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
        if self.browser == "edge":
            return await playwright.chromium.launch(channel="msedge", headless=self.headless, slow_mo=self.slow_mo)
        return await playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)

    async def _wait_for_manual_login(self, page: Page, steps: List[Dict[str, Any]]) -> None:
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
        for step in steps:
            url = self._normalize_url(step.get("url"))
            if url:
                return url
        return None

    def _normalize_url(self, raw_url: Any) -> Optional[str]:
        if not isinstance(raw_url, str):
            return None
        return raw_url.strip().strip("`").strip() or None

    def _is_video_url(self, url: str) -> bool:
        return "ananas/modules/video/index.html" in url.lower()

    def _sanitize_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = dict(step)
        url = self._normalize_url(sanitized.get("url")) or ""
        if url:
            sanitized["url"] = url

        iframe_path = sanitized.get("iframePath", [])
        if isinstance(iframe_path, list):
            # 保留特殊标记，如 __cross_origin_iframe__
            cleaned_path = [item for item in iframe_path if isinstance(item, str)]
            sanitized["iframePath"] = cleaned_path

        if sanitized.get("action") == "click" and self._is_video_url(url):
            sanitized["xpath"] = "//button[contains(@class, 'vjs-big-play-button')]"

        if "selector" in sanitized and "xpath" not in sanitized:
            sanitized["xpath"] = sanitized.pop("selector")

        return sanitized

    async def _wait_until_step_time(self, step: Dict[str, Any], start_time: float) -> None:
        target_seconds = max(0, int(step.get("time", 0))) / 1000
        elapsed = time.monotonic() - start_time
        wait_seconds = target_seconds - elapsed
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    async def _wait_for_ready_selector(self, page: Page, step: Dict[str, Any], index: int, total: int) -> None:
        ready_selector = step.get("readySelector")
        if ready_selector:
            logger.info("步骤 %s/%s: 等待就绪标志: %s", index, total, ready_selector)
            try:
                await page.locator(ready_selector).wait_for(state="visible", timeout=10000)
                logger.info("步骤 %s/%s: 就绪标志已出现", index, total)
            except PlaywrightTimeoutError:
                logger.warning("步骤 %s/%s: 就绪标志等待超时，继续执行", index, total)

    async def _execute_step(self, page: Page, step: Dict[str, Any], index: int, total: int) -> None:
        action = step.get("action")
        url = self._normalize_url(step.get("url"))
        
        if url and page.url != url:
            if self.use_step_url:
                logger.info("步骤 %s/%s: 导航到 %s", index, total, url)
                await page.goto(url, wait_until="domcontentloaded")
            else:
                logger.info("步骤 %s/%s: 检测到URL变化，等待页面加载: %s", index, total, url)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)

        await self._wait_for_ready_selector(page, step, index, total)
        
        logger.info("步骤 %s/%s: 执行动作 %s, xpath=%s", index, total, action, step.get("xpath"))

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
        self,
        page: Page,
        step: Dict[str, Any],
        index: int,
        total: int
    ) -> None:
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
        xpath = step.get("xpath")
        xpath_text = xpath.lower() if isinstance(xpath, str) else ""
        step_url = self._normalize_url(step.get("url")) or ""
        url_text = f"{current_url} {step_url}".lower()
        keywords = ("video", "play", "vjs", "ananas", "播放器", "播放")
        return any(keyword in xpath_text for keyword in keywords) or any(keyword in url_text for keyword in keywords)

    async def _build_candidate_locators(self, page: Page, step: Dict[str, Any]) -> List[Locator]:
        selectors = step.get("selectors", [])
        xpath = step.get("xpath")
        
        if not selectors and (not isinstance(xpath, str) or not xpath.strip()):
            raise ValueError("动作缺少 xpath 或 selectors")
        
        if selectors:
            xpaths_to_try = selectors
        else:
            xpaths_to_try = [xpath]

        candidates: List[Locator] = []
        iframe_path = step.get("iframePath", [])
        
        # 对每个XPath进行智能修复，生成更多候选
        expanded_xpaths = []
        for xpath in xpaths_to_try:
            expanded_xpaths.extend(self._fix_xpath_if_needed(xpath))
        
        # 去重，保持原始顺序
        unique_xpaths = []
        seen = set()
        for xpath in expanded_xpaths:
            if xpath not in seen:
                seen.add(xpath)
                unique_xpaths.append(xpath)
        
        xpaths_to_try = unique_xpaths
        logger.info("构建定位器: 原始xpaths=%s, 修复后xpaths=%s, iframePath=%s", 
                   step.get("xpath") or step.get("selectors", []), xpaths_to_try, iframe_path)

        if isinstance(iframe_path, list) and iframe_path:
            frame_locator = None
            frame_path_valid = True
            for i, frame_xpath in enumerate(iframe_path):
                if not isinstance(frame_xpath, str) or not frame_xpath.strip():
                    frame_path_valid = False
                    logger.warning("iframe路径第 %s 项无效: %s", i, frame_xpath)
                    break
                
                # 处理特殊标记，如 __cross_origin_iframe__
                if frame_xpath.startswith("__"):
                    if frame_xpath == "__cross_origin_iframe__":
                        logger.info("检测到跨域iframe标记，尝试定位跨域iframe")
                        # 尝试查找页面中的跨域iframe（增加等待机制）
                        try:
                            # 等待iframe加载（最多等待10秒）
                            max_wait_attempts = 5
                            frame_locator_found = False
                            
                            for attempt in range(max_wait_attempts):
                                logger.info("等待iframe加载 (尝试 %s/%s)...", attempt + 1, max_wait_attempts)
                                
                                # 获取所有iframe
                                frames = page.frames
                                logger.info("当前检测到 %s 个frames", len(frames))
                                
                                if len(frames) > 1:
                                    # 第一个frame通常是顶层页面，跳过
                                    for frame_idx, frame in enumerate(frames[1:], start=1):
                                        try:
                                            frame_url = frame.url
                                            logger.info("检查frame[%s]: URL=%s", frame_idx, frame_url[:100] if frame_url else "None")
                                            # 检查是否跨域（与当前页面URL比较）
                                            if frame_url and page.url:
                                                current_domain = self._extract_domain(page.url)
                                                frame_domain = self._extract_domain(frame_url)
                                                logger.info("域名比较: 当前=%s, frame=%s", current_domain, frame_domain)
                                                
                                                # 更宽松的跨域检测
                                                if current_domain != frame_domain:
                                                    logger.info("找到跨域iframe: 索引=%s, URL=%s", frame_idx, frame_url)
                                                    # 使用frame索引创建frame_locator
                                                    frame_locator = page.frame_locator(f"iframe").nth(frame_idx-1)
                                                    frame_locator_found = True
                                                    break
                                                elif attempt == max_wait_attempts - 1:
                                                    # 最后一次尝试，即使域名相同也使用第一个iframe
                                                    logger.info("未找到明显跨域iframe，使用第一个iframe")
                                                    frame_locator = page.frame_locator(f"iframe").first
                                                    frame_locator_found = True
                                                    break
                                        except Exception as e:
                                            logger.debug("检查frame异常: %s", str(e)[:100])
                                            continue
                                    
                                    if frame_locator_found:
                                        break
                                
                                # 如果没有找到iframe，等待2秒后重试
                                if not frame_locator_found:
                                    if attempt < max_wait_attempts - 1:
                                        logger.info("iframe未找到，等待2秒后重试...")
                                        await asyncio.sleep(2)
                                    else:
                                        logger.warning("等待iframe超时，尝试直接定位iframe标签")
                                        # 最后尝试：直接查找iframe元素
                                        iframe_count = await page.locator("iframe").count()
                                        logger.info("直接查找找到 %s 个iframe元素", iframe_count)
                                        if iframe_count > 0:
                                            frame_locator = page.frame_locator("iframe").first
                                            frame_locator_found = True
                                        else:
                                            logger.warning("页面中没有iframe，降级为顶层定位")
                                            frame_path_valid = False
                                            break
                            
                            if not frame_locator_found and frame_locator is None:
                                logger.warning("定位跨域iframe失败，降级为顶层定位")
                                frame_path_valid = False
                                break
                                
                        except Exception as e:
                            logger.warning("定位跨域iframe失败: %s", str(e)[:200])
                            frame_path_valid = False
                            break
                        # 特殊标记处理完毕，继续下一层
                        logger.info("进入第 %s 层iframe (特殊标记处理)", i + 1)
                        continue
                    else:
                        logger.warning("未知的特殊iframe标记: %s，降级为顶层定位", frame_xpath)
                        frame_path_valid = False
                        break
                
                logger.info("等待第 %s 层iframe元素附加: %s", i + 1, frame_xpath)
                try:
                    if frame_locator is None:
                        await page.locator(f"xpath={frame_xpath}").first.wait_for(
                            state="attached", timeout=self.iframe_wait_ms
                        )
                    else:
                        await frame_locator.locator(f"xpath={frame_xpath}").first.wait_for(
                            state="attached", timeout=self.iframe_wait_ms
                        )
                    logger.info("第 %s 层iframe元素已附加", i + 1)
                except PlaywrightTimeoutError as e:
                    frame_path_valid = False
                    logger.warning("第 %s 层iframe元素等待超时: %s", i + 1, str(e)[:200])
                    break
                except Exception as e:
                    frame_path_valid = False
                    logger.warning("第 %s 层iframe元素等待异常: %s", i + 1, str(e)[:200])
                    break

                logger.info("进入第 %s 层iframe: %s", i + 1, frame_xpath)
                if frame_locator is None:
                    frame_locator = page.frame_locator(f"xpath={frame_xpath}")
                else:
                    frame_locator = frame_locator.frame_locator(f"xpath={frame_xpath}")

            if frame_path_valid and frame_locator is not None:
                for xpath_to_try in xpaths_to_try:
                    candidates.append(frame_locator.locator(f"xpath={xpath_to_try}"))
                logger.info("添加iframe内定位器，共 %s 个", len(xpaths_to_try))
            else:
                logger.warning("iframePath 不可用，降级为顶层定位: %s", iframe_path)

        for xpath_to_try in xpaths_to_try:
            candidates.append(page.locator(f"xpath={xpath_to_try}"))
        logger.info("添加顶层定位器，共 %s 个", len(xpaths_to_try))

        step_url = self._normalize_url(step.get("url")) or ""
        if self._is_video_url(step_url):
            video_xpath = "//button[contains(@class, 'vjs-big-play-button')]"
            candidates.append(page.locator(f"xpath={video_xpath}"))
            logger.info("添加视频播放按钮定位器")

        return candidates

    async def _safe_wait_then_click(self, locators: List[Locator]) -> None:
        last_error: Optional[Exception] = None
        for i, locator in enumerate(locators):
            logger.info("尝试第 %s 个定位器...", i + 1)
            try:
                await locator.first.wait_for(state="attached", timeout=self.iframe_wait_ms)
                await asyncio.sleep(0.5)
                await locator.first.wait_for(state="visible", timeout=self.default_timeout_ms)
                await locator.first.click(timeout=self.default_timeout_ms)
                logger.info("第 %s 个定位器点击成功", i + 1)
                return
            except PlaywrightTimeoutError as error:
                last_error = error
                logger.warning("第 %s 个定位器超时: %s", i + 1, str(error)[:200])
                try:
                    await asyncio.sleep(1)
                    await locator.first.wait_for(state="attached", timeout=self.iframe_wait_ms)
                    await locator.first.wait_for(state="visible", timeout=self.retry_timeout_ms)
                    await locator.first.click(timeout=self.retry_timeout_ms)
                    logger.info("第 %s 个定位器延长等待后点击成功", i + 1)
                    return
                except PlaywrightTimeoutError as retry_error:
                    last_error = retry_error
                    logger.warning("第 %s 个定位器延长等待后仍然超时", i + 1)
                    continue
                except Exception as e:
                    last_error = e
                    logger.warning("第 %s 个定位器出现异常: %s", i + 1, str(e)[:200])
                    continue
        raise TimeoutError("元素点击失败：已尝试所有定位策略") from last_error

    async def _safe_wait_then_fill(self, locators: List[Locator], value: str) -> None:
        last_error: Optional[Exception] = None
        for locator in locators:
            try:
                await locator.first.wait_for(state="visible", timeout=self.default_timeout_ms)
                await locator.first.fill(value, timeout=self.default_timeout_ms)
                return
            except PlaywrightTimeoutError as error:
                last_error = error
                logger.warning("输入元素等待超时，尝试延长等待后重试")
                try:
                    await locator.first.wait_for(state="visible", timeout=self.retry_timeout_ms)
                    await locator.first.fill(value, timeout=self.retry_timeout_ms)
                    return
                except PlaywrightTimeoutError as retry_error:
                    last_error = retry_error
                    continue
        raise TimeoutError("输入失败：已尝试所有定位策略") from last_error

    def _extract_domain(self, url: str) -> str:
        """从URL中提取域名（粗略实现）"""
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
        """智能修复XPath，返回可能的修复版本列表"""
        if not isinstance(xpath, str):
            return []
        
        fixed_paths = [xpath]
        
        # 修复1: 如果XPath以/div[2]结尾（没有/a[1]），尝试添加/a[1]
        if xpath.endswith("/div[2]"):
            fixed = xpath + "/a[1]"
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)
        
        # 修复2: 如果XPath以/div[2]/a结尾（没有索引），尝试添加[1]
        elif xpath.endswith("/div[2]/a"):
            fixed = xpath + "[1]"
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)
        
        # 修复3: 如果XPath以/div[2]/a[1]结尾，但也尝试无索引版本
        elif xpath.endswith("/div[2]/a[1]"):
            fixed = xpath[:-3]  # 移除[1]
            fixed_paths.append(fixed)
            logger.debug("XPath修复: %s -> %s", xpath, fixed)
        
        # 修复4: 通用的绝对路径简化（移除[1]索引尝试相对路径）
        if xpath.startswith("/html/"):
            # 尝试将绝对路径转换为更灵活的相对路径
            # 例如：/html/body[1]/div[1]/div[1] -> //body//div[1]/div[1]
            import re
            simplified = re.sub(r'^/html/body\[1\]/', '//body//', xpath)
            simplified = re.sub(r'/div\[\d+\]/', '//div[', simplified)
            if simplified != xpath:
                fixed_paths.append(simplified)
                logger.debug("XPath简化: %s -> %s", xpath, simplified)
        
        return fixed_paths
