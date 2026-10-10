"""Curated catalog of crypto news and signal feeds.

Every URL in this catalog was verified to return a parseable RSS/Atom/JSON
feed and to have published content recently (within the freshness window used
by the feed worker). Feeds are grouped by intent: crypto media, news
aggregators, macro/regulation, on-chain/analytics research, exchange/company/
protocol blogs, and mainstream finance/tech.

Each entry is a ``(title, feed_url, credibility)`` tuple where ``credibility``
is a 0.0-1.0 prior used by the signal and corroboration logic.
"""

POLL_INTERVAL_SECONDS = 300

DEFAULT_FEEDS: list[tuple[str, str, float]] = [
    # ---- crypto media ----
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", 0.75),
    ("Unchained", "https://unchainedcrypto.com/feed/", 0.72),
    ("Decrypt", "https://decrypt.co/feed", 0.70),
    ("Cointelegraph", "https://cointelegraph.com/rss", 0.68),
    ("Protos", "https://protos.com/feed/", 0.68),
    ("BeInCrypto", "https://beincrypto.com/feed/", 0.66),
    ("Finance Magnates", "https://www.financemagnates.com/feed/", 0.66),
    ("Bitcoin.com News", "https://news.bitcoin.com/feed/", 0.64),
    ("crypto.news", "https://crypto.news/feed/", 0.64),
    ("Crypto Briefing", "https://cryptobriefing.com/feed/", 0.62),
    ("Bitcoin.com", "https://www.bitcoin.com/feed/", 0.60),
    ("CryptoPotato", "https://cryptopotato.com/feed/", 0.60),
    ("Cryptonews", "https://cryptonews.com/news/feed/", 0.60),
    ("NewsBTC", "https://www.newsbtc.com/feed/", 0.60),
    ("Seeking Alpha Crypto", "https://seekingalpha.com/market_currents.xml", 0.60),
    ("The Daily Hodl", "https://dailyhodl.com/feed/", 0.60),
    ("Bitcoinist", "https://bitcoinist.com/feed/", 0.58),
    ("CoinJournal", "https://coinjournal.net/feed/", 0.58),
    ("Cointribune", "https://www.cointribune.com/en/feed/", 0.58),
    ("TheStreet Crypto", "https://www.thestreet.com/.rss/full/", 0.58),
    ("Bitget Blog", "https://www.bitget.com/blog/rss", 0.56),
    ("99Bitcoins", "https://99bitcoins.com/feed/", 0.55),
    ("Motley Fool Crypto", "https://www.fool.com/feeds/index.aspx?id=crypto", 0.55),
    ("U.Today", "https://u.today/rss", 0.55),
    ("Watcher Guru", "https://watcher.guru/news/feed", 0.55),
    ("Coinpedia", "https://coinpedia.org/feed/", 0.54),
    ("CoinSpeaker", "https://www.coinspeaker.com/feed/", 0.52),
    ("Cryptopolitan", "https://www.cryptopolitan.com/feed/", 0.52),
    ("NFT Evening", "https://nftevening.com/feed/", 0.52),
    ("The Crypto Basic", "https://thecryptobasic.com/feed/", 0.52),
    ("Blockchain.News", "https://blockchain.news/RSS", 0.50),
    ("Crypto News Flash", "https://www.crypto-news-flash.com/feed/", 0.50),
    ("CryptoDaily", "https://cryptodaily.co.uk/feed", 0.50),
    ("CryptoTicker", "https://cryptoticker.io/en/feed/", 0.50),
    ("TokenPost", "https://tokenpost.com/rss", 0.50),
    ("Captain Altcoin", "https://captainaltcoin.com/feed/", 0.48),
    ("CryptoNewsZ", "https://www.cryptonewsz.com/feed/", 0.48),
    ("Live Bitcoin News", "https://www.livebitcoinnews.com/feed/", 0.48),
    ("The Bitcoin News", "https://thebitcoinnews.com/feed/", 0.48),
    ("The Cryptonomist", "https://en.cryptonomist.ch/feed/", 0.48),
    ("BlockchainReporter", "https://blockchainreporter.net/feed/", 0.46),
    ("CoinEdition", "https://coinedition.com/feed/", 0.46),
    ("Hackernoon Crypto", "https://hackernoon.com/tagged/crypto/feed", 0.45),
    ("The Merkle", "https://themerkle.com/feed/", 0.45),
    ("BitcoinKE", "https://bitcoinke.io/feed/", 0.44),
    ("BitcoinWorld", "https://bitcoinworld.co.in/feed/", 0.44),
    ("CoinCu", "https://coincu.com/feed/", 0.44),
    ("NullTX", "https://nulltx.com/feed/", 0.44),
    ("The Coin Republic", "https://www.thecoinrepublic.com/feed/", 0.44),
    ("UseTheBitcoin", "https://usethebitcoin.com/feed/", 0.42),
    ("Crypto Adventure", "https://cryptoadventure.com/feed/", 0.40),
    ("CryptoMode", "https://cryptomode.com/feed/", 0.40),
    # ---- news aggregators ----
    (
        "Google News Bitcoin",
        "https://news.google.com/rss/search?q=bitcoin&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Google News Crypto",
        "https://news.google.com/rss/search?q=cryptocurrency&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Google News Crypto Regulation",
        "https://news.google.com/rss/search?q=crypto+regulation+OR+SEC&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Google News Crypto Trading",
        "https://news.google.com/rss/search?q=crypto+trading&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Google News DeFi",
        "https://news.google.com/rss/search?q=defi&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Google News Ethereum",
        "https://news.google.com/rss/search?q=ethereum&hl=en-US&gl=US&ceid=US:en",
        0.55,
    ),
    (
        "Bing News Crypto",
        "https://www.bing.com/news/search?q=crypto&format=RSS",
        0.50,
    ),
    (
        "Google News Altcoin",
        "https://news.google.com/rss/search?q=altcoin&hl=en-US&gl=US&ceid=US:en",
        0.50,
    ),
    (
        "Reddit r/CryptoCurrency",
        "https://www.reddit.com/r/CryptoCurrency/.rss",
        0.45,
    ),
    ("Stacker News", "https://stacker.news/rss", 0.42),
    ("TradingView Ideas", "https://www.tradingview.com/feed/", 0.40),
    # ---- macro / regulation ----
    (
        "Federal Reserve Press",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        0.85,
    ),
    ("SEC Press Releases", "https://www.sec.gov/news/pressreleases.rss", 0.85),
    ("CFTC Press Releases", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml", 0.82),
    ("ForexLive", "https://www.forexlive.com/feed/news", 0.62),
    ("Investing.com Crypto", "https://www.investing.com/rss/news_301.rss", 0.60),
    ("MarketPulse", "https://www.marketpulse.com/feed/", 0.60),
    ("Zerohedge", "https://feeds.feedburner.com/zerohedge/feed", 0.58),
    # ---- on-chain / analytics / research ----
    ("Glassnode Insights", "https://insights.glassnode.com/rss/", 0.82),
    ("Bitcoin Optech", "https://bitcoinops.org/feed.xml", 0.80),
    ("Chainalysis Blog", "https://www.chainalysis.com/blog/feed/", 0.80),
    ("Ark Invest", "https://www.ark-invest.com/feed", 0.72),
    ("IntoTheBlock", "https://medium.com/feed/intotheblock", 0.72),
    ("TRM Labs", "https://www.trmlabs.com/post/rss.xml", 0.64),
    # ---- exchanges / company / protocols ----
    ("Ethereum Foundation Blog", "https://blog.ethereum.org/feed.xml", 0.82),
    ("Arbitrum Blog", "https://blog.arbitrum.io/feed", 0.62),
    ("Solana News", "https://solana.com/news/rss.xml", 0.62),
    ("Coinbase Status", "https://status.coinbase.com/history.rss", 0.60),
    ("Kraken Status", "https://status.kraken.com/history.rss", 0.58),
    # ---- mainstream finance / tech ----
    (
        "Bloomberg Technology",
        "https://feeds.bloomberg.com/technology/news.rss",
        0.85,
    ),
    (
        "Financial Times Digital",
        "https://www.ft.com/cryptocurrencies?format=rss",
        0.85,
    ),
    (
        "The Economist Finance",
        "https://www.economist.com/finance-and-economics/rss.xml",
        0.85,
    ),
    ("Bloomberg Crypto", "https://feeds.bloomberg.com/crypto/news.rss", 0.82),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", 0.82),
    (
        "NYTimes Business",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        0.80,
    ),
    (
        "CNBC Crypto",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
        0.78,
    ),
    (
        "Washington Post Business",
        "https://feeds.washingtonpost.com/rss/business",
        0.78,
    ),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", 0.74),
    ("NPR Business", "https://feeds.npr.org/1006/rss.xml", 0.74),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", 0.72),
    (
        "CNBC Markets",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
        0.72,
    ),
    (
        "Wired Business",
        "https://www.wired.com/feed/category/business/latest/rss",
        0.72,
    ),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", 0.70),
    (
        "Guardian Cryptocurrencies",
        "https://www.theguardian.com/technology/cryptocurrencies/rss",
        0.70,
    ),
    ("The Verge", "https://www.theverge.com/rss/index.xml", 0.66),
    ("ZDNet", "https://www.zdnet.com/news/rss.xml", 0.64),
    ("Business Insider Crypto", "https://www.businessinsider.com/rss", 0.60),
    (
        "Nasdaq Crypto",
        "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
        0.60,
    ),
]
