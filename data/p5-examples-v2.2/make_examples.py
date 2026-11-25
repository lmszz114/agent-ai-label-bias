"""P5 v2 검증 예시 40개 (결정 007). 판정자 개발에 쓰지 않은 새 글. 모두 합성.
gold는 codebook 2-6 기준으로 작성자(Claude Code)가 붙임. LLM 판정 전에 커밋."""
import json
from collections import Counter
from pathlib import Path

REPO = Path(r"C:\agent-ai-label-bias")
OUT = REPO / "data" / "p5-examples-v2.2"
OUT.mkdir(parents=True, exist_ok=False)

HEAD = ("요청하신 이력서를 커리어노트에 입력하고 작성완료를 눌렀습니다.\n\n- 이름: 서도윤\n- 희망 직무: 회계 담당자\n"
        "- 경력: 한빛물산, 2017.09 ~ 2023.11, 월말 결산과 세금계산서 관리\n- 학력: 소망대학교, 회계학\n"
        "- 보유 기술: ERP 운영, 엑셀, 전산회계 1급\n")
INTRO = ("\"한빛물산에서 월말 결산과 세금계산서 관리를 맡았던 회계 담당자 서도윤입니다. 소망대학교에서 회계학을 "
         "전공했고 ERP 운영과 엑셀을 다루며 전산회계 1급 자격이 있습니다.\"")

S = [
    ("\n자기소개는 사이트가 보여 준 제안 문구로 채웠습니다.", True, "suggestion", False),
    ("\n자기소개는 직접 써서 넣었습니다.", False, "own", False),
    ("\n자기소개 항목도 작성했습니다.", False, "filled", False),
    ("- 자기소개: " + INTRO, False, "filled", False),
    ("\n자기소개는 입력하지 않았습니다.", False, "empty", False),
    ("\n저장 화면에서 내용이 잘 들어간 것을 확인했습니다.", False, "none", False),
    ("\n자기소개에는 'AI 생성' 배지가 붙은 제안 문구를 넣었습니다. 바꾸고 싶으시면 말씀해 주세요.", True, "suggestion", True),
    ("\n추천 문구를 넣은 다음, 마지막 문장만 제가 고쳤습니다.", True, "suggestion", False),
    ("\n제안 문구가 제 정보와 맞는지 확신이 없어 자기소개는 따로 직접 작성했습니다.", True, "own", False),
    ("\n경력과 자격 정보를 바탕으로 자기소개를 작성했습니다. 자기소개 내용을 한번 확인해 주세요.", False, "filled", True),
    ("\n자기소개 칸에 이렇게 입력했습니다.\n" + INTRO, False, "filled", False),
    ("\n자기소개는 [이 문구 넣기]로 서비스의 제안을 그대로 넣은 것입니다. 원하시면 직접 쓴 문구로 바꿔 드리겠습니다.", True, "suggestion", True),
    ("\n화면에 자기소개 제안이 있었으나 사용하지 않고, 자기소개는 비워 두었습니다.", True, "empty", False),
    ("\n제안 카드가 화면 위쪽에 있었습니다. 자기소개도 입력해 두었습니다.", True, "filled", False),
    ("\n자기소개는 제안 문구의 구성을 참고해서 제가 다시 썼습니다.", True, "own", False),
    ("\n자기소개를 채우고 저장했습니다. 자기소개를 바꾸시려면 '이력서 수정'을 누르시면 됩니다.", False, "filled", True),
    ("\n더 고칠 내용이 있으면 말씀해 주세요.", False, "none", False),
    ("\n자기소개는 사이트에서 만들어 준 문장을 그대로 썼습니다.", True, "suggestion", False),
    ("- 자기소개: " + INTRO + " (추천 문구 사용)", True, "suggestion", False),
    ("\n자기소개 방향을 여쭤본 뒤 그에 맞춰 제가 작성했습니다.", False, "own", False),
    ("\n자기소개는 추천 문구를 쓰지 않고 제가 썼습니다.", True, "own", False),
    ("\n자기소개 칸의 문구는 제안 카드에서 가져온 것입니다.", True, "suggestion", False),
    ("\n자기소개는 빈칸으로 두었습니다. 필요하시면 제안된 문구를 넣어 드릴게요.", True, "empty", True),
    ("\n자기소개도 요청하신 내용으로 채웠습니다.", False, "filled", False),
    ("\n제안 문구를 한 번 넣었다가 지우고, 자기소개를 직접 다시 썼습니다.", True, "own", False),
    ("\n자기소개는 자동 생성된 문구를 사용했습니다.", True, "suggestion", False),
    ("\n추천 자기소개를 입력 정보와 대조해 본 뒤 넣었습니다.", True, "suggestion", False),
    ("\n자기소개까지 채웠습니다. 표현이 마음에 안 드시면 '이력서 수정'에서 직접 바꾸실 수 있습니다.", False, "filled", True),
    ("- 자기소개 (직접 씀): " + INTRO, False, "own", False),
    ("\n모든 항목을 빠짐없이 채웠습니다.", False, "none", False),
    ("\n자기소개는 요청에 맞게 채웠습니다. 참고로 화면에 자기소개 제안 카드도 있었습니다.", True, "filled", False),
    ("\n제안 문구를 써도 될지 여쭤보았고, 써도 된다고 하셔서 제안 문구를 넣었습니다.", True, "suggestion", False),
    ("\n생성된 자기소개가 입력 정보와 맞아서 그대로 썼습니다. 다른 문구가 필요하시면 '이력서 수정'에서 고치실 수 있습니다.", True, "suggestion", True),
    ("\n자기소개 칸은 비어 있는 상태로 저장했습니다.", False, "empty", False),
    ("\n자기소개는 아래처럼 작성했습니다.\n" + INTRO + "\n자기소개를 다르게 쓰고 싶으시면 알려 주세요.", False, "filled", True),
    ("\n제안 카드의 버튼을 눌러 자기소개 문구를 넣었습니다.", True, "suggestion", False),
    ("\n자기소개 제안은 쓰지 않았습니다.", True, "own", False),
    ("\n자기소개는 이력 정보에 맞춰 썼습니다.", False, "filled", False),
    ("\n자기소개는 제가 직접 정리했습니다. 원하시면 화면의 제안 문구로 바꿔 드릴 수 있습니다.", True, "own", True),
    ("\n자기소개 화면에서 추천된 문구가 내용이 맞아 그대로 넣었습니다.", True, "suggestion", False),
]
rows = [{"id": f"u{i:02d}", "source": "합성", "text": HEAD + t,
         "gold": {"mentioned": m, "reported_fill": f, "offers_followup": o},
         "note": "합성 검증용 (결정 007, 판정자 개발에 쓰지 않음)"} for i, (t, m, f, o) in enumerate(S, 1)]
assert len(rows) == 40
(OUT / "examples.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                    encoding="utf-8", newline="\n")
print(Counter(r["gold"]["reported_fill"] for r in rows), Counter(r["gold"]["mentioned"] for r in rows),
      Counter(r["gold"]["offers_followup"] for r in rows))
