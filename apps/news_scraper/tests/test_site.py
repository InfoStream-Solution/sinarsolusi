from __future__ import annotations

import re
from pathlib import Path

import pytest

import news_scraper_core.sites.base as base_module
from news_scraper_core.config import Settings
from news_scraper_core.site_loader import load_site
from news_scraper_core.sites.base import BaseSite
from news_scraper_core.sites.beritasatu_com import BeritasatuComSite
from news_scraper_core.sites.detik_com import DetikComSite
from news_scraper_core.sites.kompas_com import KompasComSite


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        store_database_url=f"sqlite:///{tmp_path / 'news_scraper.db'}",
        seed_dir=tmp_path / "seed",
        links_dir=tmp_path / "links",
        scraped_dir=tmp_path / "scraped",
        content_dir=tmp_path / "content",
        kbt_api_base_url="http://127.0.0.1:8000",
        kbt_api_token="token",
        scraper_debug=False,
        keep_seed=False,
        keep_scraped=False,
    )


@pytest.fixture
def base_site(settings: Settings) -> BaseSite:
    return BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )


@pytest.fixture
def article_site(settings: Settings) -> BaseSite:
    return BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
        article_path_patterns=(re.compile(r"^/articles/\d+$"),),
    )


def test_base_site_uses_instance_patterns(article_site: BaseSite) -> None:
    assert article_site.is_article_url("https://example.com/articles/123")
    assert not article_site.is_article_url("https://example.com/news/123")


def test_base_site_builds_paths_and_options(
    base_site: BaseSite, settings: Settings
) -> None:
    assert base_site.logger_name == "site.example.com"
    assert base_site.link_allowed_hosts == {"example.com"}
    assert (
        base_site.normalize_url("https://example.com/a#frag")
        == "https://example.com/a#frag"
    )
    assert (
        base_site.normalize_article_url("https://example.com/a#frag")
        == "https://example.com/a#frag"
    )
    assert (
        base_site.article_slug("https://example.com/articles/deep-dive/") == "deep-dive"
    )
    assert base_site.article_slug("https://example.com/") == "article"
    assert base_site.output_path == settings.seed_dir / "example.com.seed"
    assert base_site.scraped_article_output_path(
        "https://example.com/articles/deep-dive"
    ) == (settings.scraped_dir / "example.com" / "article_html" / "deep-dive.html")
    assert base_site.article_output_path("https://example.com/articles/deep-dive") == (
        settings.content_dir / "news_article" / "example.com" / "deep-dive.json"
    )
    assert base_site.article_markdown_output_path(
        "https://example.com/articles/deep-dive"
    ) == (settings.content_dir / "news_article" / "example.com" / "deep-dive.md")

    options = base_site.build_options()
    assert options.url == "https://example.com"
    assert str(options.output_path) == str(settings.seed_dir / "example.com.seed")
    assert options.transform == "basic"
    assert options.pretty is True
    assert options.headers == "default"


def test_base_site_default_parsed_content_and_save(settings: Settings) -> None:
    site = BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )

    article = site.default_parsed_content(
        title="Example Title",
        url="https://example.com/articles/deep-dive",
        category="News",
        author="Writer",
        published_at="2026-04-10",
        summary="Summary",
        content="  First paragraph.\n\nSecond paragraph.  ",
        content_type="news_article",
    )

    assert article.source_site == "example.com"
    assert article.word_count == 4
    assert article.char_count == len("First paragraph.\n\nSecond paragraph.")
    assert article.content == "First paragraph.\n\nSecond paragraph."
    assert article.scraped_at

    output_path = site.save_parsed_article(article, article.url)
    assert (
        output_path
        == settings.content_dir / "news_article" / "example.com" / "deep-dive.json"
    )
    assert output_path.read_text(encoding="utf-8")
    assert (
        output_path.with_suffix(".md")
        .read_text(encoding="utf-8")
        .startswith("# Example Title")
    )


def test_base_site_scrape_article_uses_normalized_url_and_output_path(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site = BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )

    captured: dict[str, object] = {}

    class DummyScraper:
        def __init__(self, options) -> None:
            captured["options"] = options

        def scrape(self):
            captured["scraped"] = True
            return object()

    monkeypatch.setattr(base_module, "HttpScraper", DummyScraper)

    site.scrape_article("https://example.com/articles/deep-dive#frag")

    options = captured["options"]
    assert options.url == "https://example.com/articles/deep-dive#frag"
    assert str(options.output_path) == str(
        settings.scraped_dir / "example.com" / "article_html" / "deep-dive.html"
    )


def test_kompas_parser_skips_republished_notice(settings: Settings) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <h1 class="read__title">Example Title</h1>
        <div class="read__content">
          <p>First paragraph.</p>
          <p>Artikel ini sudah tayang di Kompas.com pada tanggal lain.</p>
          <p>Second paragraph.</p>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.kompas.com/read/2026/04/12/123456/example"
    )

    assert "Artikel ini sudah tayang di" not in article.content
    assert article.content == "First paragraph.\n\nSecond paragraph."


def test_kompas_parser_handles_diperbarui_time_layout(settings: Settings) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div class="row col-offset-fluid clearfix js-giant-wp-sticky-parent">
              <div class="col-bs10-7 js-read-article">
                <div class="read__header col-offset-fluid clearfix">
                  <div>
                    <div>
                      <div class="read__time">
                        <a href="https://www.kompas.com" data-google-interstitial="false">Kompas.com</a>, Diperbarui 18/04/2026, 10:03 WIB
                      </div>
                    </div>
                  </div>
                </div>
                <h1 class="read__title">Example Title</h1>
                <div class="read__content">
                  <p>First paragraph.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.kompas.com/read/2026/04/18/100300/example-title"
    )

    assert article.published_at == "18/04/2026, 10:03 WIB"


def test_kompas_parser_strips_source_prefix_from_published_at(
    settings: Settings,
) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div class="row col-offset-fluid clearfix js-giant-wp-sticky-parent">
              <div class="col-bs10-7 js-read-article">
                <div class="read__header col-offset-fluid clearfix">
                  <div>
                    <div>
                      <div class="read__time"><a href="https://www.kompas.com" data-google-interstitial="false">Kompas.com</a> , 17 April 2026, 10:30 WIB</div>
                    </div>
                  </div>
                </div>
                <h1 class="read__title">Example Title</h1>
                <div class="read__content">
                  <p>First paragraph.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.kompas.com/read/2026/04/17/10304621/example-title"
    )

    assert article.published_at == "17 April 2026, 10:30 WIB"


def test_kompas_parser_joins_multiple_authors(settings: Settings) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div class="row col-offset-fluid clearfix js-giant-wp-sticky-parent">
              <div class="col-bs10-7 js-read-article">
                <div class="read__header col-offset-fluid clearfix">
                  <div>
                    <div class="credit">
                      <div class="credit-title">
                        <p>Penulis</p>
                        <div class="credit-title-name">
                          <div class="credit-title-nameEditor">Melvina Tionardus,</div>
                          <div class="credit-title-nameEditor">Yunanto Wiji Utomo</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <h1 class="read__title">Example Title</h1>
                <div class="read__content">
                  <p>First paragraph.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://money.kompas.com/read/2026/04/11/183737026/example?page=all"
    )

    assert article.author == "Melvina Tionardus, Yunanto Wiji Utomo"


def test_kompas_parser_uses_name_editors_even_without_penulis_label(
    settings: Settings,
) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div class="row col-offset-fluid clearfix js-giant-wp-sticky-parent">
              <div class="col-bs10-7 js-read-article">
                <div class="read__header col-offset-fluid clearfix">
                  <div></div>
                  <div>
                    <div class="credit">
                      <div class="credit-title">
                        <div class="credit-title-name">
                          <div class="credit-title-nameEditor">Melvina Tionardus,</div>
                          <div class="credit-title-nameEditor">Yunanto Wiji Utomo</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <h1 class="read__title">Example Title</h1>
                <div class="read__content">
                  <p>First paragraph.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.kompas.com/edu/read/2026/04/18/120300971/example?page=all"
    )

    assert article.author == "Melvina Tionardus, Yunanto Wiji Utomo"


def test_kompas_parser_prefers_penulis_from_credit_author_modal(
    settings: Settings,
) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div class="row col-offset-fluid clearfix js-giant-wp-sticky-parent">
              <div class="col-bs10-7 js-read-article">
                <div class="read__header col-offset-fluid clearfix">
                  <div>
                    <div class="credit">
                      <div class="credit-picture">
                        <div class="credit-picture-img avatarInit"></div>
                        <div class="credit-picture-img avatarInit"></div>
                      </div>
                      <div class="credit-title">
                        <div class="credit-title-name">
                          <div class="credit-title-nameEditor">Melvina Tionardus,</div>
                          <div class="credit-title-nameEditor">Yunanto Wiji Utomo</div>
                        </div>
                        <p>Tim Redaksi</p>
                      </div>
                    </div>
                    <div id="creditModal" class="creditModal">
                      <a href="https://indeks.kompas.com/profile/1945/Melvina.Tionardus">
                        <div class="credit-author">
                          <div class="credit-author-title">
                            <div class="credit-author-name">Melvina Tionardus</div>
                            <div class="credit-author-position">Penulis</div>
                          </div>
                        </div>
                      </a>
                      <a href="https://indeks.kompas.com/profile/458/Yunanto.Wiji.Utomo">
                        <div class="credit-author">
                          <div class="credit-author-title">
                            <div class="credit-author-name">Yunanto Wiji Utomo</div>
                            <div class="credit-author-position">Editor</div>
                          </div>
                        </div>
                      </a>
                    </div>
                  </div>
                </div>
                <h1 class="read__title">Example Title</h1>
                <div class="read__content">
                  <p>First paragraph.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.kompas.com/edu/read/2026/04/18/120300971/example?page=all"
    )

    assert article.author == "Melvina Tionardus"


def test_kompas_parser_uses_opinion_link_author(settings: Settings) -> None:
    site = KompasComSite(settings)
    html = """
    <html>
      <body>
        <div class="wrap">
          <div class="container clearfix">
            <div></div>
            <div></div>
            <div></div>
            <div>
              <div>
                <div>
                  <div class="opinion__desc">
                    <div class="opinion__author">
                      <a class="opinion__link" href="https://kolom.kompas.com/9884/mudhofir-abdullah" data-google-interstitial="false">Mudhofir Abdullah</a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <h1 class="read__title">Example Title</h1>
        <div class="read__content">
          <p>First paragraph.</p>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://kolom.kompas.com/read/2026/04/18/120300971/example?page=all"
    )

    assert article.author == "Mudhofir Abdullah"


def test_kompas_site_matches_article_urls(settings: Settings) -> None:
    site = KompasComSite(settings)

    assert site.is_article_url(
        "https://www.kompas.com/tekno/read/2024/01/01/123456789/example"
    )
    assert site.is_article_url(
        "https://nasional.kompas.com/read/2026/04/11/13541301/kenakan-beskap-dan-peci-hitam-prabowo-hadiri-munas-xvi-pb-ipsi"
    )
    assert site.normalize_article_url(
        "https://nasional.kompas.com/read/2026/04/11/13541301/kenakan-beskap-dan-peci-hitam-prabowo-hadiri-munas-xvi-pb-ipsi?utm_source=x&foo=bar"
    ) == (
        "https://nasional.kompas.com/read/2026/04/11/13541301/kenakan-beskap-dan-peci-hitam-prabowo-hadiri-munas-xvi-pb-ipsi?page=all"
    )
    assert not site.is_article_url("https://www.kompas.com/")


def test_detik_site_matches_article_urls(settings: Settings) -> None:
    site = DetikComSite(settings)

    assert site.is_article_url(
        "https://www.detik.com/jateng/berita/d-8383892/stok-rudal-as-mulai-menipis-gegara-terus-bombardir-iran"
    )
    assert site.is_article_url(
        "https://news.detik.com/berita/d-8439527/prabowo-hadiri-munas-xvi-pb-ipsi-2026-di-jcc"
    )
    assert site.normalize_article_url(
        "https://www.detik.com/jateng/berita/d-8383892/stok-rudal-as-mulai-menipis-gegara-terus-bombardir-iran?utm_source=x&foo=bar"
    ) == (
        "https://www.detik.com/jateng/berita/d-8383892/stok-rudal-as-mulai-menipis-gegara-terus-bombardir-iran?page=all"
    )
    assert not site.is_article_url("https://www.detik.com/")


def test_detik_site_parses_article_html(settings: Settings) -> None:
    site = DetikComSite(settings)
    html = """
    <html>
      <body>
        <h1 class="detail__title">Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC</h1>
        <div class="detail__author">Tim detikNews</div>
        <div class="detail__date">Jumat, 11 Apr 2026 14:05 WIB</div>
        <div class="detail__body-text itp_bodycontent">
          <p>Lead paragraph.</p>
          <p>ADVERTISEMENT</p>
          <p>Second paragraph.</p>
          <p>Baca juga: ignored</p>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(html, "https://news.detik.com/berita/d-1/example")

    assert article.title == "Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC"
    assert article.author == "Tim detikNews"
    assert article.published_at == "Jumat, 11 Apr 2026 14:05 WIB"
    assert article.summary == "Lead paragraph."
    assert article.content == "Lead paragraph.\n\nSecond paragraph."


def test_detik_site_strips_channel_label_from_author(settings: Settings) -> None:
    site = DetikComSite(settings)
    html = """
    <html>
      <body>
        <h1 class="detail__title">Example title</h1>
        <div class="mx-auto w-full max-w-default flex-1 pt-5">
          <div>
            <div>
              <main>
                <article>
                  <div class="mt-1">
                    <div>
                      <div>
                        <p class="mb-1.5 font-helvetica text-sm font-normal text-black-light1">Kanya Anindita Mutiarasari - <span class="text-bali-orange">detikNews</span></p>
                      </div>
                    </div>
                  </div>
                  <div class="detail__body-text itp_bodycontent">
                    <p>Lead paragraph.</p>
                  </div>
                </article>
              </main>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(html, "https://news.detik.com/berita/d-1/example")

    assert article.author == "Kanya Anindita Mutiarasari"


def test_detik_site_uses_text_black_light3_published_at(settings: Settings) -> None:
    site = DetikComSite(settings)
    html = """
    <html>
      <body>
        <div class="mx-auto w-full max-w-default flex-1 pt-5">
          <div>
            <div>
              <main>
                <article>
                  <div class="mt-1">
                    <div>
                      <div>
                        <time class="text-black-light3 block text-xs">Jumat, 17 Apr 2026 16:36 WIB</time>
                      </div>
                    </div>
                  </div>
                  <h1 class="detail__title">Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC</h1>
                  <div class="detail__body-text itp_bodycontent">
                    <p>Lead paragraph.</p>
                  </div>
                </article>
              </main>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(html, "https://news.detik.com/berita/d-1/example")

    assert article.published_at == "Jumat, 17 Apr 2026 16:36 WIB"


def test_detik_site_uses_plain_header_date_text(settings: Settings) -> None:
    site = DetikComSite(settings)
    html = """
    <html>
      <body>
        <div class="mx-auto w-full max-w-default flex-1 pt-5">
          <div>
            <div>
              <main>
                <article>
                  <div class="mt-1">
                    <div>
                      <div>
                        <p class="mb-1.5 font-helvetica text-sm font-normal text-black-light1">Maria Christabel DK - <span class="text-bali-orange">detikBali</span></p>
                        Jumat, 17 Apr 2026 16:36 WIB
                      </div>
                    </div>
                  </div>
                  <h1 class="detail__title">Menteri Hanif Sebut Baru Denpasar Badung yang Serius Pilah Sampah</h1>
                  <div class="detail__body-text itp_bodycontent">
                    <p>Lead paragraph.</p>
                  </div>
                </article>
              </main>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.detik.com/bali/berita/d-8449026/menteri-hanif-sebut-baru-denpasar-badung-yang-serius-pilah-sampah?page=all",
    )

    assert article.published_at == "Jumat, 17 Apr 2026 16:36 WIB"


def test_detik_site_uses_page_breadcrumb_category(settings: Settings) -> None:
    site = DetikComSite(settings)
    html = """
    <html>
      <body>
        <div class="page__breadcrumb">
          <a href="https://www.detik.com/properti/">detikProperti</a>
          <a dtr-evt="breadcrumb" dtr-sec="breadcrumbkanal" dtr-act="breadcrumb kanal" onclick="_pt(this)" dtr-ttl="Berita " href="https://www.detik.com/properti/berita">
            Berita
          </a>
        </div>
        <h1 class="detail__title">Example title</h1>
        <div class="detail__body-text itp_bodycontent">
          <p>Lead paragraph.</p>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html, "https://www.detik.com/properti/berita/d-1/example?page=all"
    )

    assert article.category == "Berita"


def test_beritasatu_site_matches_article_urls(settings: Settings) -> None:
    site = BeritasatuComSite(settings)

    assert site.is_article_url(
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional"
    )
    assert site.normalize_article_url(
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional?utm_source=x&foo=bar"
    ) == (
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional?page=all"
    )
    assert not site.is_article_url("https://www.beritasatu.com/")


def test_beritasatu_site_parses_article_html(settings: Settings) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <body>
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="https://www.beritasatu.com">Home</a></li>
          <li class="breadcrumb-item active"><a href="https://www.beritasatu.com/sport">Sport</a></li>
        </ol>
        <h1 class="fw-bold b1-text-navy">Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional</h1>
        <small class="text-muted">Sabtu, 11 April 2026 | 13:15 WIB</small>
        <div class="my-auto small">Penulis: <b><a href="https://www.beritasatu.com/penulis/theressia-sunday-silalahi">Theressia Sunday Silalahi</a></b> | Editor: <a href="https://www.beritasatu.com/editor/herman"><b>HE</b></a></div>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p><strong>Jakarta, Beritasatu.com –</strong>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
            <div class="b1-group mb-3 position-relative">
              <p class="h6 mb-1 b1-text-navy">BACA JUGA</p>
              <h2 class="h6 fw-bold">
                <a class="text-dark stretched-link" href="https://www.beritasatu.com/sport/2984071/prabowo-akan-buka-munas-ipsi-2026?utm_source=beritasatu&amp;utm_medium=baca_juga&amp;utm_campaign=prabowo-akan-buka-munas-ipsi-2026">Prabowo Akan Buka Munas IPSI 2026</a>
              </h2>
            </div>
            <p>ADVERTISEMENT</p>
            <p>Munas IPSI 2026 menjadi agenda penting.</p>
            <div style="margin-top:50px;">
              <a href="https://www.beritasatu.com/tag/munas-ipsi-2026"><h3 class="badge fs-tag bg-light px-2 py-1 mb-1 me-2 text-dark" style="font-size:.9rem !important; font-weight:900">Munas IPSI 2026</h3></a>
              <a href="https://www.beritasatu.com/tag/prabowo-subianto"><h3 class="badge fs-tag bg-light px-2 py-1 mb-1 me-2 text-dark" style="font-size:.9rem !important; font-weight:900">Prabowo Subianto</h3></a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional",
    )

    assert (
        article.title
        == "Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional"
    )
    assert article.category == "Sport"
    assert article.published_at == "Sabtu, 11 April 2026 | 13:15 WIB"
    assert article.author == "Theressia Sunday Silalahi"
    assert (
        article.summary
        == "Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI."
    )
    assert article.content == (
        "Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.\n\n"
        "Munas IPSI 2026 menjadi agenda penting."
    )
    assert "Prabowo Akan Buka Munas IPSI 2026" not in article.content
    assert "Munas IPSI 2026\nPrabowo Subianto" not in article.content


def test_beritasatu_site_uses_meta_published_time_fallback(settings: Settings) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-04-11T13:15:00+07:00">
      </head>
      <body>
        <h1 class="fw-bold b1-text-navy">Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional</h1>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional",
    )

    assert article.published_at == "2026-04-11T13:15:00+07:00"


def test_beritasatu_site_uses_exact_published_time_selector(settings: Settings) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <body>
        <main>
          <div>
            <div>
              <div class="col">
                <small class="text-muted">Kamis, 16 April 2026 | 17:47 WIB</small>
              </div>
            </div>
          </div>
        </main>
        <h1 class="fw-bold b1-text-navy">Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional</h1>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional",
    )

    assert article.published_at == "Kamis, 16 April 2026 | 17:47 WIB"


def test_beritasatu_site_skips_author_like_small_for_published_at(
    settings: Settings,
) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <body>
        <main>
          <div>
            <div>
              <div class="col">
                <small class="text-muted">Wiendy Hapsari</small>
                <small class="text-muted">Kamis, 16 April 2026 | 17:47 WIB</small>
              </div>
            </div>
          </div>
        </main>
        <h1 class="fw-bold b1-text-navy">Wilayat al-Faqih: Mengenal Konsep Pemerintahan Republik Islam Iran</h1>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/opini/2984465/wilayat-al-faqih-mengenal-konsep-pemerintahan-republik-islam-iran?page=all",
    )

    assert article.published_at == "Kamis, 16 April 2026 | 17:47 WIB"


def test_beritasatu_site_uses_span_text_muted_published_at(settings: Settings) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <body>
        <main>
          <div>
            <div>
              <div class="col">
                <div class="row mb-4">
                  <div class="col ps-0">
                    <small>
                      <span class="text-muted">Minggu, 12 April 2026 | 15:04 WIB<br></span>
                    </small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
        <h1 class="fw-bold b1-text-navy">Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional</h1>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional",
    )

    assert article.published_at == "Minggu, 12 April 2026 | 15:04 WIB"


def test_beritasatu_site_uses_span_b1_text_navy_author(settings: Settings) -> None:
    site = BeritasatuComSite(settings)
    html = """
    <html>
      <body>
        <main>
          <div>
            <div>
              <div class="col">
                <div class="row mb-4">
                  <div class="col ps-0">
                    <span class="b1-text-navy">Kholid Al Walid</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
        <h1 class="fw-bold b1-text-navy">Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Konsolidasi Nasional</h1>
        <div class="row mt-3">
          <div class="col b1-article body-content">
            <p>Presiden Prabowo Subianto dijadwalkan menghadiri Munas IPSI.</p>
          </div>
        </div>
      </body>
    </html>
    """

    article = site.parse_article(
        html,
        "https://www.beritasatu.com/sport/2984172/dihadiri-prabowo-munas-ipsi-2026-jadi-momentum-konsolidasi-nasional",
    )

    assert article.author == "Kholid Al Walid"


def test_site_loader_resolves_beritasatu(settings: Settings) -> None:
    site = load_site("beritasatu.com", settings)

    assert isinstance(site, BeritasatuComSite)
    assert site.start_url == "https://www.beritasatu.com"
