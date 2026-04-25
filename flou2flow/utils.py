import re

# Professional "Stop Words" and fillers for token pruning
# Based on common NLP semantic compression lists
PRUNING_LIST = {
    "um", "uh", "err", "ah", "like", "basically", "actually", "literally", 
    "totally", "sort of", "kind of", "you know", "i mean", "so basically"
}

def semantic_prune(text: str) -> str:
    """
    Pro Method: Semantic Compression.
    Reduces token count by removing low-entropy fillers and cleaning noise.
    """
    if not text:
        return ""

    # 1. Remove background noise markers like [BEEP], [COUGH]
    text = re.sub(r"\[.*?\]", "", text)
    
    # 2. Tokenize and remove fillers
    words = text.split()
    clean_words = [w for w in words if w.lower().strip(",.?!") not in PRUNING_LIST]
    
    # 3. deduplicate consecutive words (common in voice disfluencies)
    final_words = []
    for i, word in enumerate(clean_words):
        if i == 0 or word.lower() != clean_words[i-1].lower():
            final_words.append(word)
            
    return " ".join(final_words)

def calculate_token_savings(original: str, pruned: str) -> float:
    """Calculate the % of tokens saved."""
    orig_count = len(original.split())
    pruned_count = len(pruned.split())
    if orig_count == 0: return 0.0
    return (1 - (pruned_count / orig_count)) * 100

def generate_stable_hash(content: str) -> str:
    """
    Generate a deterministic SHA256 hash for a given string content.
    Used for stable element identification in the AI pipeline.
    """
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]
