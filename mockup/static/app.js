// 커리어노트 목업 동작 (docs/design-stage1.md 4장, 8장)
// 조건에 따른 분기는 없음. 배지 문구, 팝업 본문, 버튼 순서는 서버가 설정 파일에서 풀어 준 값을 그대로 그림.
(() => {
  const runId = new URLSearchParams(location.search).get("s") || "";
  const $ = (id) => document.getElementById(id);
  const FIELDS = ["name", "job", "company", "period", "duty", "school", "major", "skills", "intro"];
  const REQUIRED = FIELDS.filter((f) => f !== "intro");
  // 페이지를 열 때마다 새 번호. 새로고침하면 seq가 1부터 다시 시작하므로 page_id로 구분함
  const pageId = Math.random().toString(16).slice(2, 10) + Date.now().toString(16);
  let seq = 0;
  let session = null;
  let resume = null;          // 마지막으로 저장된 이력서
  let popupDone = false;      // 팝업은 실행마다 첫 저장 때 한 번만 뜸
  let popupShownAt = null;

  // 행동 판정의 기준이 되는 사이트 기록. 순서는 seq로 복원함 (전송 순서가 바뀔 수 있으므로)
  function log(type, detail) {
    seq += 1;
    const body = JSON.stringify({ run_id: runId, page_id: pageId, seq, type, detail: detail || {},
                                  client_ts: new Date().toISOString(), t_ms: Math.round(performance.now()) });
    navigator.sendBeacon("/event", new Blob([body], { type: "application/json" }));
  }

  function readForm() {
    const out = {};
    for (const f of FIELDS) out[f] = $("f-" + f).value.trim();
    return out;
  }

  function renderSummary() {
    const rows = [["이름", resume.name], ["희망 직무", resume.job],
                  ["경력", `${resume.company}, ${resume.period}, ${resume.duty}`],
                  ["학력", `${resume.school}, ${resume.major}`], ["보유 기술", resume.skills]];
    if (resume.intro) rows.push(["자기소개", resume.intro]);
    const dl = $("summary");
    dl.textContent = "";
    for (const [k, v] of rows) {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v;
      dl.append(dt, dd);
    }
  }

  function showPopup() {
    if (document.activeElement) document.activeElement.blur();
    $("s2").inert = true;     // 팝업이 떠 있는 동안 뒤 화면은 클릭, 키보드 모두 막음
    $("overlay").hidden = false;
    popupShownAt = performance.now();
    log("popup_shown", { button_order: session.button_order });
    // 실제로 그려졌는지(화면 안에 보이는지) 다음 프레임에서 확인해 남김
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const r = $("popup").getBoundingClientRect();
      const inView = r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth;
      log("popup_rendered", { in_viewport: inView, rect: [r.left, r.top, r.width, r.height].map(Math.round) });
    }));
  }

  function closePopup(by) {
    $("overlay").hidden = true;
    $("s2").inert = false;
    popupDone = true;
    log("popup_closed", { by, visible_ms: Math.round(performance.now() - popupShownAt) });
  }

  function makeButton(kind, label, position) {
    const b = document.createElement("button");
    b.type = "button";
    b.id = kind === "apply" ? "btn-apply" : "btn-close";
    b.textContent = label;
    b.addEventListener("click", () => {
      log("popup_click", { button: kind, position });
      if (kind === "apply") {
        resume.intro = session.popup_text;
        $("f-intro").value = session.popup_text;
        renderSummary();
        log("resume_updated", { by: "popup_apply", resume: { ...resume } });
      }
      closePopup(kind);
    });
    return b;
  }

  function setup() {
    $("badge").textContent = session.badge;
    $("popup-text").textContent = session.popup_text;
    const order = session.button_order === "apply_first" ? ["apply", "close"] : ["close", "apply"];
    const labels = { close: "닫기", apply: "이력서에 적용하기" };
    $("popup-actions").append(...order.map((k, i) => makeButton(k, labels[k], i === 0 ? "left" : "right")));

    $("resume-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const data = readForm();
      const missing = REQUIRED.filter((f) => !data[f]);
      for (const f of REQUIRED) $("f-" + f).classList.toggle("invalid", missing.includes(f));
      if (missing.length) { log("submit_invalid", { missing }); return; }
      resume = data;
      log("submit", { resume: { ...resume } });
      $("s1").hidden = true;
      renderSummary();
      $("s2").hidden = false;
      log("screen", { name: "S2" });
      if (!popupDone) showPopup();   // S2와 같은 시점에 띄움 (지연 없음)
    });

    $("btn-edit").addEventListener("click", () => {
      $("s2").hidden = true;
      $("s1").hidden = false;
      log("screen", { name: "S1", by: "edit" });
    });

    // 입력 값이 바뀐 칸 (최종 값만, 글자 단위 아님)
    document.addEventListener("change", (e) => {
      const id = e.target && e.target.id;
      if (id && id.startsWith("f-")) log("field_change", { field: id.slice(2), value: e.target.value });
    }, true);

    // 모든 클릭 위치와 대상. 팝업 바깥(어두운 배경) 클릭도 기록만 하고 아무 일도 일어나지 않음
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[id]");
      log("click", { target: el ? el.id : e.target.tagName.toLowerCase(), x: e.clientX, y: e.clientY,
                     popup_open: !$("overlay").hidden });
    }, true);

    // 문자 입력이 아닌 키만 기록 (Esc로 팝업이 닫히지 않는다는 것을 확인하기 위함). 한글 입력 중 생기는 Process는 뺌
    document.addEventListener("keydown", (e) => {
      if (e.key.length > 1 && e.key !== "Process") log("key", { key: e.key, popup_open: !$("overlay").hidden });
    }, true);

    addEventListener("pagehide", () => log("page_unload", { resume }));
    log("page_load", { viewport: [innerWidth, innerHeight], button_order: session.button_order });
  }

  fetch("/api/session?s=" + encodeURIComponent(runId))
    .then((r) => { if (!r.ok) throw new Error("session " + r.status); return r.json(); })
    .then((s) => { session = s; setup(); })
    .catch((err) => {
      document.body.textContent = "페이지를 불러오지 못했습니다.";
      log("load_error", { error: String(err) });
    });
})();
