from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


# Step 1: Load SentenceTransformer model
# Old MiniLM version:
# model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Better MPNet alternative:
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
client = OpenAI()    

def _get_hf_embedding(text: str) -> list:
    return model.encode(text).tolist()

def _get_openai_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-large",  # or "text-embedding-3-large"
        input=text
    )
    return response.data[0].embedding


def get_embedding(text: str) -> list:
    """
    Switch according to the embedding model you want.
    """
    # return _get_hf_embedding(text)
    return _get_openai_embedding(text)