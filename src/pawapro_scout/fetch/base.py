"""
fetch/base.py
全 Fetcher の基底クラス。
- キャッシュ統合 (_cached_fetch)
- tenacity によるリトライ
- requests.Session の共有
"""

from __future__ import annotations

import io
import logging
import time
from typing import Callable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import (
    BREF_SLEEP_SEC,
    REQUEST_TIMEOUT,
    RETRY_MAX_ATTEMPTS,
    RETRY_WAIT_MAX,
    RETRY_WAIT_MIN,
)

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    """リトライ付き requests.Session を生成する。"""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "pawapro-scout/0.1 (research)"})
    return session


class BaseFetcher:
    """
    全 Fetcher の基底クラス。

    サブクラスは fetch メソッドを定義し、
    _cached_fetch() を使ってキャッシュと統合する。

    使い方:
        class MyFetcher(BaseFetcher):
            def get_something(self) -> pd.DataFrame:
                return self._cached_fetch(
                    "league/something",
                    lambda: self._fetch_something_from_api()
                )
    """

    def __init__(self, cache: CacheStore) -> None:
        self.cache = cache
        self.session = _make_session()

    # ──────────────────────────────────────────────
    # キャッシュ統合
    # ──────────────────────────────────────────────

    def _cached_fetch(
        self,
        cache_key: str,
        fetch_fn: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        """
        キャッシュがあれば返す。なければ fetch_fn を呼んで保存してから返す。
        force_refresh=True の場合は常に fetch_fn を呼ぶ。
        """
        return self.cache.get_or_fetch(cache_key, fetch_fn)

    # ──────────────────────────────────────────────
    # HTTP ユーティリティ
    # ──────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((requests.RequestException, IOError)),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get_csv(self, url: str, params: dict | None = None) -> pd.DataFrame:
        """
        URL から CSV を GET してDataFrame で返す。
        tenacity でリトライ付き。
        """
        resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text))

    @retry(
        retry=retry_if_exception_type((requests.RequestException, IOError)),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _post_json(self, url: str, payload: dict) -> dict | list:
        """
        URL に JSON を POST してレスポンスを返す。
        tenacity でリトライ付き。
        """
        resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _sleep_for_bref(self) -> None:
        """Baseball Reference へのアクセス前に待機する。"""
        time.sleep(BREF_SLEEP_SEC)
