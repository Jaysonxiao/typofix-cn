from typofix_cn.documents.models import ExtractedBlock
from typofix_cn.documents.sentences import SentenceSpan, split_sentences
from typofix_cn.rules.base import RuleContext


def first_context(block: ExtractedBlock) -> RuleContext:
    sentences = split_sentences(block.text)
    sentence = sentences[0] if sentences else SentenceSpan(index=0, text=block.text, start=0, end=len(block.text))
    return RuleContext(block=block, sentence=sentence)
