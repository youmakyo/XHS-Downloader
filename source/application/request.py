from typing import TYPE_CHECKING

from curl_cffi.requests import AsyncSession, get
from curl_cffi.requests.exceptions import RequestException

from ..module import ERROR, logging, retry, sleep_time
from ..translation import _

if TYPE_CHECKING:
    from ..module import Manager

__all__ = ["Html"]


class Html:
    MOBILE_USER_AGENT = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    )
    MOBILE_IMPERSONATE = "safari180_ios"
    MOBILE_ACCEPT = (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )

    def __init__(
        self,
        manager: "Manager",
    ):
        self.manager = manager
        self.print = manager.print
        self.retry = manager.retry
        self.client = manager.request_client
        self.timeout = manager.timeout
        self.proxy = manager.proxy
        self.impersonate = manager.impersonate
        self.mobile_client: AsyncSession | None = None

    @retry
    async def request_url(
        self,
        url: str,
        content=True,
        cookie: str | None = None,
        proxy: str | None = None,
        mobile: bool = False,
        **kwargs,
    ) -> str:
        if not url.startswith("http"):
            url = f"https://{url}"
        headers = self.manager.get_headers(url)
        impersonate = self.impersonate
        if mobile:
            # 移动端页面对 UA、Accept 与 TLS 指纹的一致性校验严格，
            # 任一不匹配都会返回风控拦截页
            headers["user-agent"] = self.MOBILE_USER_AGENT
            headers["accept"] = self.MOBILE_ACCEPT
            impersonate = self.MOBILE_IMPERSONATE
        try:
            if cookie:
                response = self.__request_url_with_cookie(
                    url,
                    headers,
                    cookie,
                    proxy=proxy,
                    impersonate=impersonate,
                    **kwargs,
                )
            else:
                response = await self.__request_url_get(
                    url,
                    headers,
                    proxy=proxy,
                    mobile=mobile,
                    **kwargs,
                )
            await sleep_time()
            response.raise_for_status()
            return response.text if content else str(response.url)
        except RequestException as error:
            logging(
                self.print,
                _("网络异常，{0} 请求失败: {1}").format(url, repr(error)),
                ERROR,
            )
            return ""

    @staticmethod
    def format_url(url: str) -> str:
        return bytes(url, "utf-8").decode("unicode_escape")

    def __request_url_with_cookie(
            self,
            url: str,
            headers: dict,
            cookie: str,
            proxy: str | None = None,
            impersonate: str | None = None,
            **kwargs,
    ):
        return get(
            url,
            headers=headers,
            cookies=self.manager.cookie_str_to_dict(cookie),
            timeout=self.timeout,
            verify=False,
            allow_redirects=True,
            proxy=self.proxy if proxy is None else proxy,
            impersonate=impersonate or self.impersonate,
            **kwargs,
        )

    async def __request_url_get(
        self,
        url: str,
        headers: dict,
        proxy: str | None = None,
        mobile: bool = False,
        **kwargs,
    ):
        client = self.__get_mobile_client() if mobile else self.client
        return await client.get(
            url,
            headers=headers,
            proxy=self.proxy if proxy is None else proxy,
            **kwargs,
        )

    def __get_mobile_client(self) -> AsyncSession:
        """移动端页面要求 UA 与 TLS 指纹匹配，否则只会返回风控拦截页。"""

        if self.mobile_client is None:
            self.mobile_client = AsyncSession(
                headers=self.manager.blank_headers,
                cookies=self.client.cookies,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
                proxy=self.proxy,
                impersonate=self.MOBILE_IMPERSONATE,
            )
        return self.mobile_client

    async def close(self) -> None:
        if self.mobile_client is not None:
            await self.mobile_client.close()
            self.mobile_client = None
