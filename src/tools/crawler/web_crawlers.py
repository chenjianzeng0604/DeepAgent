"""
统一科技新闻网站爬虫模块，整合顶级科技和AI新闻网站
"""

import logging
import io
import os
import asyncio
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urlunparse, urljoin
from markdownify import markdownify as md
import aiohttp

import asyncio
import logging
import re
import os
from typing import List, Optional, AsyncGenerator
from urllib.parse import urlparse, urljoin, quote
import aiohttp
import requests
import pdfplumber
import io
from pdfminer.layout import LAParams

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from src.database.vectordb.milvus_dao import milvus_dao
import uuid
from src.prompts.prompt_templates import PromptTemplates
from datetime import datetime, timezone
from src.model.llm_client import llm_client
from playwright.async_api import async_playwright
from src.tools.crawler.cloudflare_bypass import CloudflareBypass
from src.database.vectordb.schema_manager import MilvusSchemaManager
from src.tools.crawler.crawler_config import crawler_config_manager
from src.utils.json_parser import str2Json
from src.utils.text_filter import TextFilter

logger = logging.getLogger(__name__)

class WebCrawler:
    """
    常用网站爬虫，支持主流技术媒体
    """
    
    def __init__(self):
        self.crawler_config_manager = crawler_config_manager
        self.milvus_dao = milvus_dao
        self.proxies = {
            "server": os.getenv("KDL_PROXIES_SERVER", ""),
            "username": os.getenv("KDL_PROXIES_USERNAME", ""),
            "password": os.getenv("KDL_PROXIES_PASSWORD", "")
        }
        self.headers = {
            'User-Agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        self.crawler_extract_pdf_timeout = int(os.getenv("CRAWLER_EXTRACT_PDF_TIMEOUT", 10))
        self.crawler_max_links_result = int(os.getenv("CRAWLER_MAX_LINKS_RESULT", 20))
        self.crawler_fetch_url_timeout = int(os.getenv("CRAWLER_FETCH_URL_TIMEOUT", 20))
        self.crawler_fetch_article_with_semaphore = int(os.getenv("CRAWLER_FETCH_ARTICLE_WITH_SEMAPHORE", 10))
        self.llm_client = llm_client
        self.article_trunc_word_count = int(os.getenv("ARTICLE_TRUNC_WORD_COUNT", 10000))
        self.article_compress_word_count = int(os.getenv("ARTICLE_COMPRESS_WORD_COUNT", 5000))
        
    def is_valid_url(self, url: str, base_domain: Optional[str] = None) -> bool:
        """
        检查URL是否有效且应该被爬取
        
        Args:
            url: 要检查的URL
            base_domain: 可选的基础域名限制
            
        Returns:
            bool: URL是否有效且应该被爬取
        """
        parsed = urlparse(url)
        
        # 基础验证
        if parsed.scheme not in ('http', 'https'):
            return False
            
        # 域名限制
        if base_domain and not parsed.netloc.endswith(base_domain):
            return False
        
        # 排除静态文件（图片、视频、压缩包等）
        static_ext = ('.jpg', '.jpeg', '.png', '.gif', '.css', '.js',
                     '.zip', '.tar', '.gz', '.exe', '.svg', '.ico',
                     '.mp3', '.mp4', '.avi', '.mov', '.flv', '.wmv',
                     '.woff', '.woff2', '.ttf', '.eot', '.otf')
        if any(parsed.path.lower().endswith(ext) for ext in static_ext):
            return False

        # 排除低质量内容链接
        low_value_patterns = [
            # 广告、跟踪和分析
            '/ads/', '/ad/', 'doubleclick', 'analytics', 'tracker', 'click.php',
            'pixel.php', 'counter.php', 'utm_', 'adserv', 'banner', 'sponsor',
            # 用户操作和账户页面
            'redirect', 'share', 'login', 'signup', 'register', 'comment', 
            'subscribe', 'newsletter', 'account', 'profile', 'password',
            "/dictionary/", "/translate/", "/grammar/", "/thesaurus/", 
            # 站点信息页
            'privacy', 'terms', 'about-us', 'contact-us', 'faq', 'help',
            'cookie', 'disclaimer', 'copyright', 'license', 'sitemap',
            "contact", "about", "privacy", "disclaimer",
            # 搜索引擎特定页面
            'www.bing.com/images/search', 'google.com/imgres',
            'search?', 'search/', '/search', 'query=', 'www.google.com/maps/search',
            'www.bing.com/translate', 'www.instagram.com/cambridgewords',
            'dictionary.cambridge.org/plus', 'dictionary.cambridge.org/howto.html',
            'www.google.com/shopping', 'support.google.com/googleshopping',
            'www.bing.com/maps', 'www.bing.com/shop', 'go.microsoft.com/fwlink',
            'bingapp.microsoft.com/bing', 'www.google.com/httpservice/retry/enablejs',
            'www.google.com/travel/flights', 'maps.google.com/maps',
            # 社交媒体分享链接
            'facebook.com/sharer', 'twitter.com/intent', 'linkedin.com/share',
            'plus.google.com', 'pinterest.com/pin', 't.me/share',
            # 打印、RSS和其他功能页面
            'print=', 'print/', 'print.html', 'rss', 'feed', 'atom',
            'pdf=', 'pdf/', 'download=', '/download', 'embed=',
            # 日历、存档和分类页面
            'calendar', '/tag/', '/tags/', '/category/', '/categories/',
            '/archive/', '/archives/', '/author/', '/date/',
            # 购物车、结账和交易页面
            'cart', 'checkout', 'basket', 'payment', 'order', 'transaction',
            # 人工识别链接
            'www.ggzy.gov.cn/information/serve/wechat.jsp'
        ]
        if any(pattern in url.lower() for pattern in low_value_patterns):
            return False

        search_engine_home = [
            # 匹配所有Bing主页变体（含参数）
            r'^https?://(www\.)?bing\.com/?(\?.*)?$',
            r'^http?://(www\.)?bing\.com/?(\?.*)?$',
            # 匹配所有Google主页变体（含参数）
            r'^https?://(www\.)?google\.com/?(\?.*)?$'
            r'^http?://(www\.)?google\.com/?(\?.*)?$'
        ]
        for pattern in search_engine_home:
            if re.match(pattern, url, re.I):
                return False
            
        return True
    
    def normalize_url(self, url: str) -> str:
        """
        标准化URL：去除查询参数、锚点和末尾斜杠
        
        Args:
            url: 要标准化的URL
            
        Returns:
            str: 标准化后的URL
        """
        parsed = urlparse(url)
        parsed = parsed._replace(
            query='',
            fragment='',
            path=parsed.path.rstrip('/')
        )
        return urlunparse(parsed)
    
    async def extract_pdf(self, url: str) -> str:
        """
        提取PDF文档内容
        
        Args:
            url: PDF文档URL
            
        Returns:
            Dict[str, Any]: 提取的内容
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=self.crawler_extract_pdf_timeout) as response:
                    if response.status == 200:
                        pdf_content = await response.read()
                        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                            text_content = []
                            laparams = LAParams(
                                detect_vertical=True,  # 检测垂直文本
                                all_texts=True,        # 提取所有文本层
                                line_overlap=0.5,      # 行重叠阈值
                                char_margin=2.0        # 字符间距阈值
                            )
                            for page in pdf.pages:
                                page_text = page.extract_text(laparams=laparams)
                                if page_text:
                                    text_content.append(
                                        page_text.replace('\ufffd', '?')  # 替换非法字符
                                    )
                            if text_content:
                                final_text = '\n\n'.join(text_content)
                                is_filter = self._rule_based_filter(url, final_text)
                                if (is_filter):
                                    logger.info(f"命中低质量规则校验，过滤掉 {url} 的内容")
                                    return None
                                return final_text
        except Exception as e:
            logger.error(f"提取PDF内容出错: {url}, 错误: {str(e)}")
        return None
    
    async def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        从HTML中提取链接
        
        Args:
            html: HTML内容
            base_url: 基础URL
            
        Returns:
            List[str]: 提取的链接列表
        """
        links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_url = urljoin(base_url, href)
                if self.is_valid_url(absolute_url):
                    if absolute_url in links:
                        continue
                    links.append(absolute_url)
        except Exception as e:
            logger.error(f"提取链接出错: {base_url}, 错误: {str(e)}")
        return links

    async def parse_sub_url(self, search_url: str) -> List[str]:
        try:
            html_content = await self.fetch_url_with_proxy_fallback(search_url)
            if not html_content:
                logger.error(f"主URL获取内容为空: {search_url}")
                return []
            return await self.extract_links(html_content, search_url)
        except Exception as e:
            logger.error(f"parse_sub_url出错: {search_url}, 错误: {str(e)}")
            return []

    async def filterSavedUrl(self, links, scenario: str = None):
        # 获取场景对应的Milvus集合名称
        collection_name = self.crawler_config_manager.get_collection_name(scenario)
        if not collection_name:
            logger.warning(f"未找到场景 {scenario} 对应的Milvus集合名称")
            return []
            
        logger.info(f"过滤已存在URL，场景: {scenario}, 集合: {collection_name}")
        
        # 将链接按批次处理，避免查询字符串过长
        batch_size = 50
        unique_links = list(set(links))  # 去重
        all_existing_urls = set()
        
        for i in range(0, len(unique_links), batch_size):
            batch_links = unique_links[i:i+batch_size]
            url_list_str = ", ".join([f"'{url}'" for url in batch_links])
            filter_expr = f"url in [{url_list_str}]"
            
            try:
                res = self.milvus_dao.query(
                    collection_name=collection_name,
                    filter=filter_expr,
                    output_fields=["url"],
                )
                if res:
                    batch_existing_urls = set(r["url"] for r in res) if res else set()
                    all_existing_urls.update(batch_existing_urls)
            except Exception as e:
                logger.error(f"查询Milvus中的已存在URL失败: {str(e)}")
                # 继续执行，不阻断进程

        links_to_fetch = [link for link in unique_links if link not in all_existing_urls]
        if not links_to_fetch:
            logger.info(f"所有链接 ({len(unique_links)}) 已存在于数据库中，无需重新处理")
            return []
            
        logger.info(f"将处理{len(links_to_fetch)}/{len(unique_links)} 个链接 (过滤掉 {len(all_existing_urls)} 个已存在链接)")
        return links_to_fetch

    async def fetch_article_stream(self, links: List[str], query: str = None) -> AsyncGenerator[dict, None]:
        """
        流式获取文章内容并保存到Milvus
        
        Args:
            links: 链接列表
        
        Yields:
            dict: 包含url/content/error的字典对象
        """
        if not links:
            logger.warning("没有有效链接可爬取")
            return
        sem = asyncio.Semaphore(self.crawler_fetch_article_with_semaphore)
        async def process_link(link: str) -> dict:
            """处理单个链接的异步任务"""
            try:
                async with sem:
                    if self.is_pdf_url(link):
                        content = await self.extract_pdf(link)
                    else:
                        content = await self.fetch_url_md(link)
                    clean_content = content.strip() if content else ""
                    if not clean_content:
                        return {
                            "url": link, 
                            "content": "", 
                            "title": "", 
                            "high_quality": False, 
                            "reason": "内容未获取到或已被过滤", 
                            "compress": False
                        }
                    prompt = PromptTemplates.format_article_quality_prompt(
                        article=clean_content, 
                        query=query,
                        word_count=self.article_trunc_word_count)
                    response = await self.llm_client.generate(
                        prompt=prompt, 
                        model=os.getenv("ARTICLE_QUALITY_MODEL")
                    )
                    quality_result = str2Json(response)
                    if not quality_result:
                        return {
                            "url": link, 
                            "content": "", 
                            "title": "", 
                            "high_quality": False, 
                            "reason": "内容质量评估失败", 
                            "compress": False
                        }
                    if not quality_result.get("high_quality", False):
                        return {
                            "url": link, 
                            "content": "", 
                            "title": "", 
                            "high_quality": False, 
                            "reason": quality_result.get("reason"), 
                            "compress": False
                        }
                    if quality_result.get("compress"): 
                        content = quality_result.get("compressed_article")
                    result = {
                        "url": link, 
                        "content": content, 
                        "title": quality_result.get("title"), 
                        "high_quality": True, 
                        "reason": quality_result.get("reason"), 
                        "compress": quality_result.get("compress"),
                    }
                    asyncio.create_task(self.save_article([result], quality_result["scenario"]))
                    return result
            except asyncio.CancelledError:
                logger.warning(f"任务取消: {link}", exc_info=True)
                return {"url": link, "error": "任务取消"}
            except Exception as e:
                logger.error(f"处理失败: {link} - {str(e)}", exc_info=True)
                return {"url": link, "error": str(e)}
        max_links = min(self.crawler_max_links_result, len(links))
        tasks = [
            asyncio.create_task(process_link(link))
            for link in links[:max_links]
        ]
        try:
            for future in asyncio.as_completed(tasks):
                try:
                    result = await future
                    yield result
                except Exception as e:
                    logger.error(f"任务异常: {str(e)}")
                    yield {"error": str(e)}
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

    async def save_article(self, results, scenario: str = None):
        batch_size = 5
        current_batch = []
        rows = 0
        collection_name = self.crawler_config_manager.get_collection_name(scenario)
        if not collection_name:
            logger.warning(f"未找到场景 {scenario} 对应的Milvus集合名称")
            return
        links = [r["url"] for r in results if r and "url" in r]
        links_to_save = await self.filterSavedUrl(links, scenario)
        if not links_to_save:
            logger.warning(f"没有需要保存的文章，场景：{scenario}")
            return
        results = [r for r in results if r["url"] in links_to_save]
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"获取文章信息时发生错误: {str(result)}")
                continue
            if not result or 'url' not in result:
                logger.warning(f"获取的结果格式不正确: {result}")
                continue
            if 'error' in result and result['error']:
                logger.warning(f"获取文章 {result['url']} 失败: {result['error']}")
                continue
            if not result['content'] or len(result['content'].strip()) == 0:
                logger.warning(f"获取的文章内容为空: {result['url']}")
                continue
            try:
                schema, index_params = MilvusSchemaManager.get_deepresearch_schema()
                contents = self.cut_string_by_length(result['content'], self.article_trunc_word_count)
                for content in contents:
                    if not content or len(content.strip()) == 0:
                        continue
                    try:
                        content_embs = self.milvus_dao.generate_embeddings([content])
                        if not content_embs or len(content_embs) == 0:
                            logger.warning(f"为内容生成嵌入向量失败: {result['url']}")
                            continue
                        data_item = {
                            "id": str(uuid.uuid4()),
                            "url": result['url'],
                            "title": result['title'],
                            "content": content,
                            "content_emb": content_embs[0],
                            "create_time": int(datetime.now(timezone.utc).timestamp() * 1000)
                        }
                        current_batch.append(data_item)
                        if len(current_batch) >= batch_size:
                            try:
                                success = await self.batch_save_to_milvus(
                                    collection_name=collection_name, 
                                    schema=schema, 
                                    index_params=index_params, 
                                    data=current_batch
                                )
                                if success:
                                    rows += len(current_batch)
                                await asyncio.sleep(1)
                            except Exception as e:
                                logger.error(f"写入Milvus失败: {str(e)}")
                            current_batch = []
                    except Exception as e:
                        logger.error(f"处理内容块时出错: {str(e)}")
            except Exception as e:
                logger.error(f"处理文章时出错: {result['url']}, {str(e)}")
        
        if current_batch:
            success = await self.batch_save_to_milvus(
                collection_name=collection_name, 
                schema=schema, 
                index_params=index_params, 
                data=current_batch
            )
            if success:
                rows += len(current_batch)
            await asyncio.sleep(1)
    
        logger.info(f"成功写入{rows}行数据到集合 {collection_name}")

    async def batch_save_to_milvus(self, collection_name, schema, index_params, data):
        try:
            success = self.milvus_dao.store(
                collection_name=collection_name, 
                schema=schema, 
                index_params=index_params, 
                data=data
            )
            if not success:
                logger.warning(f"Milvus数据存储失败，批次大小：{len(data)}")
            return success
        except Exception as e:
            logger.error(f"批量写入Milvus失败: {str(e)}")
            return False
    
    def cut_string_by_length(self, s, length):
        """
        将字符串按固定长度切割成数组

        :param s: 需要切割的字符串
        :param length: 每个子字符串的固定长度
        :return: 切割后的子字符串数组
        """
        return [s[i:i+length] for i in range(0, len(s), length)]
    
    def is_pdf_url(self, url: str) -> bool:
        return '/pdf/' in url or url.endswith('.pdf')
    
    async def fetch_url_md(self, url: str) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 要获取的URL
            
        Returns:
            Optional[str]: Markdown内容
        """
        return self.html2md(await self.fetch_url_with_proxy_fallback(url))

    async def fetch_url_with_proxy_fallback(self, url: str) -> Optional[str]:
        """
        尝试获取URL内容，如果不使用代理失败，则尝试使用代理
        
        Args:
            url: 要获取的URL
            
        Returns:
            Optional[str]: 页面内容或None（如果获取失败）
        """
        # 验证URL格式
        if not url or not isinstance(url, str):
            logger.error(f"无效URL: {url}")
            return None
            
        # 确保URL有正确的协议前缀
        if not url.startswith(('http://', 'https://')):
            logger.error(f"URL缺少协议前缀: {url}")
            return None
            
        try:
            return await self._fetch_url_implementation(url, useProxy=False)    
        except Exception as e:
            logger.error(f"不使用代理获取URL失败 {url}: {str(e)}")
            try:
                return await self._fetch_url_implementation(url, useProxy=True)    
            except Exception as e:
                logger.error(f"使用代理获取URL失败 {url}: {str(e)}")
                return None
    
    async def _fetch_url_implementation(self, url: str, useProxy: bool = False) -> Optional[str]:
        try:
            async with async_playwright() as p:
                if useProxy:
                    logger.info(f"Fetching URL {url} with proxy")
                    browser = await p.chromium.launch(
                        headless=True,
                        proxy=self.proxies,
                        args=[
                        "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-web-security",
                            "--disable-features=IsolateOrigins,site-per-process",
                            f"--user-agent={UserAgent().random}",
                            "--use-fake-ui-for-media-stream",
                            "--use-fake-device-for-media-stream",
                            "--disable-gpu",
                            "--disable-dev-shm-usage",
                            "--disable-software-rasterizer"
                        ],
                        env={"SSLKEYLOGFILE": "/dev/null"}
                    )
                else:
                    logger.info(f"Fetching URL {url} without proxy")
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-web-security",
                            "--disable-features=IsolateOrigins,site-per-process",
                            f"--user-agent={UserAgent().random}",
                            "--use-fake-ui-for-media-stream",
                            "--use-fake-device-for-media-stream",
                            "--disable-gpu",
                            "--disable-dev-shm-usage",
                            "--disable-software-rasterizer"
                        ],
                        env={"SSLKEYLOGFILE": "/dev/null"}
                    )

                context = await browser.new_context(
                    user_agent=UserAgent().random,
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US,en;q=0.9",
                    timezone_id="America/New_York",
                    permissions=["geolocation"],
                    geolocation={"latitude": 40.7128, "longitude": -74.0060},
                    color_scheme="dark"
                )

                try:
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                        window.generateMouseMove = () => {
                            const path = Array.from({length: 20}, () => ({
                                x: Math.random() * window.innerWidth,
                                y: Math.random() * window.innerHeight,
                                duration: Math.random() * 300 + 200
                            }))
                            path.forEach(p => {
                                window.dispatchEvent(new MouseEvent('mousemove', p))
                            })
                        }
                    """)

                    page = await context.new_page()

                    await page.route("**/*", lambda route: route.abort() 
                        if route.request.resource_type in {"image", "media", "stylesheet", "font"}
                        else route.continue_()
                    )

                    await page.goto(
                        url, 
                        wait_until="domcontentloaded", 
                        timeout=self.crawler_fetch_url_timeout * 1000
                    )

                    cloudflare_bypass = CloudflareBypass(page)
                    try:
                        # 先尝试模拟人类交互
                        await cloudflare_bypass.simulate_human_interaction()
                        # 然后处理Cloudflare挑战
                        html = await cloudflare_bypass.handle_cloudflare()
                    except Exception as e:
                        logger.warning(f"Cloudflare绕过过程中出错: {str(e)}")
                        # 即使出错也尝试获取页面内容
                        try:
                            html = await page.inner_html("body")
                        except Exception as content_error:
                            logger.error(f"获取页面内容失败: {str(content_error)}")
                            html = None
                    if html:
                        text = await page.inner_text("body")
                        is_filter = self._rule_based_filter(url, text)
                        if is_filter:
                            logger.info(f"命中低质量规则校验，过滤掉 {url} 的内容")
                            return None
                        else:
                            return html
                    else:
                        return None
                finally:
                    try:
                        await context.close()
                    except Exception as context_error:
                        logger.warning(f"关闭浏览器上下文失败: {str(context_error)}")
                    try:
                        await browser.close()
                    except Exception as browser_error:
                        logger.warning(f"关闭浏览器失败: {str(browser_error)}")
        except Exception as e:
            logger.error(f"获取页面内容失败: {str(e)}")
            return None

    def get_domain(self, url: str) -> str:
        """
        获取URL的域名
        
        Args:
            url: 网址
            
        Returns:
            str: 域名
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logger.error(f"解析域名出错 {url}: {e}")
            return ""

    def html2md(self, html: str) -> str:
        """
        将HTML内容转换为Markdown
        
        Args:
            html: HTML内容字符串
        Returns:
            str: 转换后的Markdown内容
        """
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        strip_tags = [
            "script", "style", "nav",
            {"tag": "div", "attrs": {"class": "footer"}},
            {"tag": "div", "attrs": {"id": "footer"}},
            {"tag": "div", "attrs": {"class": "header"}},
            {"tag": "div", "attrs": {"id": "header"}},
            "header", "footer", "aside",
            "iframe", "form", "button", "input",
            "svg", "meta", "link",
            {"tag": "div", "attrs": {"class": "copyright"}},
            {"tag": "div", "attrs": {"id": "copyright"}},
            {"tag": "div", "attrs": {"class": "version-info"}},
            {"tag": "div", "attrs": {"id": "version-info"}},
        ]
        for item in strip_tags:
            if isinstance(item, str):
                for tag in soup(item):
                    tag.decompose()
            elif isinstance(item, dict) and "tag" in item:
                tag_name = item["tag"]
                attrs = item.get("attrs", {})
                for tag in soup.find_all(tag_name, attrs=attrs):
                    tag.decompose()
        convert_rules = [
            ("div", lambda tag, _: tag.text + "\n\n"),
            ("span", lambda tag, _: tag.text),
            ("strong", lambda tag, _: "**" + tag.text + "**"),
            ("em", lambda tag, _: "*" + tag.text + "*"),
            ("p", lambda tag, _: tag.text + "\n\n"),
            ("h1", lambda tag, _: "# " + tag.text + "\n\n"),
            ("h2", lambda tag, _: "## " + tag.text + "\n\n"),
            ("h3", lambda tag, _: "### " + tag.text + "\n\n"),
            ("h4", lambda tag, _: "#### " + tag.text + "\n\n"),
            ("h5", lambda tag, _: "##### " + tag.text + "\n\n"),
            ("h6", lambda tag, _: "###### " + tag.text + "\n\n"),
            ("li", lambda tag, _: "- " + tag.text + "\n"),
            ("ul", lambda tag, _: "\n" + tag.text + "\n"),
            ("ol", lambda tag, _: "\n" + tag.text + "\n"),
            ("blockquote", lambda tag, _: "> " + tag.text.replace("\n", "\n> ") + "\n\n"),
            ("pre", lambda tag, _: "```\n" + tag.text + "\n```\n"),
            ("code", lambda tag, _: "`" + tag.text + "`"),
            ("a", lambda tag, _: f"[{tag.text}]({tag.get('href', '')})"),
            ("img", lambda tag, _: f"![{tag.get('alt', '')}]({tag.get('src', '')})")
        ]
        markdown_content = md(
            str(soup), 
            convert=convert_rules,
            heading_style=None,
            strong_em_symbol='',
            bullets='',
            wrap_text=False    
        )
        if markdown_content:
            markdown_content = TextFilter.filter_useless(markdown_content)
        return markdown_content

    def _rule_based_filter(self, url, text):
        """基础规则过滤，检测明显的低质量内容"""
        if not text:
            return True
        # 文本过短
        if len(text) < 150:
            logger.info(f"{url} 文本过短，过滤")
            return True
            
        # 检测乱码（非中文/英文/数字/常用标点符号占比过高）
        non_valid_chars = re.findall(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、,\.!?]', text)
        if len(non_valid_chars) / max(len(text), 1) > 0.3:  # 非有效字符超过30%
            logger.info(f"{url} 检测到乱码，过滤")
            return True
            
        # 重复内容检测
        words = text.split()
        if len(words) > 20 and len(set(words)) / max(len(words), 1) < 0.1:  # 词汇多样性过低
            logger.info(f"{url} 检测到重复内容，过滤")
            return True
            
        # 检测垃圾内容标志
        keywords = [
            'click here', 'buy now', 'limited offer', 'free download',
            'make money', 'earn cash', '点击这里', '立即购买', '限时优惠',
            "免费领取", "限时优惠", "点击下载", "立即注册", 
            "v信", "加微", "低价出售", "【广告】", "completed our registration form"
        ]
        lower_text = text.lower()
        if any(keyword in lower_text for keyword in keywords):
            logger.info(f"{url} 检测到垃圾内容，过滤")
            return True

        # 检测反爬验证页面
        captcha_patterns = [
            "detected unusual traffic",
            "systems have detected unusual",
            "IP address:",
            "This page checks",
            "see if it's really you",
            "not a robot",
            "Why did this happen",
            "Loading...The system can't perform the operation now.",
            "Try again later.",
            "Our systems have detected unusual traffic from your computer network."
        ]
        text_lower = text.lower()
        for pattern in captcha_patterns:
            if pattern in text or pattern.lower() in text_lower:
                logger.info(f"{url}检测到反爬验证页面，过滤")
                return True
        return False

web_crawler = WebCrawler()