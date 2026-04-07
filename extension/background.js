let recording = false;
let recordingStartTime = 0;
let actions = [];

function exportActionsAsJson() {
  const fileName = `recording-${Date.now()}.json`;
  const payload = JSON.stringify(actions, null, 2);
  const dataUrl = `data:application/json;charset=utf-8,${encodeURIComponent(payload)}`;

  chrome.downloads.download({
    url: dataUrl,
    filename: fileName,
    saveAs: true
  });
}

function normalizeEventAction(rawAction) {
  if (rawAction === "input") {
    return "type";
  }
  return rawAction;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "START_RECORDING") {
    recording = true;
    recordingStartTime = Date.now();
    actions = [];
    chrome.storage.local.set({
      recording,
      recordingStartTime
    });
    sendResponse({ ok: true });
    return true;
  }

  if (message?.type === "STOP_RECORDING") {
    recording = false;
    chrome.storage.local.set({ recording });
    actions.sort((a, b) => a.time - b.time);
    exportActionsAsJson();
    sendResponse({
      ok: true,
      count: actions.length
    });
    return true;
  }

  if (message?.type === "GET_RECORDING_STATE") {
    sendResponse({ recording });
    return true;
  }

  if (message?.type === "RECORD_EVENT") {
    if (!recording) {
      sendResponse({ ok: true, skipped: true });
      return true;
    }

    const absoluteTime = typeof message.timestamp === "number" ? message.timestamp : Date.now();
    const relativeTime = Math.max(0, absoluteTime - recordingStartTime);

    // v2.0 格式：支持混合策略定位系统
    const actionRecord = {
      action: normalizeEventAction(message.action),
      xpath: message.xpath || null,
      value: message.value ?? null,
      url: message.url || sender?.url || null,
      iframePath: Array.isArray(message.iframePath) ? message.iframePath : [],
      time: relativeTime,
      // v2.0 新增字段
      selectorType: message.selectorType || null,
      selectorPriority: message.selectorPriority || null,
      cssSelector: message.cssSelector || null,
      readySelector: message.readySelector || null,
      selectors: Array.isArray(message.selectors) ? message.selectors : null
    };

    actions.push(actionRecord);

    sendResponse({ ok: true });
    return true;
  }

  return false;
});
