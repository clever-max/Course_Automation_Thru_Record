function escapeXPathString(value) {
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
  if (!element.parentElement) {
    return 1;
  }
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

function buildStableXPath(element, rootDocument = document) {
  if (!element || element.nodeType !== Node.ELEMENT_NODE) {
    return "";
  }

  const tagName = element.tagName.toLowerCase();

  if (element.id) {
    const byId = `//*[@id=${escapeXPathString(element.id)}]`;
    if (isUniqueXPath(byId, rootDocument)) {
      return byId;
    }
  }

  const nameAttr = element.getAttribute("name");
  if (nameAttr) {
    const byName = `//${tagName}[@name=${escapeXPathString(nameAttr)}]`;
    if (isUniqueXPath(byName, rootDocument)) {
      return byName;
    }
  }

  const dataAttrs = Array.from(element.attributes).filter(attr => attr.name.startsWith("data-"));
  for (const attr of dataAttrs) {
    const byData = `//${tagName}[@${attr.name}=${escapeXPathString(attr.value)}]`;
    if (isUniqueXPath(byData, rootDocument)) {
      return byData;
    }
  }

  if (element.classList.length > 0) {
    const classNames = Array.from(element.classList).filter(Boolean);
    if (classNames.length > 0) {
      const classConditions = classNames.map(cls => `contains(@class, ${escapeXPathString(cls)})`).join(" and ");
      const byClass = `//${tagName}[${classConditions}]`;
      if (isUniqueXPath(byClass, rootDocument)) {
        return byClass;
      }
    }
  }

  if (element.parentElement) {
    const position = getElementPosition(element);
    const byPosition = `//${tagName}[${position}]`;
    if (isUniqueXPath(byPosition, rootDocument)) {
      return byPosition;
    }
  }

  return buildPositionalXPath(element);
}

function buildMultipleSelectors(element, rootDocument = document) {
  if (!element || element.nodeType !== Node.ELEMENT_NODE) {
    return [];
  }

  const selectors = [];
  const tagName = element.tagName.toLowerCase();

  if (element.id) {
    selectors.push(`//*[@id=${escapeXPathString(element.id)}]`);
  }

  const nameAttr = element.getAttribute("name");
  if (nameAttr) {
    selectors.push(`//${tagName}[@name=${escapeXPathString(nameAttr)}]`);
  }

  const dataAttrs = Array.from(element.attributes).filter(attr => attr.name.startsWith("data-"));
  for (const attr of dataAttrs) {
    selectors.push(`//${tagName}[@${attr.name}=${escapeXPathString(attr.value)}]`);
  }

  if (element.classList.length > 0) {
    const classNames = Array.from(element.classList).filter(Boolean);
    if (classNames.length > 0) {
      const classConditions = classNames.map(cls => `contains(@class, ${escapeXPathString(cls)})`).join(" and ");
      selectors.push(`//${tagName}[${classConditions}]`);
    }
  }

  const textContent = element.textContent?.trim();
  if (textContent && textContent.length < 50) {
    selectors.push(`//${tagName}[contains(text(), ${escapeXPathString(textContent)})]`);
  }

  if (element.parentElement) {
    const position = getElementPosition(element);
    selectors.push(`//${tagName}[${position}]`);
  }

  selectors.push(buildPositionalXPath(element));

  const uniqueSelectors = [...new Set(selectors)];
  return uniqueSelectors.filter(sel => isUniqueXPath(sel, rootDocument));
}

function findReadySelector(element, rootDocument = document) {
  let current = element.parentElement;
  let depth = 0;
  const maxDepth = 5;

  while (current && depth < maxDepth) {
    if (current.id) {
      const byId = `//*[@id=${escapeXPathString(current.id)}]`;
      if (isUniqueXPath(byId, rootDocument)) {
        return byId;
      }
    }

    const dataAttrs = Array.from(current.attributes).filter(attr => attr.name.startsWith("data-"));
    for (const attr of dataAttrs) {
      const byData = `//*[@${attr.name}=${escapeXPathString(attr.value)}]`;
      if (isUniqueXPath(byData, rootDocument)) {
        return byData;
      }
    }

    current = current.parentElement;
    depth++;
  }

  return null;
}

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

      const frameXPath = buildStableXPath(frameElement, parentDocument);
      path.unshift(frameXPath);
      currentWindow = parentWindow;
    } catch (error) {
      path.unshift("__cross_origin_iframe__");
      break;
    }
  }

  return path;
}

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

function recordClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }

  const selectors = buildMultipleSelectors(target);
  const xpath = selectors[0] || buildStableXPath(target);
  const readySelector = findReadySelector(target);

  sendRecordEvent({
    action: "click",
    xpath,
    selectors,
    value: null,
    url: window.location.href,
    iframePath: getIframePath(),
    readySelector,
    timestamp: Date.now()
  });
}

function recordInput(event) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement)) {
    return;
  }

  const selectors = buildMultipleSelectors(target);
  const xpath = selectors[0] || buildStableXPath(target);
  const readySelector = findReadySelector(target);
  const value = target instanceof HTMLSelectElement ? target.value : target.value ?? "";

  sendRecordEvent({
    action: "input",
    xpath,
    selectors,
    value,
    url: window.location.href,
    iframePath: getIframePath(),
    readySelector,
    timestamp: Date.now()
  });
}

document.addEventListener("click", recordClick, true);
document.addEventListener("input", recordInput, true);
