const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusEl = document.getElementById("status");

function setStatus(text) {
  statusEl.textContent = text;
}

function sendMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response);
    });
  });
}

async function refreshState() {
  try {
    const state = await sendMessage({ type: "GET_RECORDING_STATE" });
    setStatus(state?.recording ? "录制中..." : "未录制");
  } catch (error) {
    setStatus(`状态获取失败: ${error.message}`);
  }
}

startBtn.addEventListener("click", async () => {
  try {
    await sendMessage({ type: "START_RECORDING" });
    setStatus("已开始录制");
  } catch (error) {
    setStatus(`启动失败: ${error.message}`);
  }
});

stopBtn.addEventListener("click", async () => {
  try {
    const result = await sendMessage({ type: "STOP_RECORDING" });
    if (result?.count !== undefined) {
      setStatus(`已停止，导出 ${result.count} 条动作`);
    } else {
      setStatus("已停止录制");
    }
  } catch (error) {
    setStatus(`停止失败: ${error.message}`);
  }
});

refreshState();
