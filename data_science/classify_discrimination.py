"""
남녀차별 표현 분류 스크립트 (Step 2)
------------------------------------------------
- 대상 파일: 개드립_최종.xlsx, 워마드_최종.xlsx
- text 컬럼(제목/본문/댓글)을 LLM으로 분류
- 결과는 classification_results/{site}_classification.csv 로 저장
  -> 다음 단계(Step 3)에서 원본 엑셀과 id 기준으로 병합
- fewshot_examples.json(UnSmile 데이터셋 기반)을 프롬프트에 함께 넣어 판별 정밀도를 보정
  (build_fewshot_examples.py로 생성. 없으면 few-shot 없이 진행)

사전 준비
- pip install anthropic pandas openpyxl
- 환경변수 ANTHROPIC_API_KEY 설정 필요
- (권장) build_fewshot_examples.py를 먼저 실행해 fewshot_examples.json 생성
"""

import json
import time
from pathlib import Path

import pandas as pd
from anthropic import Anthropic

# ------------------ 설정 ------------------
INPUT_DIR = Path(".")  # 엑셀 파일이 있는 경로로 수정
FILES = {
    "dogdrip": "개드립_최종.xlsx",
    "womad": "워마드_최종.xlsx",
}
OUTPUT_DIR = Path("./classification_results")
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "claude-haiku-4-5-20251001"  # 대량 처리 -> 속도/비용 우선. 정확도 우선이면 "claude-sonnet-5"로 교체
BATCH_SIZE = 10
MAX_RETRIES = 3
FEWSHOT_PATH = Path("fewshot_examples.json")

client = Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

BASE_TAXONOMY_PROMPT = """너는 한국 온라인 커뮤니티 게시글/댓글에서 성차별·혐오 표현을 판별하는 분류기다.
아래 분류체계에 따라 입력된 각 텍스트를 판별하라.

[1차] 차별/혐오 표현 여부: true / false
 - 특정 성별 전체를 대상으로 한 비하, 조롱, 낙인, 폭력 정당화 표현이 있으면 true
 - 정책에 대한 단순 찬반 의견(예: "군가산점 폐지해야 한다")은 그 자체로는 false
 - 단, 정책/제도를 근거로 특정 성별의 희생이나 기여를 조롱·폄하하면 true (유형 G)
 - 노골적인 멸칭이 없어도 성립할 수 있다: 은유·냉소적 비유로 조롱하거나(예: 특정 집단을 벌레·질병에 빗댐),
   외모·능력에 대한 고정관념을 일반화하거나, "재기"/"재기해" 같은 자살 암시 은어로 조롱하는 경우도 true로 판단하라

[2차] 대상 성별 (1차가 true일 때만): "여성" / "남성"
 - 1차가 false면 null
 - 한 문장에 남녀 관련 단어·멸칭이 동시에 등장하면, 단순히 더 많이 언급된 쪽이 아니라
   실제로 조롱·비하의 화살이 향하는 대상이 누구인지를 기준으로 판단하라
   (예: 여성 멸칭을 인용하면서 실제로는 남성을 공격하는 문장이면 대상은 남성)

[3차] 세부 유형 (1차가 true일 때만, 다중 선택 가능, 최소 1개):
 A. 멸칭·낙인 표현 - 특정 성별 지칭 멸칭 사용, 혹은 멸칭 없이도 집단 전체를 낙인찍는 일반화
 B. 외모·신체 비하
 C. 능력·지적 비하 - 지적 능력, 사회적 역할 수행 능력이 열등하다는 일반화
 D. 성적 대상화·성적 비하
 E. 경제적 프레임 - 데이트비용, 기생·무임승차 등 경제적 착취 서사
 F. 폭력 옹호·조장 - 신체적 폭력, 성범죄, 자살 조롱 등을 정당화·조장
 G. 기여·희생 폄하 - 병역, 가사·돌봄노동 등 사회적 의무·희생·기여를 무시하거나 깎아내림

각 텍스트에 대해 classify_texts 도구를 사용해 결과만 반환하라. 텍스트를 옮겨 적지 말 것."""


def build_taxonomy_prompt() -> str:
    """fewshot_examples.json이 있으면 1차/2차 판별 예시로 프롬프트에 삽입한다.
    출처: Korean UnSmile Dataset (Smilegate AI, CC-BY-NC-ND 4.0, 비상업적 이용)
    3차 세부유형(A~G)은 이 데이터셋에 없는 자체 기준이라 few-shot에는 포함하지 않는다."""
    if not FEWSHOT_PATH.exists():
        print("[안내] fewshot_examples.json 없음 -> few-shot 없이 진행 (build_fewshot_examples.py 실행 권장)")
        return BASE_TAXONOMY_PROMPT

    with open(FEWSHOT_PATH, "r", encoding="utf-8") as f:
        examples = json.load(f)

    lines = ["\n[참고 예시] (1차/2차 판별 기준 보정용, UnSmile 데이터셋 기반)"]
    for ex in examples:
        note = f' ({ex["note"]})' if ex.get("note") else ""
        if ex["is_discriminatory"]:
            lines.append(f'- "{ex["text"]}" -> 차별표현 O, 대상: {ex["target_gender"]}{note}')
        else:
            lines.append(f'- "{ex["text"]}" -> 차별표현 X (욕설/비속어가 있어도 특정 성별 비하가 아니면 X){note}')

    return BASE_TAXONOMY_PROMPT + "\n" + "\n".join(lines)


TAXONOMY_PROMPT = build_taxonomy_prompt()

TOOL_SCHEMA = {
    "name": "classify_texts",
    "description": "배치 내 각 텍스트에 대한 분류 결과 반환",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "description": "배치 내 순번(0부터 시작)"},
                        "is_discriminatory": {"type": "boolean"},
                        "target_gender": {
                            "type": ["string", "null"],
                            "enum": ["여성", "남성", None],
                        },
                        "types": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G"]},
                        },
                    },
                    "required": ["index", "is_discriminatory", "target_gender", "types"],
                },
            }
        },
        "required": ["results"],
    },
}


def classify_batch(texts: list[str]) -> list[dict]:
    """텍스트 배치를 LLM으로 분류. 실패 시 재시도.
    시스템 프롬프트(분류기준+few-shot)는 매 호출마다 동일하므로 prompt caching을 적용해
    반복되는 입력 토큰 비용을 최대 90%까지 절감한다."""
    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                temperature=0,  # 분류 작업은 정답이 있는 태스크이므로 재현성을 위해 고정
                system=[
                    {
                        "type": "text",
                        "text": TAXONOMY_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "classify_texts"},
                messages=[
                    {"role": "user", "content": f"다음 {len(texts)}개 텍스트를 분류하라:\n{numbered}"}
                ],
            )
            # 캐시 적중 여부 확인용 로그 (usage.cache_read_input_tokens > 0 이면 캐시 적중)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
                cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
                if cache_read or cache_write:
                    print(f"    [캐시] read={cache_read} write={cache_write}")
            for block in resp.content:
                if block.type == "tool_use":
                    results = block.input["results"]
                    if len(results) == len(texts):
                        return results
            raise ValueError("결과 개수 불일치 또는 tool_use 없음")
        except Exception as e:
            print(f"  [재시도 {attempt + 1}/{MAX_RETRIES}] 오류: {e}")
            time.sleep(2 ** attempt)
    # 전부 실패하면 수동 검토용 빈 값 반환
    return [
        {"index": i, "is_discriminatory": None, "target_gender": None, "types": []}
        for i in range(len(texts))
    ]


def process_file(site: str, filename: str):
    print(f"\n=== {site} ({filename}) 처리 시작 ===")
    df = pd.read_excel(INPUT_DIR / filename)
    df = df[df["text"].notna() & (df["text"].astype(str).str.strip() != "")].reset_index(drop=True)

    checkpoint_path = OUTPUT_DIR / f"{site}_classification.csv"
    done_ids = set()
    results_rows = []
    if checkpoint_path.exists():
        prev = pd.read_csv(checkpoint_path)
        done_ids = set(prev["id"])
        results_rows = prev.to_dict("records")
        print(f"기존 진행 결과 {len(done_ids)}건 발견, 이어서 진행")

    remaining = df[~df["id"].isin(done_ids)].reset_index(drop=True)
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"분류 대상 {len(remaining)}건, 배치 {total_batches}개")

    for b in range(total_batches):
        batch_df = remaining.iloc[b * BATCH_SIZE:(b + 1) * BATCH_SIZE].reset_index(drop=True)
        if batch_df.empty:
            continue
        texts = batch_df["text"].astype(str).tolist()
        classified = classify_batch(texts)

        for c in classified:
            row = batch_df.iloc[c["index"]]
            results_rows.append({
                "id": row["id"],
                "post_id": row["post_id"],
                "type": row["type"],
                "is_discriminatory": c["is_discriminatory"],
                "target_gender": c["target_gender"],
                "types": ",".join(c["types"]) if c["types"] else "",
            })

        pd.DataFrame(results_rows).to_csv(checkpoint_path, index=False, encoding="utf-8-sig")
        print(f"  배치 {b + 1}/{total_batches} 완료 (누적 {len(results_rows)}건)")
        time.sleep(1)  # API rate limit 여유

    print(f"=== {site} 처리 완료: 총 {len(results_rows)}건 -> {checkpoint_path} ===")


if __name__ == "__main__":
    for site, filename in FILES.items():
        process_file(site, filename)
