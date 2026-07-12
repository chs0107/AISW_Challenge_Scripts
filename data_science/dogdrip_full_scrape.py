"""
개드립 최종 크롤러
1) 목록 수집 (dogdrip_scraper.crawl 재사용, 페이지 구간 지정 가능)
2) 게시글별 상세 페이지 방문 -> 본문 + 댓글(cpage=1, 오래된 순 상위 20개) 수집
3) 엑셀로 저장 (output/개드립_p{시작}-{끝}.xlsx)

컬럼: id, post_id, type(title/body/comment), text, author, date, url, views, recommend, comment_count
- views/recommend/comment_count는 type='title' 행에만 값이 채워짐

사용법:
  python dogdrip_full_scrape.py            -> 기본 범위(1~15페이지, 약 300개) 전체 수집
  python dogdrip_full_scrape.py 1 9        -> 1~9페이지만 수집 -> output/개드립_p1-9.xlsx
  python dogdrip_full_scrape.py 10 19      -> 10~19페이지만 수집 -> output/개드립_p10-19.xlsx
  python dogdrip_full_scrape.py 20 29      -> 20~29페이지만 수집 -> output/개드립_p20-29.xlsx

한 번에 끊기지 않고 다 되면 인자 없이 실행해도 되고,
중간에 계속 막히면 위처럼 구간을 나눠 여러 번 실행한 뒤 merge_excels.py로 합치면 됨.
"""
import sys

from bs4 import BeautifulSoup

from crawler_utils import logger, polite_sleep, save_rows_to_excel
from selenium_utils import get_uc_driver, fetch_rendered_html
from dogdrip_scraper import crawl as crawl_list

MAX_COMMENTS = 20
CHECKPOINT_EVERY = 20  # 이 개수마다 중간 저장

COLUMNS = ["id", "post_id", "type", "text", "author", "date", "url", "views", "recommend", "comment_count"]


def parse_detail(html: str):
    soup = BeautifulSoup(html, "lxml")

    # 본문: class가 'document_'로 시작하는 div (예: document_712212350_0 rhymix_content xe_content)
    body_div = soup.find("div", class_=lambda c: c and any(cls.startswith("document_") for cls in c))
    body_text = body_div.get_text(" ", strip=True) if body_div else ""

    comments = []
    for item in soup.select("div.comment-item"):
        author_tag = item.select_one("h6.text-normal a")
        author = author_tag.get_text(strip=True) if author_tag else ""

        date_tag = item.select_one("div.comment-bar span.text-muted")
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        text_div = item.select_one("div[class*='rhymix_content']")
        text = text_div.get_text(" ", strip=True) if text_div else ""

        if text:
            comments.append({"author": author, "date": date_text, "text": text})

    return body_text, comments


def crawl_details(driver, posts, output_path):
    rows = []
    row_id = 1

    try:
        for i, post in enumerate(posts, 1):
            document_srl = post["document_srl"]
            detail_url = f"https://www.dogdrip.net/dogdrip/{document_srl}?cpage=1#comment"
            logger.info(f"[개드립 상세 {i}/{len(posts)}] {detail_url}")

            try:
                html = fetch_rendered_html(driver, detail_url, wait_sec=2.5)
                body_text, comments = parse_detail(html)
            except Exception as e:
                logger.warning(f"{i}번째 게시글 처리 중 오류, 건너뜀: {e}")
                continue

            rows.append({
                "id": row_id, "post_id": document_srl, "type": "title",
                "text": post["title"], "author": post["author"], "date": post["date"],
                "url": post["url"], "views": "", "recommend": post["recommend"],
                "comment_count": post["comment_count"],
            })
            row_id += 1

            rows.append({
                "id": row_id, "post_id": document_srl, "type": "body",
                "text": body_text, "author": post["author"], "date": post["date"],
                "url": post["url"], "views": "", "recommend": "", "comment_count": "",
            })
            row_id += 1

            for c in comments[:MAX_COMMENTS]:
                rows.append({
                    "id": row_id, "post_id": document_srl, "type": "comment",
                    "text": c["text"], "author": c["author"], "date": c["date"],
                    "url": post["url"], "views": "", "recommend": "", "comment_count": "",
                })
                row_id += 1

            polite_sleep()

            if i % CHECKPOINT_EVERY == 0:
                save_rows_to_excel(rows, COLUMNS, output_path)
                logger.info(f"중간 저장 완료 ({i}/{len(posts)}개 게시글 처리)")

    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단됨 (Ctrl+C). 지금까지 수집된 데이터는 저장함.")

    return rows


def main():
    # 명령줄 인자로 시작/끝 페이지 지정 가능. 없으면 기본값(1~15페이지, 약 300개) 사용
    if len(sys.argv) >= 3:
        start_page = int(sys.argv[1])
        end_page = int(sys.argv[2])
    else:
        start_page, end_page = 1, 15

    output_path = f"output/개드립_p{start_page}-{end_page}.xlsx"

    logger.info(f"1단계: 게시글 목록 수집 ({start_page}~{end_page}페이지)")
    posts = crawl_list(start_page=start_page, end_page=end_page)
    logger.info(f"목록 수집 완료: {len(posts)}개")

    if not posts:
        logger.error("목록을 하나도 못 가져왔음 - 사이트 차단이거나 구조가 바뀌었을 수 있음. 중단.")
        return

    logger.info("2단계: 게시글별 본문/댓글 수집 시작")
    driver = get_uc_driver(headless=False)
    rows = []
    try:
        rows = crawl_details(driver, posts, output_path)
    finally:
        driver.quit()
        if rows:
            save_rows_to_excel(rows, COLUMNS, output_path)
            logger.info(f"최종 저장 완료: {output_path} (총 {len(rows)}행)")
        else:
            logger.warning("저장할 데이터가 없음")


if __name__ == "__main__":
    main()
