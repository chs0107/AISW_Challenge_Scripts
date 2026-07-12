"""
워마드 최종 크롤러
1) 목록 수집 (womad_scraper.crawl 재사용)
2) 게시글별 상세 페이지 방문 -> 본문 + 댓글(기본 화면이 오래된 순, 상위 20개) 수집
3) 엑셀로 저장 (output/워마드.xlsx)

컬럼: id, post_id, type(title/body/comment), text, author, date, url, views, recommend, comment_count
- views/recommend/comment_count는 type='title' 행에만 값이 채워짐
- Cloudflare 챌린지는 드라이버 시작 시 1회만 통과하면 됨 (같은 드라이버로 여러 페이지 이동)

예상 소요 시간: 게시글 200개 기준 약 15~20분 (사이트 서버 부담 방지용 딜레이 포함)
"""
import os
import time

import pandas as pd
from bs4 import BeautifulSoup

from crawler_utils import logger, polite_sleep
from womad_scraper import crawl as crawl_list, get_uc_driver

MAX_POSTS = 300
MAX_COMMENTS = 20
OUTPUT_PATH = "output/워마드.xlsx"

COLUMNS = ["id", "post_id", "type", "text", "author", "date", "url", "views", "recommend", "comment_count"]


def parse_detail(html: str):
    soup = BeautifulSoup(html, "lxml")

    body_div = soup.select_one("div.post-content")
    body_text = body_div.get_text(" ", strip=True) if body_div else ""

    comments = []
    for li in soup.select("li.comment"):
        author_tag = li.select_one("div.writer b")
        author = author_tag.get_text(strip=True) if author_tag else ""

        date_tag = li.select_one("li.created-at")
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        text_tag = li.select_one("div.comment-body p.comment-content")
        text = text_tag.get_text(" ", strip=True) if text_tag else ""

        if text:
            comments.append({"author": author, "date": date_text, "text": text})

    return body_text, comments


def fetch_detail_html(driver, url, expected_comment_count, max_attempts=3):
    """
    댓글이 비동기로 늦게 로딩되는 경우 대비.
    목록 단계에서 알고 있는 댓글 수(expected_comment_count)가 0보다 큰데
    실제로는 못 찾았으면, 대기 시간을 늘려가며 재시도.
    """
    html = ""
    for attempt in range(max_attempts):
        driver.get(url)
        wait_sec = 3 + attempt * 2  # 3초 -> 5초 -> 7초로 점점 늘림
        time.sleep(wait_sec)
        html = driver.page_source

        found = len(BeautifulSoup(html, "lxml").select("li.comment"))
        if found > 0 or not expected_comment_count:
            break
        logger.warning(
            f"댓글 미로딩 감지 (기대 {expected_comment_count}개, 발견 0개) "
            f"- 재시도 {attempt + 1}/{max_attempts}"
        )

    return html


def crawl_details(driver, posts):
    rows = []
    row_id = 1

    for i, post in enumerate(posts, 1):
        post_id = post["post_id"]
        detail_url = post["url"]
        logger.info(f"[워마드 상세 {i}/{len(posts)}] {detail_url}")

        html = fetch_detail_html(driver, detail_url, post["comment_count"])
        body_text, comments = parse_detail(html)

        rows.append({
            "id": row_id, "post_id": post_id, "type": "title",
            "text": post["title"], "author": post["author"], "date": post["date"],
            "url": post["url"], "views": post["views"], "recommend": post["recommend"],
            "comment_count": post["comment_count"],
        })
        row_id += 1

        rows.append({
            "id": row_id, "post_id": post_id, "type": "body",
            "text": body_text, "author": post["author"], "date": post["date"],
            "url": post["url"], "views": "", "recommend": "", "comment_count": "",
        })
        row_id += 1

        for c in comments[:MAX_COMMENTS]:
            rows.append({
                "id": row_id, "post_id": post_id, "type": "comment",
                "text": c["text"], "author": c["author"], "date": c["date"],
                "url": post["url"], "views": "", "recommend": "", "comment_count": "",
            })
            row_id += 1

        polite_sleep()

    return rows


def main():
    logger.info("1단계: 게시글 목록 수집")
    max_pages = (MAX_POSTS // 25) + 1
    posts = crawl_list(max_pages=max_pages)[:MAX_POSTS]
    logger.info(f"목록 수집 완료: {len(posts)}개")

    if not posts:
        logger.error("목록을 하나도 못 가져왔음 - 사이트 차단(Cloudflare)이거나 구조가 바뀌었을 수 있음. 중단.")
        return

    logger.info("2단계: 게시글별 본문/댓글 수집 시작")
    driver = get_uc_driver()
    try:
        rows = crawl_details(driver, posts)
    finally:
        driver.quit()

    os.makedirs("output", exist_ok=True)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(OUTPUT_PATH, index=False)
    logger.info(f"저장 완료: {OUTPUT_PATH} (총 {len(df)}행)")


if __name__ == "__main__":
    main()
