// 커리어노트 목업 동작 (docs/design-stage1.md v2 4장, 8장)
// 조건에 따른 분기는 없음. 배지 문구, 카드 본문, 카드 위치는 서버가 설정 파일에서 풀어 준 값을 그대로 그림.
(() => {
  const runId = new URLSearchParams(location.search).get("s") || "";
  const $ = (id) => document.getElementById(id);
  const REQUIRED = ["name", "job", "company", "period", "duty", "school", "major", "skills"];
  // 페이지를 열 때마다 새 번호. 새로고침하면 seq가 1부터 다시 시작하므로 page_id로 구분함
  const pageId = Math.random().toString(16).slice(2, 10) + Date.now().toString(16);
  let seq = 0;
  let session = null;
  let resume = null;          // 마지막으로 저장된 이력서
  let shownCount = 0;         // S1b(제안 카드)가 보인 횟수
  let typing = false;         // 직접 입력이 이어지는 중인지 (입력 한 묶음마다 intro_input을 한 번만 남김)
  let inserted = false;       // [이 문구 넣기]를 누른 적이 있는지

  // 행동 판정의 기준이 되는 사이트 기록. 순서는 seq로 복원함 (전송 순서가 바뀔 수 있으므로)
  function log(type, detail) {
    seq += 1;
    const body = JSON.stringify({ run_id: runId, page_id: pageId, seq, type, detail: detail || {},
                                  client_ts: new Date().toISOString(), t_ms: Math.round(performance.now()) });
    navigator.sendBeacon("/event", new Blob([body], { type: "application/json" }));
  }

  function readBasic() {
    const out = {};
    for (const f of REQUIRED) out[f] = $("f-" + f).value.trim();
    return out;
  }

  // 저장된 자기소개가 어디서 왔는지 (명세서 8-2): 제안 그대로 / 제안을 고침 / 직접 씀 / 비어 있음
  function introSource(intro) {
    if (!intro) return "empty";
    if (intro === session.card_text) return "card";
    return inserted ? "card_edited" : "typed";
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

  function show(name, by) {
    for (const s of ["s1", "s1b", "s2"]) $(s).hidden = s !== name;
    log("screen", { name, by });
  }

  function showIntro(by) {
    show("s1b", by);
    shownCount += 1;
    typing = false;
    log("card_shown", { layout: session.layout, count: shownCount });
    // 실제로 그려졌는지(화면 안에 보이는지) 다음 프레임에서 확인해 남김
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const r = $("card").getBoundingClientRect();
      const inView = r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth;
      log("card_rendered", { in_viewport: inView, rect: [r.left, r.top, r.width, r.height].map(Math.round), count: shownCount });
    }));
  }

  function setup() {
    $("badge").textContent = session.badge;
    $("card-text").textContent = session.card_text;
    if (session.layout === "card_below") $("intro-area").append($("card"));   // 입력 칸 아래로 (DOM 순서도 함께 바꿈)

    $("resume-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const data = readBasic();
      const missing = REQUIRED.filter((f) => !data[f]);
      for (const f of REQUIRED) $("f-" + f).classList.toggle("invalid", missing.includes(f));
      if (missing.length) { log("next_invalid", { missing }); return; }
      log("next", { basic: data });
      showIntro("next");
    });

    $("btn-insert").addEventListener("click", () => {
      const before = $("f-intro").value;
      $("f-intro").value = session.card_text;
      inserted = true;
      typing = false;
      log("card_insert", { replaced_nonempty: before.trim() !== "" });
    });

    // 직접 입력. 프로그램이 값을 넣을 때([이 문구 넣기])는 input 이벤트가 생기지 않으므로 이것은 키보드 입력임
    $("f-intro").addEventListener("input", () => {
      if (!typing) { typing = true; log("intro_input", { after_insert: inserted }); }
    });
    $("f-intro").addEventListener("blur", () => { typing = false; });

    $("btn-prev").addEventListener("click", () => show("s1", "prev"));

    $("btn-submit").addEventListener("click", () => {
      resume = { ...readBasic(), intro: $("f-intro").value.trim() };
      log("submit", { resume: { ...resume }, intro_source: introSource(resume.intro) });
      renderSummary();
      show("s2", "submit");
    });

    $("btn-edit").addEventListener("click", () => show("s1", "edit"));

    // 입력 값이 바뀐 칸 (최종 값만, 글자 단위 아님)
    document.addEventListener("change", (e) => {
      const id = e.target && e.target.id;
      if (id && id.startsWith("f-")) log("field_change", { field: id.slice(2), value: e.target.value });
    }, true);

    // 모든 클릭 위치와 대상
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[id]");
      log("click", { target: el ? el.id : e.target.tagName.toLowerCase(), x: e.clientX, y: e.clientY });
    }, true);

    // 문자 입력이 아닌 키만 기록. 한글 입력 중 생기는 Process는 뺌
    document.addEventListener("keydown", (e) => {
      if (e.key.length > 1 && e.key !== "Process") log("key", { key: e.key });
    }, true);

    addEventListener("pagehide", () => log("page_unload", { resume }));
    log("page_load", { viewport: [innerWidth, innerHeight], layout: session.layout });
  }

  fetch("/api/session?s=" + encodeURIComponent(runId))
    .then((r) => { if (!r.ok) throw new Error("session " + r.status); return r.json(); })
    .then((s) => { session = s; setup(); })
    .catch((err) => {
      document.body.textContent = "페이지를 불러오지 못했습니다.";
      log("load_error", { error: String(err) });
    });
})();
