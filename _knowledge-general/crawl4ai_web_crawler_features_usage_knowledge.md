🚀🤖 Crawl4AI: Open-source LLM Friendly Web Crawler & Scraper  
### License  
Apache-2.0 license  

🚀 **Quick Start**  
1. Install Crawl4AI:  
```  
pip install -U crawl4ai  
crawl4ai-setup  
crawl4ai-doctor  
```  

2. Basic web crawl:  
```python  
import asyncio  
from crawl4ai import *  

async def main():  
    async with AsyncWebCrawler() as crawler:  
        result = await crawler.arun(url="https://www.nbcnews.com/business")  
        print(result.markdown)  

if __name__ == "__main__":  
    asyncio.run(main())  
```  

✨ **Key Features**  
1. **AI-Optimized Output**:  
   - Generates clean Markdown with BM25 filtering  
   - Maintains citations and semantic structure  

2. **Advanced Extraction**:  
   - CSS/XPath selectors  
   - LLM-powered schema extraction  
   - Dynamic content handling with JS execution  

3. **Deployment Ready**:  
   - Docker support  
   - Proxy rotation  
   - Memory-adaptive dispatcher  

🔬 **Advanced Usage Examples**  
```python  
# Schema-based extraction  
schema = {  
    "baseSelector": "section.courses",  
    "fields": [  
        {"name": "title", "selector": "h3", "type": "text"},  
        {"name": "description", "selector": ".content", "type": "text"}  
    ]  
}  

# LLM-powered extraction  
from pydantic import BaseModel  
class Course(BaseModel):  
    title: str  
    difficulty: str  

extraction_strategy = LLMExtractionStrategy(  
    provider="openai/gpt-4",  
    schema=Course.schema()  
)  
```  

🔄 **Recent Updates**  
- Memory-adaptive crawling system  
- Real-time streaming support  
- Automatic schema generation  
- robots.txt compliance  
- Proxy rotation management  

📦 **Installation Options**  
```  
# Development setup  
git clone https://github.com/unclecode/crawl4ai.git  
pip install -e ".[all]"  

# Docker deployment  
docker-compose up -d  
```  

📈 **Performance**  
- 6x faster than traditional crawlers  
- 90% reduction in irrelevant content  
- Supports 1000+ concurrent sessions  

🤝 **Contributing**  
- Accepting PRs for:  
  - New extraction strategies  
  - Browser compatibility fixes  
  - Documentation improvements  

🔮 **Roadmap**  
- Graph-based website traversal  
- Natural language query interface  
- Automated data marketplace integration  

📄 **License**  
Apache 2.0 - Free for commercial use