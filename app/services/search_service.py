from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

from app.db.database import Database
from app.services.search_utils import normalize_text, tokenize, build_keywords


@dataclass(frozen=True)
class SearchResult:
    product: dict
    score: float


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    async def _load_synonyms(self, shop_id: int) -> dict[str, set[str]]:
        async with self.db.conn() as conn:
            cur = await conn.execute(
                """
                SELECT term, synonym
                FROM search_synonyms
                WHERE shop_id IS NULL OR shop_id=?
                """,
                (shop_id,),
            )
            rows = await cur.fetchall()

        mapping: dict[str, set[str]] = {}
        for r in rows:
            term = normalize_text(r["term"])
            syn = normalize_text(r["synonym"])
            if not term or not syn:
                continue
            mapping.setdefault(term, set()).add(syn)
            mapping.setdefault(syn, set()).add(term)
        return mapping

    def _expand_query(self, query: str, synonyms: dict[str, set[str]]) -> list[str]:
        tokens = tokenize(query)
        if not tokens:
            return []
        expanded = set(tokens)
        for tok in tokens:
            expanded.update(synonyms.get(tok, set()))
        return list(expanded)

    def _score(self, query_norm: str, candidate_norm: str) -> float:
        if not query_norm or not candidate_norm:
            return 0.0
        if query_norm in candidate_norm:
            return 1.0
        return SequenceMatcher(None, query_norm, candidate_norm).ratio()

    async def search_products(
        self,
        shop_id: int,
        query: str,
        limit: int = 20,
        active_only: bool = True,
    ) -> Sequence[SearchResult]:
        query_norm = normalize_text(query)
        if not query_norm:
            return []

        synonyms = await self._load_synonyms(shop_id)
        expanded_tokens = self._expand_query(query_norm, synonyms)
        if not expanded_tokens:
            expanded_tokens = [query_norm]

        like = f"%{query_norm}%"
        token_likes = [f"%{tok}%" for tok in expanded_tokens]

        placeholders = " OR ".join(["name_norm LIKE ? OR keywords_norm LIKE ?"] * len(token_likes))
        params = []
        for tok_like in token_likes:
            params.extend([tok_like, tok_like])

        q = """
            SELECT *
            FROM products
            WHERE shop_id=?
        """
        params = [shop_id, *params]
        if active_only:
            q += " AND is_active=1"
        q += f" AND ({placeholders} OR name_norm LIKE ? OR keywords_norm LIKE ?)"
        params.extend([like, like])
        q += " ORDER BY id DESC LIMIT 100"

        async with self.db.conn() as conn:
            cur = await conn.execute(q, params)
            rows = [dict(r) for r in await cur.fetchall()]

        if not rows:
            async with self.db.conn() as conn:
                cur = await conn.execute(
                    "SELECT * FROM products WHERE shop_id=? ORDER BY id DESC LIMIT 100",
                    (shop_id,),
                )
                rows = [dict(r) for r in await cur.fetchall()]

        results: list[SearchResult] = []
        for row in rows:
            candidate_norm = normalize_text(row.get("name", ""))
            keywords_norm = normalize_text(row.get("keywords_norm", ""))
            score = max(
                self._score(query_norm, candidate_norm),
                self._score(query_norm, keywords_norm),
            )
            if score >= 0.55:
                results.append(SearchResult(product=row, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    @staticmethod
    def build_product_keywords(name: str, description: str | None = None, extra: Sequence[str] | None = None) -> str:
        parts = [name]
        if description:
            parts.append(description)
        if extra:
            parts.extend(extra)
        return build_keywords(parts)
