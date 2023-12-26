import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

@st.cache
def get_verses(query):
    url = f"https://www.biblegateway.com/quicksearch/?search={query}&resultspp=5000&version=KLB"
    with requests.Session() as session:
        response = session.get(url)
        soup = BeautifulSoup(response.content, "lxml")
        verses = soup.select("div.bible-item-text.col-sm-9")
        titles = soup.select("div.bible-item-title-wrap.col-sm-3")
    try:    
        total = soup.select_one("#serp-bible-pane > div > div:nth-child(1) > div.content-section > div.search-tools > div.results-info > span.showing-results").text.replace('“', '').replace('”','')
        df = pd.DataFrame({"Title": [title.get_text() for title in titles], "Verse": [verse.get_text().strip() for verse in verses]})
        df["Verse"] = df["Verse"].apply(lambda x: re.sub(r"In Context\n \| Full Chapter", "", x))
        return df, total
    except:
        st.warning('검색어 없음')
        return None, None

def main():
    st.title("Bible Verse Search")

    query = st.text_input("Enter the search query:")
    df, total = get_verses(query)
    if df is not None:
        st.write(f"Total results: {total}")

        # Display results with reduced font size
        for index, row in df.iterrows():
            st.markdown(f"**{row['Title']}**\n{row['Verse']}", unsafe_allow_html=True)

        # Export to csv button
        # if st.button("Export to csv"):
            # Use a unique key for caching to ensure consistent behavior
        csv_data = df.to_csv().encode('utf-8-sig')
        st.download_button(
            label="Download csv",
            data=csv_data,
            file_name=f"{total}.csv",
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
