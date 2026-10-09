def split(pages):
    # pages of the same type become one document, page order is kept
    docs = {}
    for page in pages:
        docs.setdefault(page["doc_type"], []).append(page["page_num"])
    return docs