"""
1단계: 사이트 접근성 & HTML 구조 진단 스크립트

하는 일:
1) sites_config.py에 URL이 채워진 사이트들에 requests로 접근 시도
2) 성공하면 raw_html/{사이트키}.html 로 저장
3) 실패하거나 봇 차단으로 의심되면 결과에 표시

실행 후 할 일:
- raw_html/ 폴더에 저장된 .html 파일을 VS Code에서 열어서
  게시글이 반복되는 태그 구조(예: <tr>, <li>, <div class="...">)를 확인
- 확인이 어려우면 그 부분(게시글 1개 분량 HTML)을 복사해서 나한테 보내주면
  정확한 크롤링 코드(제목/글쓴이/날짜/조회수/추천수/링크 추출)를 이어서 작성함
- "봇 차단 의심"으로 나온 사이트는 requests로는 못 뚫으므로
  Selenium 사용이 필요하다는 뜻 (다음 단계에서 안내)
"""
from crawler_utils import get_session, fetch, looks_blocked, save_debug_html, polite_sleep, logger
from sites_config import SITES


def main():
    session = get_session()
    results = []

    for key, info in SITES.items():
        url = info["url"]
        label = info["label"]

        if not url:
            logger.warning(f"[건너뜀] {label}: URL 미등록 (sites_config.py에서 채워야 함)")
            results.append((label, "URL 없음 - 주소 확인 필요", None))
            continue

        logger.info(f"[요청] {label} -> {url}")
        html = fetch(session, url)
        polite_sleep()

        if html is None:
            results.append((label, "요청 실패 (네트워크/HTTP 오류)", None))
            continue

        if looks_blocked(html):
            results.append((label, "봇 차단/로그인 필요 의심 (Selenium 검토 필요)", None))
            continue

        path = save_debug_html(key, html)
        results.append((label, "성공", str(path)))

    print("\n===== 진단 결과 =====")
    for label, status, path in results:
        line = f"- {label}: {status}"
        if path:
            line += f" -> {path}"
        print(line)


if __name__ == "__main__":
    main()
