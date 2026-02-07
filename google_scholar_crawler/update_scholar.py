import requests
import json
import os
import logging
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_scholar_data_serpapi(scholar_id, api_key):
    """使用 SerpAPI 获取 Google Scholar 数据并转换为原有格式"""
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "api_key": api_key,
        "hl": "en"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        serpapi_data = response.json()
        
        logger.info(f"SerpAPI response keys: {list(serpapi_data.keys())}")
        
        # 安全地提取数据
        cited_by_table = serpapi_data.get("cited_by", {}).get("table", [])
        logger.info(f"Cited by table length: {len(cited_by_table)}")
        
        # 计算动态的 5 年起始年份键，例如 current_year=2026 -> since_2021 (2026-5)
        now_year = datetime.now().year
        since_key = f"since_{now_year - 5}"
        
        # 转换为原有格式
        author_data = {
            "container_type": "Author",
            "filled": [
                "basics",
                "publications", 
                "indices",
                "counts"
            ],
            "scholar_id": scholar_id,
            "source": "AUTHOR_PROFILE_PAGE",
            "name": serpapi_data.get("author", {}).get("name", ""),
            "url_picture": serpapi_data.get("author", {}).get("thumbnail", ""),
            "affiliation": serpapi_data.get("author", {}).get("affiliations", ""),
            "interests": [interest.get("title", "") for interest in serpapi_data.get("author", {}).get("interests", [])],
            "email_domain": "@my.cityu.edu.hk",  # 从email信息提取
            "homepage": serpapi_data.get("author", {}).get("website", ""),
            "citedby": 0,
            "publications": [],
            "citedby5y": 0,
            "hindex": 0,
            "hindex5y": 0,
            "i10index": 0,
            "i10index5y": 0,
            "cites_per_year": {}
        }
        
        # 安全地提取引用数据 - 修正数据结构
        for item in cited_by_table:
            if "citations" in item:
                citations_data = item["citations"]
                author_data["citedby"] = citations_data.get("all", 0)
                author_data["citedby5y"] = citations_data.get(since_key, 0)
            elif "h_index" in item:
                hindex_data = item["h_index"]
                author_data["hindex"] = hindex_data.get("all", 0)
                author_data["hindex5y"] = hindex_data.get(since_key, 0)
            elif "i10_index" in item:
                i10_data = item["i10_index"]
                author_data["i10index"] = i10_data.get("all", 0)
                author_data["i10index5y"] = i10_data.get(since_key, 0)
        
        # 处理年度引用数据
        yearly_data = serpapi_data.get("cited_by", {}).get("graph", [])
        for year_data in yearly_data:
            year = year_data.get("year")
            citations = year_data.get("citations", 0)
            if year:
                author_data["cites_per_year"][str(year)] = citations
        
        # 处理出版物
        for i, pub in enumerate(serpapi_data.get("articles", [])):
            publication = {
                "container_type": "Publication",
                "source": "AUTHOR_PUBLICATION_ENTRY", 
                "bib": {
                    "title": pub.get("title", ""),
                    "pub_year": str(pub.get("year", "")),
                    "citation": pub.get("publication", "")
                },
                "filled": False,
                "author_pub_id": pub.get("citation_id", f"{scholar_id}:pub{i}"),
                "num_citations": pub.get("cited_by", {}).get("value", 0),
                "citedby_url": pub.get("cited_by", {}).get("link", ""),
                "cites_id": [pub.get("cited_by", {}).get("cites_id", "")]
            }
            author_data["publications"].append(publication)
        
        logger.info(f"Successfully processed data: {author_data['citedby']} citations, {len(author_data['publications'])} publications")
        return author_data
        
    except Exception as e:
        logger.error(f"SerpAPI request failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    try:
        SCHOLAR_ID = "9F_Gj1sAAAAJ"
        SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        
        if not SERPAPI_KEY:
            logger.error("SERPAPI_KEY environment variable not set")
            sys.exit(1)

        logger.info(f"Fetching data for Google Scholar ID: {SCHOLAR_ID} using SerpAPI")

        # 获取作者数据
        author_data = get_scholar_data_serpapi(SCHOLAR_ID, SERPAPI_KEY)
        
        if not author_data:
            raise ValueError("Failed to fetch data from SerpAPI")

        # 保存数据
        os.makedirs("results", exist_ok=True)
        with open("results/gs_data.json", "w", encoding="utf-8") as f:
            json.dump(author_data, f, ensure_ascii=False, indent=2)

        shieldio_data = {
            "schemaVersion": 1,
            "label": "citations",
            "message": f"{author_data.get('citedby', 'N/A')}",
            "color": "9cf",
        }
        with open("results/gs_data_shieldsio.json", "w", encoding="utf-8") as f:
            json.dump(shieldio_data, f, ensure_ascii=False)

        logger.info("Data successfully fetched and saved")
        
        # 打印关键信息用于验证
        logger.info(f"Name: {author_data.get('name')}")
        logger.info(f"Citations: {author_data.get('citedby')}")
        logger.info(f"5-Year Citations: {author_data.get('citedby5y')}")
        logger.info(f"H-index: {author_data.get('hindex')}")
        logger.info(f"i10-index: {author_data.get('i10index')}")
        logger.info(f"Publications: {len(author_data.get('publications', []))}")

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
