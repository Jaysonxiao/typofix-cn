import re
from collections import Counter

from typofix_cn.documents.models import ExtractedBlock

from .document_helpers import first_context
from .helpers import make_issue


_ENDING_PUNCTUATION = set("。！？!?；;：:")


def _level(block: ExtractedBlock) -> int | None:
    match = re.search(r"(?:Heading|标题)\s*(\d+)", block.style_name or "", flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


class StructureRuleSet:
    def check_document(self, blocks: list[ExtractedBlock]):
        issues = []
        headings = [block for block in blocks if block.role == "heading"]
        levels = [_level(block) for block in headings]
        previous: int | None = None
        for block, level in zip(headings, levels):
            if block.text.rstrip().endswith(tuple(_ENDING_PUNCTUATION)):
                context = first_context(block)
                end = len(block.text.rstrip())
                issues.append(make_issue(context, type_code="HEADING_END_PUNCTUATION", start=end - 1, end=end, message="标题末尾不建议使用句末标点"))
            if level is not None and previous is not None and level > previous + 1:
                context = first_context(block)
                issues.append(make_issue(context, type_code="HEADING_LEVEL_JUMP", start=0, end=0, message="标题层级出现跳跃"))
            if level is not None:
                previous = level

        for label, code in (("图", "FIGURE_NUMBER_DUPLICATE_OR_GAP"), ("表", "TABLE_NUMBER_DUPLICATE_OR_GAP")):
            numbers = [match.group(1) for block in blocks for match in [re.match(rf"{label}(\d+(?:\.\d+)*)\s+", block.text)] if match]
            counts = Counter(numbers)
            for number, count in counts.items():
                if count > 1:
                    block = next(block for block in blocks if block.text.startswith(f"{label}{number}"))
                    issues.append(make_issue(first_context(block), type_code=code, start=0, end=len(number) + 1, message=f"{label}{number}编号重复"))
            targets = set(numbers)
            for block in blocks:
                for match in re.finditer(rf"{label}(\d+(?:\.\d+)*)", block.text):
                    if match.group(1) not in targets:
                        issues.append(make_issue(first_context(block), type_code="CROSS_REFERENCE_TARGET_MISSING", start=match.start(), end=match.end(), message=f"正文引用的{label}{match.group(1)}不存在"))
        return issues
