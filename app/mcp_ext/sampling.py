from __future__ import annotations


def register_sampling(mcp) -> None:
    @mcp.resource("lifeos://sampling/default")
    def default_sampling():
        return {"temperature": 0.2, "top_p": 0.9, "max_tokens": 512}
