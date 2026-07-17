import re

from typofix_cn.documents.models import ExtractedBlock

from .document_helpers import first_context
from .helpers import make_issue


class AcademicReferenceRuleSet:
    def check_document(self, blocks: list[ExtractedBlock]):
        issues = []
        for label in ("图", "表"):
            targets = {
                match.group(1)
                for block in blocks
                for match in [re.match(rf"{label}(\d+(?:\.\d+)*)\s+", block.text)]
                if match
            }
            for block in blocks:
                for match in re.finditer(rf"{label}(\d+(?:\.\d+)*)", block.text):
                    if match.group(1) not in targets:
                        issues.append(make_issue(first_context(block), type_code="CROSS_REFERENCE_TARGET_MISSING", start=match.start(), end=match.end(), message=f"正文引用的{label}{match.group(1)}不存在"))
        reference_index = next((index for index, block in enumerate(blocks) if block.text.strip() == "参考文献"), len(blocks))
        body_text = "\n".join(block.text for block in blocks[:reference_index])
        cited = {int(value) for value in re.findall(r"\[(\d+)\]", body_text)}
        entries: dict[int, ExtractedBlock] = {}
        for block in blocks[reference_index + 1 :]:
            match = re.match(r"\[(\d+)\]", block.text.strip())
            if match:
                number = int(match.group(1))
                if number in entries:
                    issues.append(make_issue(first_context(block), type_code="REFERENCE_NUMBER_DUPLICATE_OR_GAP", start=0, end=len(match.group(0)), message=f"参考文献编号[{number}]重复"))
                entries[number] = block
        for block in blocks[:reference_index]:
            for match in re.finditer(r"\[(\d+)\]", block.text):
                number = int(match.group(1))
                if number not in entries:
                    issues.append(make_issue(first_context(block), type_code="CITATION_TARGET_MISSING", start=match.start(), end=match.end(), message=f"引用文献[{number}]不存在"))
        for number, block in entries.items():
            if number not in cited:
                issues.append(make_issue(first_context(block), type_code="REFERENCE_NOT_CITED", start=0, end=len(block.text), message=f"参考文献[{number}]未在正文中引用"))
        return issues
