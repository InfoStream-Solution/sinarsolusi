(() => {
  const terminalStatuses = new Set(["succeeded", "failed"]);

  function buildStatusUrl(template, jobId) {
    return template.replace("/0/", `/${jobId}/`);
  }

  function clearNode(node) {
    node.replaceChildren();
  }

  function createTextItem(label, value) {
    const li = document.createElement("li");
    li.textContent = `${label}: ${value}`;
    return li;
  }

  function renderGenericResult(target, payload) {
    const isList = target.tagName === "UL" || target.tagName === "OL";
    const summaryEntries = Object.entries(payload.result_summary || {});
    const lines = [
      ["Job", `#${payload.job_id}`],
      ["Domain", payload.domain],
      ["Status", payload.status],
    ];

    if (isList) {
      const items = lines.map(([label, value]) => createTextItem(label, value));
      if (payload.error_message) {
        items.push(createTextItem("Error", payload.error_message));
      }
      if (summaryEntries.length > 0) {
        items.push(createTextItem("Result", JSON.stringify(payload.result_summary)));
      }
      target.replaceChildren(...items);
      return;
    }

    const wrapper = document.createElement("article");
    wrapper.className = "module aligned";

    const heading = document.createElement("h3");
    heading.textContent = `Job #${payload.job_id}`;
    wrapper.appendChild(heading);

    const definitionList = document.createElement("dl");
    for (const [label, value] of lines) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      definitionList.append(dt, dd);
    }
    wrapper.appendChild(definitionList);

    if (summaryEntries.length > 0) {
      const summaryHeading = document.createElement("h4");
      summaryHeading.textContent = "Result summary";
      wrapper.appendChild(summaryHeading);

      const summaryList = document.createElement("ul");
      for (const [key, value] of summaryEntries) {
        summaryList.appendChild(createTextItem(key, String(value)));
      }
      wrapper.appendChild(summaryList);
    }

    if (payload.error_message) {
      const error = document.createElement("p");
      error.textContent = payload.error_message;
      wrapper.appendChild(error);
    }

    target.replaceChildren(wrapper);
  }

  function renderError(target, message) {
    target.replaceChildren();
    const paragraph = document.createElement("p");
    paragraph.textContent = message;
    target.appendChild(paragraph);
  }

  function createPollTransport({ intervalMs = 1500 } = {}) {
    let stopped = false;
    let timerId = null;

    async function tick(statusUrlTemplate, jobId, onUpdate, onError) {
      if (stopped) {
        return;
      }

      try {
        const response = await fetch(buildStatusUrl(statusUrlTemplate, jobId), {
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
          },
        });
        if (!response.ok) {
          throw new Error(`Status request failed with HTTP ${response.status}`);
        }
        const payload = await response.json();
        onUpdate(payload);
        if (!terminalStatuses.has(payload.status)) {
          timerId = window.setTimeout(() => {
            void tick(statusUrlTemplate, jobId, onUpdate, onError);
          }, intervalMs);
        }
      } catch (error) {
        onError(error);
      }
    }

    return {
      start(statusUrlTemplate, jobId, onUpdate, onError) {
        stopped = false;
        void tick(statusUrlTemplate, jobId, onUpdate, onError);
      },
      stop() {
        stopped = true;
        if (timerId !== null) {
          window.clearTimeout(timerId);
          timerId = null;
        }
      },
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-seed-dashboard]");
    if (!root) {
      return;
    }

    const form = root.querySelector("#seed-job-form");
    const submitButton = form?.querySelector('button[type="submit"]');
    const resultTarget = root.querySelector("[data-job-result]");
    const createUrl = root.dataset.createUrl;
    const statusUrlTemplate = root.dataset.statusUrlTemplate;

    if (!form || !submitButton || !resultTarget || !createUrl || !statusUrlTemplate) {
      return;
    }

    const pollTransport = createPollTransport();

    function setBusy(isBusy) {
      submitButton.disabled = isBusy || submitButton.dataset.disabledByPolicy === "true";
      submitButton.textContent = isBusy ? "Running..." : "Run Seed";
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      pollTransport.stop();
      setBusy(true);

      try {
        const response = await fetch(createUrl, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
          },
        });
        const payload = await response.json();

        if (!response.ok) {
          renderGenericResult(resultTarget, {
            job_id: "n/a",
            domain: form.querySelector('select[name="domain"]')?.value || "",
            status: "validation_error",
            result_summary: payload.errors || {},
            error_message: "Unable to queue seed job.",
          });
          setBusy(false);
          return;
        }

        renderGenericResult(resultTarget, payload);
        if (terminalStatuses.has(payload.status)) {
          setBusy(false);
          return;
        }

        pollTransport.start(
          statusUrlTemplate,
          payload.job_id,
          (nextPayload) => {
            renderGenericResult(resultTarget, nextPayload);
            if (terminalStatuses.has(nextPayload.status)) {
              setBusy(false);
            }
          },
          (error) => {
            renderError(resultTarget, error instanceof Error ? error.message : String(error));
            setBusy(false);
          },
        );
      } catch (error) {
        renderError(resultTarget, error instanceof Error ? error.message : String(error));
        setBusy(false);
      }
    });
  });
})();
