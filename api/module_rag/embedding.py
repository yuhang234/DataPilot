"""
Embedding 客户端 —— provider 可插拔(DashScope / OpenAI 兼容端点 / local),纯 HTTP,无 SDK 依赖。

来源优先级(由 service 决定后传入):知识库绑定的 ai_models 模型 > env 兜底(RagConfig)。
DashScope 用 OpenAI 兼容端点 /compatible-mode/v1/embeddings,与 OpenAI 同形,便于统一。
带 rag_embedding 缓存的逻辑在 service 层(按 hash+model 命中),这里只管"算"。

provider=local(别名 local_hash / hash):**完全离线的特征哈希向量化**,不发任何外部请求、不需要 Key。
只适合本地演示 / 内网无模型服务的场景——余弦相似度≈词面重合度,不具备真正语义泛化能力。
"""

from __future__ import annotations

import hashlib
import math
import re

import requests

# 本地离线 embedding:中文按「单字 + 相邻二元组」、英文数字按下划线词切分,TF 加权后特征哈希到固定维度
_LOCAL_PROVIDERS = frozenset({'local', 'local_hash', 'hash'})
_DEFAULT_LOCAL_DIMS = 512
_DEFAULT_BASE_LOCAL = 'local://hash'
_CJK_RE = re.compile(r'[\u4e00-\u9fff]+')
_WORD_RE = re.compile(r'[a-z0-9_]+')

# provider → 默认 base_url(用户未配 base_url 时);其它 OpenAI 兼容端点设 EMBEDDING_URL 即可
_DEFAULT_BASE = {
    'dashscope': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'tongyi': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'openai': 'https://api.openai.com/v1',
    'siliconflow': 'https://api.siliconflow.cn/v1',
    'deepseek': 'https://api.deepseek.com/v1',
}

# 已知模型维度(便于建库时确定 dims;未知则用首条文本实测)
_KNOWN_DIMS = {
    'text-embedding-v1': 1536,
    'text-embedding-v2': 1536,
    'text-embedding-v3': 1024,
    'text-embedding-ada-002': 1536,
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 3072,
    'BAAI/bge-m3': 1024,
    'BAAI/bge-large-zh-v1.5': 1024,
    'BAAI/bge-large-en-v1.5': 1024,
    'Qwen/Qwen3-Embedding-0.6B': 1024,
}


def _local_tokens(text: str) -> list[str]:
    """切出用于哈希的 token:中文单字/二元组 + 英文数字词,保留字面顺序无关的集合语义。"""
    low = (text or '').lower()
    tokens = _WORD_RE.findall(low)
    for seg in _CJK_RE.findall(low):
        tokens.extend(seg)
        tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
    return tokens


def _hash_embed(text: str, dims: int) -> list[float]:
    """确定性特征哈希向量(TF 次线性加权 + L2 归一化);同文本任何时候都得到同一向量。"""
    vec = [0.0] * dims
    counts: dict[str, int] = {}
    for tok in _local_tokens(text):
        counts[tok] = counts.get(tok, 0) + 1
    for tok, cnt in counts.items():
        idx = int(hashlib.md5(tok.encode('utf-8')).hexdigest(), 16) % dims
        vec[idx] += 1.0 + math.log(cnt)  # 次线性 TF:高频词不过度主导
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


def _local_dims(model: str) -> int:
    """从模型名尾部解析维度(local-hash-512 → 512),解析不到用默认 512。"""
    m = re.search(r'-(\d{2,5})$', model or '')
    if m and 32 <= int(m.group(1)) <= 8192:
        return int(m.group(1))
    return _DEFAULT_LOCAL_DIMS


class EmbeddingClient:
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        *,
        dims: int | None = None,
        batch_size: int = 16,
        timeout: int = 60,
    ) -> None:
        self.provider = (provider or 'dashscope').strip().lower()
        self.model = model
        self.api_key = api_key
        self.local = self.provider in _LOCAL_PROVIDERS
        if self.local:  # 离线 provider:不解析外部 base_url
            self.base = _DEFAULT_BASE_LOCAL
            self._dims = dims or _KNOWN_DIMS.get(model) or _local_dims(model)
        else:
            base = (base_url or '').strip() or _DEFAULT_BASE.get(self.provider, _DEFAULT_BASE['openai'])
            self.base = base.rstrip('/')
            self._dims = dims or _KNOWN_DIMS.get(model)
        self.batch_size = batch_size
        self.timeout = timeout

    @property
    def dims(self) -> int:
        """返回维度;未知则实测一条。"""
        if self._dims is None:
            self._dims = len(self.embed(['_dim_probe_'])[0])
        return self._dims

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化,保持入参顺序。"""
        if not texts:
            return []
        if self.local:  # 离线:本地算,不发 HTTP
            return [_hash_embed(t, self.dims) for t in texts]
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            out.extend(self._embed_batch(texts[i : i + self.batch_size]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        url = f'{self.base}/embeddings'
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        payload: dict = {'model': self.model, 'input': batch}
        if self.provider == 'openai' and self._dims and self.model.startswith('text-embedding-3'):
            payload['dimensions'] = self._dims  # openai v3 可指定维度
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f'embedding 调用失败 {resp.status_code}: {resp.text[:300]}')
        data = resp.json().get('data') or []
        # 按 index 排序确保对齐
        data = sorted(data, key=lambda d: d.get('index', 0))
        return [d['embedding'] for d in data]
