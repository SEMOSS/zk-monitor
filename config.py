import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

ZK_HOST = os.getenv("ZK_HOST")

model_config = [
    {
        "model_repo_name": "PixArt-alpha/PixArt-XL-2-1024-MS",
        "model_id": "3a3c3b49-8ce4-4e66-bf42-204c3cbbfcb0",
        "model_name": "pixart",
    },
    {
        "model_repo_name": "microsoft/Phi-3-mini-128k-instruct",
        "model_id": "744a1328-63c0-447e-b516-058a75e8516d",
        "model_name": "phi-3-mini-128k-instruct",
    },
    {
        "model_repo_name": "urchade/gliner_multi-v2.1",
        "model_id": "bcc09965-9bb4-48c3-81f5-df496f9fcfad",
        "model_name": "gliner-multi-v2-1",
    },
]
