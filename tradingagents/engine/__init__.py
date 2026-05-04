"""Fast-query engine and routing helpers."""

from .fast_query import FastQueryEngine
from .query_router import QueryRoute, route_query

__all__ = ["FastQueryEngine", "QueryRoute", "route_query"]
