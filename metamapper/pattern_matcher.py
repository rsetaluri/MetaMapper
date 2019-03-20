from .rewrite_rule import RewriteRule
import coreir


#This will search for a particular pattern in coreir, then replace that with the replacement pattern
class PatternMatcher(RewriteRule):
    def __init__(self, pattern : coreir.module.Module, replace : coreir.module.Module):
        assert pattern.type == replace.type


    def __call__(self,app):

