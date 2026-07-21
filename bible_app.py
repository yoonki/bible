import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# ------------------------------------------------------------------
# 1) 한글 성경 책 이름 -> 영어 성경 책 이름 매핑
#    BibleGateway에서 NIV 구절을 찾으려면 영어 책 이름이 필요하기 때문입니다.
#    (예: "요한복음 3:16" -> "John 3:16")
# ------------------------------------------------------------------
KO_TO_EN_BOOK = {
    "창세기": "Genesis", "출애굽기": "Exodus", "레위기": "Leviticus",
    "민수기": "Numbers", "신명기": "Deuteronomy", "여호수아": "Joshua",
    "사사기": "Judges", "룻기": "Ruth", "사무엘상": "1 Samuel",
    "사무엘하": "2 Samuel", "열왕기상": "1 Kings", "열왕기하": "2 Kings",
    "역대상": "1 Chronicles", "역대하": "2 Chronicles", "에스라": "Ezra",
    "느헤미야": "Nehemiah", "에스더": "Esther", "욥기": "Job",
    "시편": "Psalm", "잠언": "Proverbs", "전도서": "Ecclesiastes",
    "아가": "Song of Solomon", "이사야": "Isaiah", "예레미야": "Jeremiah",
    "예레미야애가": "Lamentations", "에스겔": "Ezekiel", "다니엘": "Daniel",
    "호세아": "Hosea", "요엘": "Joel", "아모스": "Amos",
    "오바댜": "Obadiah", "요나": "Jonah", "미가": "Micah",
    "나훔": "Nahum", "하박국": "Habakkuk", "스바냐": "Zephaniah",
    "학개": "Haggai", "스가랴": "Zechariah", "말라기": "Malachi",
    "마태복음": "Matthew", "마가복음": "Mark", "누가복음": "Luke",
    "요한복음": "John", "사도행전": "Acts", "로마서": "Romans",
    "고린도전서": "1 Corinthians", "고린도후서": "2 Corinthians",
    "갈라디아서": "Galatians", "에베소서": "Ephesians",
    "빌립보서": "Philippians", "골로새서": "Colossians",
    "데살로니가전서": "1 Thessalonians", "데살로니가후서": "2 Thessalonians",
    "디모데전서": "1 Timothy", "디모데후서": "2 Timothy", "디도서": "Titus",
    "빌레몬서": "Philemon", "히브리서": "Hebrews", "야고보서": "James",
    "베드로전서": "1 Peter", "베드로후서": "2 Peter",
    "요한일서": "1 John", "요한이서": "2 John", "요한삼서": "3 John",
    "유다서": "Jude", "요한계시록": "Revelation",
}


def korean_title_to_english_ref(title: str):
    """'요한복음 3:16' 같은 한글 제목을 'John 3:16' 형태의 영어 참조로 바꿔줍니다.
    매핑에 없는 책 이름이 나오면 None을 돌려줍니다."""
    title = title.strip()
    parts = title.split(" ", 1)
    if len(parts) != 2:
        return None
    ko_book, chapter_verse = parts
    en_book = KO_TO_EN_BOOK.get(ko_book)
    if not en_book:
        return None
    return f"{en_book} {chapter_verse}"


# ------------------------------------------------------------------
# 2) 특정 참조(예: "John 3:16")의 NIV 본문을 BibleGateway에서 가져오기
#    같은 참조는 반복 요청하지 않도록 캐시(cache_data)를 사용합니다.
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_niv_text(reference: str):
    url = "https://www.biblegateway.com/passage/"
    params = {"search": reference, "version": "NIV"}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StreamlitBibleApp/1.0)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.content, "lxml")
    passage_div = soup.find("div", class_="passage-text")
    if not passage_div:
        return None

    # 각주, 상호참조, 다른 번역본 표시, 소제목, 링크 등 본문이 아닌 요소는 제거
    for unwanted in passage_div.find_all(["div", "h4"], class_=["footnotes", "crossrefs", "passage-other-trans"]):
        unwanted.decompose()
    for header in passage_div.find_all("h3"):
        header.decompose()
    for a_tag in passage_div.find_all("a"):
        a_tag.decompose()
    for sup in passage_div.find_all("sup", class_=["footnote", "crossreference", "versenum"]):
        sup.decompose()

    verses = []
    for p in passage_div.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            verses.append(text)
    for poetry_div in passage_div.find_all("div", class_="poetry"):
        for line in poetry_div.find_all("p", class_="line"):
            text = line.get_text(" ", strip=True)
            if text:
                verses.append(text)

    result = " ".join(verses).strip()
    return result if result else None


def get_verses(query):
    url = f"https://www.biblegateway.com/quicksearch/?search={query}&resultspp=5000&version=KLB"
    with requests.Session() as session:
        response = session.get(url)
        soup = BeautifulSoup(response.content, "lxml")
        verses = soup.select("div.bible-item-text.col-sm-9")
        titles = soup.select("div.bible-item-title-wrap.col-sm-3")
    try:
        total = soup.select_one(
            "#serp-bible-pane > div > div:nth-child(1) > div.content-section > div.search-tools > div.results-info > span.showing-results"
        ).text.replace('“', '').replace('”', '')
        df = pd.DataFrame({
            "Title": [title.get_text() for title in titles],
            "Verse": [verse.get_text().strip() for verse in verses],
        })
        df["Verse"] = df["Verse"].apply(lambda x: re.sub(r"In Context\n \| Full Chapter", "", x))
        return df, total
    except Exception:
        return None, None


def main():
    st.title("Bible Verse Search in KLB")
    query = st.text_input(
        "한글로 성경에 나오는 단어를 입력해주세요. 예) 어린양은 어린 + 양 조합이기 때문에 어린 양 중간에 띄어쓰기를 해야함",
        value="사랑",
    )

    show_niv = st.checkbox("NIV(영어) 병행 보기 (검색된 구절 전체)", value=True)

    df, total = get_verses(query)
    if df is not None:
        st.write(f"Total results: {total}")
        if show_niv and len(df) > 50:
            st.caption(
                f"※ 검색된 {len(df)}개 구절 전체에 대해 NIV를 하나씩 가져옵니다. "
                "구절이 많으면 시간이 꽤 걸릴 수 있습니다."
            )

        # 전체 구절에 대해 NIV를 가져올 때 진행 상황을 보여주는 progress bar
        progress_bar = st.progress(0) if show_niv and len(df) > 0 else None

        for index, row in df.iterrows():
            st.markdown(
                f"<span style='color: blue;'>**{row['Title']}**</span>\n\n{row['Verse']}",
                unsafe_allow_html=True,
            )

            if show_niv:
                en_ref = korean_title_to_english_ref(row["Title"])
                if en_ref is None:
                    st.caption("NIV: 책 이름을 인식하지 못했습니다.")
                else:
                    niv_text = fetch_niv_text(en_ref)
                    if niv_text:
                        st.markdown(
                            f"<span style='color: green;'>**NIV ({en_ref})**</span>\n\n{niv_text}",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption(f"NIV 본문을 가져오지 못했습니다. ({en_ref})")

                if progress_bar is not None:
                    progress_bar.progress((index + 1) / len(df))

        if progress_bar is not None:
            progress_bar.empty()

        csv_data = df.to_csv().encode('utf-8-sig')
        st.download_button(
            label="Download csv",
            data=csv_data,
            file_name=f"{total}.csv",
            mime='text/csv',
        )
    else:
        st.write('검색결과없음')


if __name__ == "__main__":
    main()
