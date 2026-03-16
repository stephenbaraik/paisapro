"""
Supabase REST API client using httpx (no supabase Python package needed).
Wraps PostgREST endpoints with a simple query builder.
"""

import httpx
from .config import get_settings


class QueryBuilder:
    def __init__(self, client: "SupabaseClient", table: str):
        self._client = client
        self._table = table
        self._select_cols = "*"
        self._filters: list[str] = []
        self._order_col: str | None = None
        self._order_desc = False
        self._limit_val: int | None = None
        self._single = False

    def select(self, cols: str) -> "QueryBuilder":
        self._select_cols = cols
        return self

    def eq(self, col: str, val: str) -> "QueryBuilder":
        self._filters.append(f"{col}=eq.{val}")
        return self

    def or_(self, expr: str) -> "QueryBuilder":
        self._filters.append(f"or=({expr})")
        return self

    def order(self, col: str, desc: bool = False) -> "QueryBuilder":
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit_val = n
        return self

    def single(self) -> "QueryBuilder":
        self._single = True
        return self

    def execute(self) -> "Result":
        params: dict[str, str] = {"select": self._select_cols}
        for f in self._filters:
            if f.startswith("or="):
                params["or"] = f[3:]
            else:
                k, v = f.split("=", 1)
                params[k] = v
        if self._order_col:
            params["order"] = f"{self._order_col}.{'desc' if self._order_desc else 'asc'}"
        if self._limit_val is not None:
            params["limit"] = str(self._limit_val)

        headers = dict(self._client._headers)
        if self._single:
            headers["Accept"] = "application/vnd.pgrst.object+json"

        resp = httpx.get(
            f"{self._client._base_url}/{self._table}",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return Result(data if not self._single else [data] if data else [])


class RpcBuilder:
    def __init__(self, client: "SupabaseClient", fn: str):
        self._client = client
        self._fn = fn

    def execute(self) -> "Result":
        resp = httpx.post(
            f"{self._client._base_url}/rpc/{self._fn}",
            headers=self._client._headers,
            timeout=15,
        )
        resp.raise_for_status()
        return Result(resp.json())


class Result:
    def __init__(self, data):
        self.data = data


class SupabaseClient:
    def __init__(self, url: str, key: str):
        self._base_url = f"{url}/rest/v1"
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def table(self, name: str) -> QueryBuilder:
        return QueryBuilder(self, name)

    def rpc(self, fn: str) -> RpcBuilder:
        return RpcBuilder(self, fn)


_client: SupabaseClient | None = None


def get_db() -> SupabaseClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = SupabaseClient(settings.supabase_url, settings.supabase_service_role_key)
    return _client
