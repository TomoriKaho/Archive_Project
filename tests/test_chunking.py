"""chunking服务的单元测试。"""
import sys  # 修改路径确保可导入app包
from pathlib import Path  # 使用Path定位工程根目录
import uuid  # 生成uuid供Document实例使用

sys.path.append(str(Path(__file__).resolve().parents[1]))  # 将项目根目录加入搜索路径

from app.models.entities import Document  # 引入Document模拟对象
from app.services.chunking import (  # 导入待测函数
    chunk_structured_entities,
    chunk_text_sliding_window,
    make_chunks,
)


def test_sliding_window_handles_short_text():
    """短文本无需切分，返回原文。"""
    text = "短文本"  # 使用中文短文本验证多语言
    chunks = chunk_text_sliding_window(text)  # 执行切分
    assert chunks == [text]  # 断言返回单个chunk
    # 设计说明：验证空重叠时不会多生成空chunk。


def test_sliding_window_overlap_preserved():
    """验证相邻chunk具有50字符重叠。"""
    text = "A" * 400  # 构造长文本
    chunks = chunk_text_sliding_window(text, size=250, overlap=50)  # 调用切分
    assert chunks[0][-50:] == chunks[1][:50]  # 断言重叠部分一致
    # 设计说明：保证召回时上下文连续。


def test_sliding_window_exact_size():
    """长度正好等于窗口时仅生成一段。"""
    text = "B" * 250  # 构造250字符文本
    chunks = chunk_text_sliding_window(text, size=250, overlap=50)  # 切分
    assert chunks == [text]  # 只有一段
    # 设计说明：覆盖边界情况避免多余空chunk。


def test_structured_entities_with_len_constraint():
    """结构化实体拼装结果不超过250字符。"""
    entities = [
        {
            "entity": "Book",
            "data": {
                "title": "A",
                "author": "B",
                "year": "2020",
                "isbn": "X",
                "publisher": "Y",
            },
        }
    ]
    chunks = chunk_structured_entities(entities, max_len=250)  # 生成结构化文本
    assert all(len(chunk) <= 250 for chunk in chunks)  # 验证长度约束
    # 设计说明：确保结构化输出满足存储限制。


def test_make_chunks_fallback_to_sliding():
    """当content不是结构化JSON时退回滑窗。"""
    document = Document(  # 构造仅含必要字段的Document实例
        id=1,
        domain_id=1,
        uuid=uuid.uuid4(),  # 使用随机uuid满足非空约束
        title="t",
        doc_metadata={},
    )
    result = make_chunks(document, "abc" * 100)
    assert len(result) > 1  # 会被滑窗切分
    # 设计说明：验证make_chunks在非结构化内容下的兜底逻辑。
