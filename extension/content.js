/**
 * Course Action Recorder - Smart Selector Engine v2.0
 * 混合策略定位系统 - 支持ID、文本、CSS类名、XPath多种定位方式
 */

// ==================== XPath 工具函数 ====================

function escapeXPathString(value) {
  if (!value) return "''";
  if (value.includes("'")) {
    if (value.includes('"')) {
      return 'concat(' + value.split("'").map(part => "'" + part + "'").join(', "\'", ') + ')';
    }
    return '"' + value + '"';
  }
  return "'" + value + "'";
}

function isUniqueXPath(xpath, rootDocument = document) {
  try {
    const result = rootDocument.evaluate(
      xpath,
      rootDocument,
      null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
      null
    );
    return result.snapshotLength === 1;
  } catch (error) {
    return false;
  }
}

function getElementPosition(element) {
  if (!element.parentElement) return 1;
  const siblings = Array.from(element.parentElement.children);
  const sameTagSiblings = siblings.filter(s => s.tagName === element.tagName);
  return sameTagSiblings.indexOf(element) + 1;
}

function buildPositionalXPath(element) {
  const path = [];
  let current = element;

  while (current && current.nodeType === Node.ELEMENT_NODE) {
    const tagName = current.tagName.toLowerCase();
    const position = getElementPosition(current);
    path.unshift(`${tagName}[${position}]`);
    current = current.parentElement;

    if (current && current.tagName && current.tagName.toLowerCase() === "html") {
      path.unshift("html");
      break;
    }
  }

  return "/" + path.join("/");
}

// ==================== CSS Selector 工具函数 ====================

function escapeCSSString(value) {
  if (!value) return '';
  return value.replace(/(["\\])/g, '\\$1');
}

function isUniqueCSSSelector(selector, rootDocument = document) {
  try {
    const elements = rootDocument.querySelectorAll(selector);
    return elements.length === 1;
  } catch (error) {
    return false;
  }
}

// ==================== 智能 Selector 构建器 ====================

class SmartSelectorBuilder {
  constructor(element) {
    this.element = element;
    this.selectors = [];
    this.tagName = element.tagName.toLowerCase();
  }

  /**
   * 构建所有可能的 selector，按优先级排序
   */
  build() {
    this.selectors = [];

    // 优先级 1: ID / data-id（最稳定）
    this._addIdSelector();

    // 优先级 2: 文本内容（学习通章节号等）
    this._addTextSelector();

    // 优先级 3: ARIA 属性
    this._addAriaSelector();

    // 优先级 4: 语义属性 data-*
    this._addDataAttributeSelector();

    // 优先级 5: CSS 类名
    this._addClassSelector();

    // 优先级 6: 相对路径（父元素有ID时）
    this._addRelativePathSelector();

    // 优先级 7: 完整 XPath（保底）
    this._addFullXPathSelector();

    // 按优先级排序
    this.selectors.sort((a, b) => a.priority - b.priority);

    return this.selectors;
  }

  /**
   * 优先级 1: ID / data-id
   */
  _addIdSelector() {
    // 标准 ID
    if (this.element.id) {
      const xpath = `//*[@id=${escapeXPathString(this.element.id)}]`;
      const css = `#${CSS.escape(this.element.id)}`;
      if (isUniqueXPath(xpath) || isUniqueCSSSelector(css)) {
        this.selectors.push({
          type: 'id',
          priority: 1,
          xpath: xpath,
          css: css,
          description: `ID: ${this.element.id}`
        });
      }
    }

    // data-id 属性
    const dataId = this.element.getAttribute('data-id');
    if (dataId) {
      const xpath = `//*[@data-id=${escapeXPathString(dataId)}]`;
      const css = `[data-id="${escapeCSSString(dataId)}"]`;
      this.selectors.push({
        type: 'data-id',
        priority: 1,
        xpath: xpath,
        css: css,
        description: `data-id: ${dataId}`
      });
    }
  }

  /**
   * 优先级 2: 文本内容（学习通特殊优化）
   */
  _addTextSelector() {
    const text = this.element.textContent?.trim();
    if (!text || text.length > 100) return;

    // 学习通章节号匹配（如 "1.1", "2.3"）
    const chapterMatch = text.match(/^(\d+\.\d+)/);
    if (chapterMatch) {
      const chapterNum = chapterMatch[1];
      this.selectors.push({
        type: 'chapter',
        priority: 2,
        xpath: `//span[contains(text(), ${escapeXPathString(chapterNum)})]`,
        description: `章节号: ${chapterNum}`,
        isXuexitongSpecial: true
      });
      return;
    }

    // 播放按钮特殊处理
    if (this.element.classList.contains('vjs-big-play-button')) {
      this.selectors.push({
        type: 'video-button',
        priority: 2,
        xpath: "//button[contains(@class, 'vjs-big-play-button')]",
        css: '.vjs-big-play-button',
        description: '视频播放按钮',
        isXuexitongSpecial: true
      });
      return;
    }

    // 返回按钮特殊处理
    if (this.element.classList.contains('icon-BackIcon') ||
        this.element.closest('[class*="BackIcon"]')) {
      this.selectors.push({
        type: 'back-button',
        priority: 2,
        xpath: "//i[contains(@class, 'icon-BackIcon')]",
        css: '.icon-BackIcon',
        description: '返回按钮',
        isXuexitongSpecial: true
      });
      return;
    }

    // 一般文本内容（短文本优先）
    if (text.length < 50 && text.length > 0) {
      // 避免纯数字或特殊字符
      if (/^[\d\s]+$/.test(text)) return;

      this.selectors.push({
        type: 'text',
        priority: 2,
        xpath: `//${this.tagName}[contains(text(), ${escapeXPathString(text)})]`,
        description: `文本: ${text.substring(0, 30)}`
      });
    }
  }

  /**
   * 优先级 3: ARIA 属性
   */
  _addAriaSelector() {
    const ariaLabel = this.element.getAttribute('aria-label');
    if (ariaLabel) {
      this.selectors.push({
        type: 'aria-label',
        priority: 3,
        xpath: `//${this.tagName}[@aria-label=${escapeXPathString(ariaLabel)}]`,
        css: `${this.tagName}[aria-label="${escapeCSSString(ariaLabel)}"]`,
        description: `ARIA: ${ariaLabel}`
      });
    }

    const ariaRole = this.element.getAttribute('role');
    if (ariaRole && ariaLabel) {
      this.selectors.push({
        type: 'aria-role',
        priority: 3,
        xpath: `//*[@role=${escapeXPathString(ariaRole)}][@aria-label=${escapeXPathString(ariaLabel)}]`,
        description: `Role: ${ariaRole}`
      });
    }
  }

  /**
   * 优先级 4: data-* 属性
   */
  _addDataAttributeSelector() {
    const dataAttrs = Array.from(this.element.attributes)
      .filter(attr => attr.name.startsWith('data-') && attr.name !== 'data-id');

    for (const attr of dataAttrs) {
      if (!attr.value || attr.value.length > 50) continue;

      const xpath = `//${this.tagName}[@${attr.name}=${escapeXPathString(attr.value)}]`;
      const css = `${this.tagName}[${attr.name}="${escapeCSSString(attr.value)}"]`;

      this.selectors.push({
        type: 'data-attribute',
        priority: 4,
        xpath: xpath,
        css: css,
        description: `${attr.name}: ${attr.value}`
      });
    }
  }

  /**
   * 优先级 5: CSS 类名
   */
  _addClassSelector() {
    if (this.element.classList.length === 0) return;

    // 过滤掉动态生成的类名（包含hash的）
    const stableClasses = Array.from(this.element.classList).filter(cls => {
      // 排除包含8位以上十六进制的类名（通常是动态hash）
      if (/[a-f0-9]{8,}/i.test(cls)) return false;
      // 排除包含长数字序列的类名
      if (/\d{5,}/.test(cls)) return false;
      // 排除以数字开头的类名
      if (/^\d/.test(cls)) return false;
      return true;
    });

    if (stableClasses.length === 0) return;

    // 单个稳定类名
    if (stableClasses.length >= 1) {
      const className = stableClasses[0];
      this.selectors.push({
        type: 'class',
        priority: 5,
        xpath: `//${this.tagName}[contains(@class, ${escapeXPathString(className)})]`,
        css: `${this.tagName}.${CSS.escape(className)}`,
        description: `类名: ${className}`
      });
    }

    // 多个类名组合（更精确）
    if (stableClasses.length >= 2) {
      const classConditions = stableClasses
        .map(cls => `contains(@class, ${escapeXPathString(cls)})`)
        .join(' and ');
      const cssSelector = stableClasses.map(cls => `.${CSS.escape(cls)}`).join('');

      this.selectors.push({
        type: 'class-combination',
        priority: 5,
        xpath: `//${this.tagName}[${classConditions}]`,
        css: `${this.tagName}${cssSelector}`,
        description: `类组合: ${stableClasses.join(', ')}`
      });
    }
  }

  /**
   * 优先级 6: 相对路径（父元素有ID时）
   */
  _addRelativePathSelector() {
    let parentWithId = this.element.parentElement;
    let depth = 0;
    const maxDepth = 3;

    while (parentWithId && depth < maxDepth) {
      if (parentWithId.id) {
        const parentId = parentWithId.id;
        const relativePath = this._buildRelativePath(parentWithId, this.element);

        if (relativePath) {
          this.selectors.push({
            type: 'relative',
            priority: 6,
            xpath: `//*[@id=${escapeXPathString(parentId)}]${relativePath}`,
            description: `相对路径 (父ID: ${parentId})`
          });
        }
        break;
      }
      parentWithId = parentWithId.parentElement;
      depth++;
    }
  }

  /**
   * 构建从父元素到当前元素的相对路径
   */
  _buildRelativePath(parent, target) {
    const path = [];
    let current = target;

    while (current && current !== parent) {
      const tagName = current.tagName.toLowerCase();
      const position = getElementPosition(current);
      path.unshift(`${tagName}[${position}]`);
      current = current.parentElement;
    }

    return path.length > 0 ? '/' + path.join('/') : null;
  }

  /**
   * 优先级 7: 完整 XPath（保底方案）
   */
  _addFullXPathSelector() {
    const fullXPath = buildPositionalXPath(this.element);
    this.selectors.push({
      type: 'xpath-full',
      priority: 7,
      xpath: fullXPath,
      description: '完整XPath（保底）'
    });
  }
}

// ==================== iframe 路径获取 ====================

function getIframePath() {
  if (window === window.top) {
    return [];
  }

  const path = [];
  let currentWindow = window;

  while (currentWindow !== currentWindow.top) {
    try {
      const parentWindow = currentWindow.parent;
      const parentDocument = parentWindow.document;
      const frameElements = Array.from(parentDocument.querySelectorAll("iframe, frame"));
      const frameElement = frameElements.find(candidate => candidate.contentWindow === currentWindow);

      if (!frameElement) {
        path.unshift("__unknown_iframe__");
        break;
      }

      // 使用 SmartSelectorBuilder 构建 iframe 的 selector
      const builder = new SmartSelectorBuilder(frameElement);
      const selectors = builder.build();

      // 使用优先级最高的 selector
      const bestSelector = selectors[0];
      path.unshift(bestSelector.xpath);

      currentWindow = parentWindow;
    } catch (error) {
      path.unshift("__cross_origin_iframe__");
      break;
    }
  }

  return path;
}

// ==================== 就绪状态检测 ====================

function findReadySelector(element) {
  let current = element.parentElement;
  let depth = 0;
  const maxDepth = 5;

  while (current && depth < maxDepth) {
    // 检查 ID
    if (current.id) {
      const byId = `//*[@id=${escapeXPathString(current.id)}]`;
      if (isUniqueXPath(byId)) {
        return byId;
      }
    }

    // 检查 data-* 属性
    const dataAttrs = Array.from(current.attributes)
      .filter(attr => attr.name.startsWith('data-'));
    for (const attr of dataAttrs) {
      const byData = `//*[@${attr.name}=${escapeXPathString(attr.value)}]`;
      if (isUniqueXPath(byData)) {
        return byData;
      }
    }

    current = current.parentElement;
    depth++;
  }

  return null;
}

// ==================== 消息发送 ====================

function sendRecordEvent(payload) {
  chrome.runtime.sendMessage(
    {
      type: "RECORD_EVENT",
      ...payload
    },
    () => {
      void chrome.runtime.lastError;
    }
  );
}

// ==================== 事件录制 ====================

function recordClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }

  // 使用 SmartSelectorBuilder 构建所有 selector
  const builder = new SmartSelectorBuilder(target);
  const selectors = builder.build();

  // 获取最佳 selector（优先级最高的）
  const bestSelector = selectors[0];
  const readySelector = findReadySelector(target);

  // 构建录制数据
  const recordData = {
    action: "click",
    xpath: bestSelector.xpath,
    cssSelector: bestSelector.css || null,
    selectorType: bestSelector.type,
    selectorPriority: bestSelector.priority,
    selectors: selectors.map(s => ({
      type: s.type,
      priority: s.priority,
      xpath: s.xpath,
      css: s.css || null
    })),
    value: null,
    url: window.location.href,
    iframePath: getIframePath(),
    readySelector: readySelector,
    timestamp: Date.now()
  };

  sendRecordEvent(recordData);
}

function recordInput(event) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement)) {
    return;
  }

  const builder = new SmartSelectorBuilder(target);
  const selectors = builder.build();
  const bestSelector = selectors[0];
  const readySelector = findReadySelector(target);

  const value = target instanceof HTMLSelectElement
    ? target.value
    : (target.value ?? "");

  const recordData = {
    action: "input",
    xpath: bestSelector.xpath,
    cssSelector: bestSelector.css || null,
    selectorType: bestSelector.type,
    selectorPriority: bestSelector.priority,
    selectors: selectors.map(s => ({
      type: s.type,
      priority: s.priority,
      xpath: s.xpath,
      css: s.css || null
    })),
    value: value,
    url: window.location.href,
    iframePath: getIframePath(),
    readySelector: readySelector,
    timestamp: Date.now()
  };

  sendRecordEvent(recordData);
}

// ==================== 初始化事件监听 ====================

document.addEventListener("click", recordClick, true);
document.addEventListener("input", recordInput, true);

console.log("[Course Recorder] Smart Selector Engine v2.0 已加载");
