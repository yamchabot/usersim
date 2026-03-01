"""
search.py — simple in-memory search implementation.

This is intentionally broken: the ranking is wrong, it returns too many
results, and doesn't respect the top-k limit properly.

The agent-convergence example demonstrates an AI agent fixing these bugs
iteratively, guided by usersim constraint violations.
"""

def search(query: str, corpus: list[str], top_k: int = 10) -> dict:
    """
    Search the corpus for items matching the query.

    Returns a dict with:
        results:     list of matched strings (ranked)
        total_found: total matches before truncation
        elapsed_ms:  simulated processing time
    """
    query_lower = query.lower()
    
    # BUG 1: Case-insensitive match is broken — using 'in' without lowering corpus
    matches = [item for item in corpus if query_lower in item]
    
    # BUG 2: Returns ALL matches, ignores top_k
    # Should be: matches[:top_k]
    results = matches
    
    # BUG 3: Ranking is just insertion order (no relevance scoring)
    # Short exact matches should rank higher than long partial matches
    
    # BUG 4: elapsed_ms is hardcoded instead of measured
    elapsed_ms = 0
    
    return {
        "results":     results,
        "total_found": len(matches),
        "elapsed_ms":  elapsed_ms,
    }
