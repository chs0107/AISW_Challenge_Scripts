"""
개드립(dogdrip.net) 크롤러 - "인기글" (sort_index=popular)

구조 확인 완료 (2026-07-08, 실제 HTML 샘플 기반).
게시글 컨테이너: <li class="ed flex flex-left flex-middle webzine">

주의: 조회수(views)는 이 목록 페이지에 표시되지 않음 (댓글수/추천수만 표시됨).
필요하면 게시글 상세 페이지에 들어가서 따로 수집해야 함 (2차 작업, 지금은 생략).
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawler_utils import logger, polite_sleep
from selenium_utils import get_uc_driver, fetch_rendered_html

BASE_URL = "https://www.dogdrip.net/dogdrip?sort_index=popular"
DOMAIN = "https://www.dogdrip.net"


def parse_list_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    posts = []

    for li in soup.select("li.webzine"):
        title_link = li.select_one("h5.title a.title-link")
        if not title_link:
            continue

        title = title_link.get_text(strip=True)
        if not title:
            continue

        url = urljoin(DOMAIN, title_link["href"])
        document_srl = title_link.get("data-document-srl", "")

        # 댓글 수: 제목 옆에 붙는 숫자 span (예: 89)
        comment_count = 0
        comment_span = title_link.find_next_sibling("span")
        if comment_span:
            m = re.search(r"\d+", comment_span.get_text())
            if m:
                comment_count = int(m.group())

        # 추천수: fa-thumbs-up 아이콘 바로 다음 span의 숫자
        recommend = 0
        thumbs_icon = li.select_one("i.fa-thumbs-up")
        if thumbs_icon:
            icon_span = thumbs_icon.find_parent("span")
            if icon_span:
                next_span = icon_span.find_next_sibling("span")
                if next_span:
                    m = re.search(r"\d+", next_span.get_text())
                    if m:
                        recommend = int(m.group())

        # 작성 시간: fa-clock 아이콘이 있는 span의 텍스트
        date_text = ""
        clock_icon = li.select_one("i.fa-clock")
        if clock_icon and clock_icon.parent:
            date_text = clock_icon.parent.get_text(strip=True)

        # 작성자: class에 'member_'가 포함된 링크
        author_tag = li.select_one("a[class*='member_']")
        author = author_tag.get_text(strip=True) if author_tag else ""

        posts.append({
            "site": "개드립",
            "title": title,
            "url": url,
            "document_srl": document_srl,
            "author": author,
            "date": date_text,
            "recommend": recommend,
            "comment_count": comment_count,
        })

    return posts


def crawl(max_pages: int = None, start_page: int = 1, end_page: int = None):
    """
    start_page ~ end_page 범위의 목록 페이지만 수집.
    기존 호출 호환을 위해 max_pages도 계속 지원 (start_page=1, end_page=max_pages와 동일).
    """
    if end_page is None:
        end_page = max_pages if max_pages is not None else 10

    driver = get_uc_driver(headless=False)
    all_posts = []

    try:
        # 세션/쿠키가 없는 상태에서 원하는 페이지로 바로 들어가면 첫 요청이 실패하는
        # 현상이 있어서, 아무 페이지나 한 번 먼저 방문해서 세션을 예열해둠.
        logger.info("세션 예열 중 (첫 요청 실패 방지)...")
        fetch_rendered_html(driver, "https://www.dogdrip.net/dogdrip", wait_sec=4.0)
        polite_sleep(2.0, 3.0)

        for page in range(start_page, end_page + 1):
            url = f"{BASE_URL}&page={page}"
            logger.info(f"[개드립] {page}페이지 요청 중...")

            posts = []
            # 빈 페이지가 나오면 바로 "끝"으로 단정하지 않고,
            # 대기 시간을 늘려가며 최대 3번 재시도 (일시적 차단/지연 대응)
            for attempt in range(3):
                wait_sec = 3.0 + attempt * 4  # 3초 -> 7초 -> 11초
                html = fetch_rendered_html(driver, url, wait_sec=wait_sec)
                posts = parse_list_page(html)
                if posts:
                    break
                logger.warning(
                    f"{page}페이지에서 게시글 0개 (시도 {attempt + 1}/3, {wait_sec}초 대기함)"
                )
                polite_sleep(3.0, 5.0)

            if not posts:
                logger.warning(f"{page}페이지: 재시도 후에도 게시글 없음. 이 구간에서 중단")
                break

            all_posts.extend(posts)
            logger.info(f"{page}페이지: {len(posts)}개 수집 (누적 {len(all_posts)}개)")
            polite_sleep()
    finally:
        driver.quit()

    return all_posts


if __name__ == "__main__":
    posts = crawl(max_pages=3)
    print(f"\n총 {len(posts)}개 게시글 수집")
    for p in posts[:5]:
        print(p)
