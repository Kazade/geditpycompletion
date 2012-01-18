#!/usr/bin/env python
""" A code completion parser for Python """

from StringIO import StringIO
import tokenize
from token import DEDENT, NEWLINE

class ScopeType:
    MODULE = 1
    CLASS = 2
    METHOD = 3

class Scope(object):
    def __init__(self, name, scope_type, parent=None):
        self.name = name
        self.scope_type = scope_type
        self.parent = parent
        
        self.variables = set()
        self.methods = set()
        self.types = set()
        self.keywords = set()
        self.modules = set()
        self.imported_scopes = set()

        self.children = {}

class ObjectScope(Scope):
    def __init__(self, parent):
        super(ObjectScope, self).__init__("object", ScopeType.CLASS, parent=parent)
        
        attrs = dir(object)
        methods = [ x for x in attrs if callable(getattr(object, x, None)) ]
        variables = [ x for x in attrs if not callable(getattr(object, x, None)) ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class ListScope(Scope):
    def __init__(self, parent):
        super(ListScope, self).__init__("list", ScopeType.CLASS, parent=parent)
        
        attrs = dir(list)
        methods = [ x for x in attrs if callable(getattr(list, x, None)) if not x.startswith("__") ]
        variables = [ x for x in attrs if not callable(getattr(list, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class TupleScope(Scope):
    def __init__(self, parent):
        super(TupleScope, self).__init__("tuple", ScopeType.CLASS, parent=parent)
        
        attrs = dir(tuple)
        methods = [ x for x in attrs if callable(getattr(tuple, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(tuple, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class IntScope(Scope):
    def __init__(self, parent):
        super(IntScope, self).__init__("int", ScopeType.CLASS, parent=parent)
        
        attrs = dir(int)
        methods = [ x for x in attrs if callable(getattr(int, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(int, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class StrScope(Scope):
    def __init__(self, parent):
        super(StrScope, self).__init__("str", ScopeType.CLASS, parent=parent)
        
        attrs = dir(str)
        methods = [ x for x in attrs if callable(getattr(str, x, None)) if not x.startswith("_")]
        variables = [ x for x in attrs if not callable(getattr(str, x, None)) if not x.startswith("_") ]
        
        self.variables = set(variables)
        self.methods = set(methods)

class DictScope(Scope):
    def __init__(self, parent):
        super(DictScope, self).__init__("dict", ScopeType.CLASS, parent=parent)
        
        attrs = dir(dict)
        methods = [ x for x in attrs if callable(getattr(dict, x, None)) if not x.startswith("__")]
        variables = [ x for x in attrs if not callable(getattr(dict, x, None)) if not x.startswith("__") ]
        
        self.variables = set(variables)
        self.methods = set(methods)
                
                
class FileParser(object):
    def __init__(self, file_contents, current_line=None):
        self._global = Scope("__global__", ScopeType.MODULE)
        self._current_scope = self._global
        self._current_line = current_line
        self._active_scope = self.get_global_scope()
        self._do_parse(file_contents)

    def _parse_to_end(self):
        tokens = []
        ignore_rest = False
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()
            
            if tok_type == tokenize.COMMENT:
                ignore_rest = True
            
            if not ignore_rest:
                tokens.append((tok_type, token))

            if tok_type == NEWLINE:
                break;
        return tokens
    
    def _parse_class(self):
        type, token, (lineno, indent), end, line = self._gen.next()
        
        class_name = token
        print "Found class: " + class_name
        self._current_scope.types.add(class_name) #Store this class as a type
        
        class_scope = Scope(token, ScopeType.CLASS, parent=self._current_scope)
        self._current_scope.children[class_name] = class_scope
        self._current_scope = class_scope
        print "New scope: " + self._current_scope.name        
        tokens = self._parse_to_end()

        #We have an open bracket, this means the class has parents
        if tokens and tokens[0][1] == "(":
            tokens = tokens[1:]
            for tok_type, token in tokens[:]: 
                if tokens[0][1] == ":": 
                    break
                
                tokens = tokens[1:]
                if token == ")": break
                if token == ",": continue
                
                self._current_scope.imported_scopes.add(token)

        #If at this point tokens[0] is a colon, we need to check and see if there are any other statements
        #after it, if so, we need to dedent
        if tokens and tokens[0][1] == ":":
            if len(tokens) > 1 and tokens[1][1] != "\n":
                #Ignore everything after the colon, but dedent, this is likely something like:
                # class B(object): pass
                self._dedent()

    def _parse_method(self):
        type, token, (lineno, indent), end, line = self._gen.next()

        method_name = token
        print "Found method: " + method_name
        self._current_scope.methods.add(method_name) #Store this class as a type
        
        method_scope = Scope(token, ScopeType.METHOD, parent=self._current_scope)
        self._current_scope.children[method_name] = method_scope
        self._current_scope = method_scope
        
        print "New scope: " + self._current_scope.name

        tokens = self._parse_to_end()
        for tok_type, token in tokens:
            if token in ("(", ",", ")"):
                continue
            elif token == "self":
                self._current_scope.variables.add(token)
                class_scope = self._find_parent_scope_of_type(ScopeType.CLASS)
                self_scope = class_scope
                if self_scope:
                    self._current_scope.children["self"] = self_scope
            else:
                #generic object scope
                self._current_scope.children[token] = ObjectScope(parent=self._current_scope)
                self._current_scope.variables.add(token)

    def _parse_with(self):
        while True:
            tok_type, token, (lineno, indent), end, line = self._gen.next()
            if tok_type == NEWLINE:
                break;
                
            #If we find the "as" token, we know the next token is the variable name
            if token == "as":
                tok_type, token, (lineno, indent), end, line = self._gen.next()
                if tok_type == NEWLINE:
                    break;
                self._current_scope.variables.add(token)
                break
        
        self._parse_to_end()

        
    def _parse_statement(self, lvalue_type, lvalue):
        """ FIXME handle multiple lvalues"""
        
        tokens = [(lvalue_type, lvalue)] + self._parse_to_end()

        is_assignment_statement = False
        equals_position = None
        i = 0
        for token in tokens:
            if token[1] == "=":
                is_assignment_statement = True
                equals_position = i
                break
            i += 1
                
        is_assignment_to_member = tokens[0][1] == "self"
        
        scope = self._current_scope
        
        if is_assignment_statement:
            lvalue_tokens = [ x for x in tokens[:equals_position] if x[1] not in (",",) ]
            rvalue_tokens = [ x for x in tokens[equals_position + 1:] if x[1] not in (",",) ]
            if is_assignment_to_member:
                class_scope = self._find_parent_scope_of_type(ScopeType.CLASS)
                if not class_scope:
                    print("Don't understand this: " + str(tokens))
                    if self._current_scope:
                        print(self._current_scope.name)
                        print(self._current_scope.parent.name)
                    else:
                        print("NO CURRENT SCOPE!")
                    return 
                else:
                    scope = class_scope
            else:
                if len(lvalue_tokens) == 1:
                    scope.variables.add(lvalue_tokens[0][1])
                    if rvalue_tokens[0][1] == "[":
                        scope.children[lvalue_tokens[0][1]] = ListScope(self._current_scope)
                    elif rvalue_tokens[0][1] == "(":
                        scope.children[lvalue_tokens[0][1]] = TupleScope(self._current_scope)
                    elif rvalue_tokens[0][1] == "{":
                        scope.children[lvalue_tokens[0][1]] = DictScope(self._current_scope)                        
                    elif rvalue_tokens[0][0] == tokenize.NUMBER:
                        scope.children[lvalue_tokens[0][1]] = IntScope(self._current_scope)
                    elif rvalue_tokens[0][0] == tokenize.STRING:
                        scope.children[lvalue_tokens[0][1]] = StrScope(self._current_scope)
                else:
                    print "TODO: Handle assignment: ", lvalue_tokens, "=", rvalue_tokens

    def _find_parent_scope_of_type(self, scope_type):
        current = self._current_scope
        while current.scope_type != scope_type and current.parent:
            current = current.parent
            
        if current.scope_type != scope_type:
            return None
            
        return current
    
    def _dedent(self):
        if self._current_scope.parent:
            self._current_scope = self._current_scope.parent
            print "New scope: " + self._current_scope.name    
    
    def _do_parse(self, file_contents):
        import keyword
        
        buf = StringIO(file_contents)
        self._gen = tokenize.generate_tokens(buf.readline)
        
        in_block_without_scope = False
        while True:
            try:
                tok_type, token, (lineno, indent), end, line = self._gen.next()
                print token
#                print line, lineno, self._current_line
                if self._current_line == lineno:
                    self._active_scope = self._current_scope

                if tok_type == DEDENT:
                    if in_block_without_scope:
                        print "skipping dedent"
                        in_block_without_scope = False
                    else:                
                        print "dedenting"
                        self._dedent()
                        continue

                if token == "pass":
                    continue
                elif token == "#" or tok_type == tokenize.COMMENT:
                    self._parse_to_end()
                elif token == "class":
                    last_line_incomplete = not self._parse_class()
                elif token == "def":
                    last_line_incomplete = not self._parse_method()
                elif token == "with":
                    self._parse_with()
                    in_block_without_scope = True
                elif token == "if":
                    tokens = self._parse_to_end()
                    in_block_without_scope = True
                elif token == "@": #Ignore decorator FIXME: should add decorator as a method to the current scope
                    self._parse_to_end()
                elif token == "try":
                    tokens = self._parse_to_end()
                    in_block_without_scope = True
                elif token == "except":
                    tokens = self._parse_to_end()
                    in_block_without_scope = True                    
                elif token == "for":
                    tokens = self._parse_to_end()
                    in_block_without_scope = True                                        
                elif token in keyword.kwlist:
                    print "Unhandled keyword: " + token
                    self._parse_to_end()
                else:
                    if token.strip():
                        self._parse_statement(tok_type, token)

            except StopIteration:
                break
        
    def get_global_scope(self):
        return self._global
        
    def get_active_scope(self):
        return self._active_scope or self.get_global_scope()

class Completer(object):
    def __init__(self):
        self._parsers = {}
        self._active_parser = None
        
    def parse_file(self, name, file_content, line):
        self._parsers[name] = FileParser(file_content, current_line=line)
        self._active_parser = name
    
    def get_completions(self, match):
        print("Completing: " + match)
        
        parser = self._parsers[self._active_parser]
        scope_at_line = parser.get_active_scope()
        
        parts = match.split(".")
        all_possible = set()
        print "Scope: " + scope_at_line.name
        all_possible.update(scope_at_line.variables)
        all_possible.update(scope_at_line.methods)
        all_possible.update(scope_at_line.types)        
    
        if match in all_possible:
            all_possible.remove(match) #Don't include the match
                        
        matches = []
        
        global_matches = set()                
        global_matches.update(parser.get_global_scope().variables)
        global_matches.update(parser.get_global_scope().methods)
        global_matches.update(parser.get_global_scope().types)
        
        if match in global_matches:
            global_matches.remove(match) #Don't include the match        
        
        for possible in global_matches:
            if possible.startswith(match) or not match.strip():
                matches.append(possible)
        
        for part in parts:        
            if part in all_possible and part in scope_at_line.children:
                scope_at_line = scope_at_line.children[part]
                print "Looking at scope: " + scope_at_line.name                
                matches = []
                
                all_possible = set()
                all_possible.update(scope_at_line.variables)
                all_possible.update(scope_at_line.methods)
                all_possible.update(scope_at_line.types)                

                if match in all_possible:
                    all_possible.remove(match) #Don't include the match
            else:

                for possible in all_possible:
                    if possible.startswith(part) or not part.strip():
                        matches.append(possible)
                        
        return sorted(list(set(matches)))

def complete(file_content, match, line):
    c = Completer()
    c.parse_file("test", file_content, line)
    return [ { 'abbr' : x } for x in c.get_completions(match) ]
    
if __name__ == '__main__':
    sample = """
    class A(object):
        class_var = 2
    
        def __init__(self):
            self._var_1 = None
            var1, var2 = (a, b)
            
        def _private(self):
            pass
            
        def public(self, other):
            self._var_1 = 1
            var2 = 2
            
            def submethod(_something):
                pass
                
            with open("x.txt") as f:
                data = f.read()
                
            if self == other:
                g = 1
                
            try:
                pass
            except Something:
                pass
            except Something, e:
                pass
            except (Something, SomethingElse):
                pass
            except (Something, SomethingElse), e:
                pass
    
    class B: pass
    class C(object): pass
    
    def main():
        a = A()
    """
    
    matches = complete(sample, "va", 6)
    print "Matches are: %s" % matches
    matches = complete(sample, "se", 6)
    print "Matches are: %s" % matches
    matches = complete(sample, "self.", 6)
    print "Matches are: %s" % matches

    parser = FileParser(sample)
    global_scope = parser.get_global_scope()
    
    assert global_scope.name == "__global__"
    assert "A" in global_scope.types
    assert "B" in global_scope.types
    assert "main" in global_scope.methods

    assert "A" in global_scope.children
    assert "__init__" in global_scope.children["A"].methods
    assert "_private" in global_scope.children["A"].methods
    assert "public" in global_scope.children["A"].methods
    assert "class_var" in global_scope.children["A"].variables
    
    assert "a" in global_scope.children["main"].variables
    assert "submethod" in global_scope.children["A"].children["public"].methods
    assert "f" in global_scope.children["A"].children["public"].variables
    
    assert "self" in global_scope.children["A"].children["public"].variables
    assert "self" in global_scope.children["A"].children["public"].children
    
    #Self should inherit the parent class scope
    assert "public" in global_scope.children["A"].children["public"].children["self"].methods
    
    #Unknown variables should inherit the "object" scope and so should contain __class__ etc.
    assert "__class__" in global_scope.children["A"].children["public"].children["other"].methods

    assert "g" in global_scope.children["A"].children["public"].variables
