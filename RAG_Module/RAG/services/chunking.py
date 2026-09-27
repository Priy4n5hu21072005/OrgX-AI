from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=100,
    chunk_overlap=30
)


def chunk_text(text):
    return splitter.split_text(text)