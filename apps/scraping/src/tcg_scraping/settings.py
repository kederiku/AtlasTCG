import os

from tcg_persistence.configuration import database_url as configured_database_url

BOT_NAME = "tcg_scraping"
SPIDER_MODULES = ["tcg_scraping.sources"]
NEWSPIDER_MODULE = "tcg_scraping.sources"
ROBOTSTXT_OBEY = True
USER_AGENT = os.getenv("TCG_USER_AGENT", "TCGCatalog/0.1")
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 45
DOWNLOAD_MAXSIZE = 25 * 1024 * 1024
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
RETRY_TIMES = 3
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_MAX_CONTEXTS = 2
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4
ITEM_PIPELINES = {
    "tcg_scraping.pipelines.validation.ValidationPipeline": 100,
    "tcg_scraping.pipelines.media.WebPImagesPipeline": 200,
    "tcg_scraping.pipelines.persistence.DatabasePipeline": 300,
}
FILES_STORE = os.getenv("TCG_IMAGES_DIR", "data/images")
FILES_EXPIRES = 30
DATABASE_URL = configured_database_url()
FEED_EXPORT_ENCODING = "utf-8"

TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False

DOWNLOADER_MIDDLEWARES = {"tcg_scraping.middleware.SkipExistingCardsMiddleware": 50}

REQUEST_FINGERPRINTER_CLASS = "tcg_scraping.fingerprints.ImageRequestFingerprinter"

EXTENSIONS = {"tcg_scraping.extensions.stats.AdminStats": 500}
