from collections.abc import Sequence

from typofix_cn.domain.issues import Issue

from .base import Rule, RuleContext
from .layout_rules import FirstLineIndentRule
from .punctuation_rules import PunctuationRule
from .text_rules import RepeatedWordRule, WhitespaceRule


class RuleRegistry:
    def __init__(self, rules: Sequence[Rule]) -> None:
        self._rules = tuple(rules)

    def check(self, context: RuleContext) -> list[Issue]:
        return [issue for rule in self._rules for issue in rule.check(context)]


def build_default_rule_registry() -> RuleRegistry:
    return RuleRegistry([RepeatedWordRule(), PunctuationRule(), WhitespaceRule(), FirstLineIndentRule()])
